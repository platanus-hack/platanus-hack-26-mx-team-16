"""Extraction phase handlers (F2 · M1).

A faithful partition of the monolithic ``run_extraction_pipeline`` into the six
library phases the interpreter sequences (``ingest`` → ``extract_text`` →
``classify_pages`` → ``extract_fields`` → ``validate_extraction`` → ``finalize``).
Each handler reuses the *exact* same activity calls, checkpoints and helpers as
the original — so a run through the interpreter is a behavioural replica
(golden-run equivalence, F1 verification). Importing this module registers the
handlers into ``PHASE_LIBRARY``.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.document_processing import (
        DocumentProcessingOutput,
        ReadS3JsonInput,
    )
    from src.common.domain.enums.processing_job_events import (
        ProcessingJobEventType,
        DocumentStatus,
        JobStatus,
        JobStep,
    )
    from src.common.domain.enums.pipelines import PhaseKind
    from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
    from src.workflows.application.pipelines.case_transitions import transition_case
    from src.workflows.application.pipelines.runtime import (
        PipelineState,
        register_phase,
    )
    from src.workflows.application.document_processing.input_builder import (
        doctype_versions_from_temporal_dicts,
    )
    from src.workflows.domain.lambda_catalog import (
        resolve_lambda_function,
    )
    from src.workflows.domain.models.phase_configs import (
        ClassifyPagesConfig,
        ExtractFieldsConfig,
        ExtractTextConfig,
        FieldEmitConfig,
        FinalizeConfig,
        ValidateExtractionConfig,
        parse_duration,
        project_emit_fields,
    )
    from src.workflows.domain.services.field_confidence import (
        compute_field_confidence,
    )
    from src.workflows.domain.utils import count_fields, count_pages, count_validations
    from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
        DispatchProcessingJobWebhookInput,
        MarkDocumentInput,
        PersistClassifiedDocumentsInput,
        PersistClassifiedDocumentsOutput,
        PersistDocumentTextsInput,
        PersistedDocumentRef,
        ReadClassifiedRefsOutput,
        SplitClassifiedDocumentsOutput,
    )
    from src.workflows.presentation.workflows.base import (
        CREATE_PROCESS_RECORD_ACTIVITY,
        DEFAULT_RETRY_POLICY,
        DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY,
        MARK_DOCUMENT_STATUS_ACTIVITY,
        PERSIST_CLASSIFIED_DOCS_ACTIVITY,
        PERSIST_DOCUMENT_TEXTS_ACTIVITY,
        READ_CLASSIFIED_REFS_ACTIVITY,
        SPLIT_CLASSIFIED_DOCS_ACTIVITY,
    )
    from src.common.domain.entities.workflows.case_runtime import (
        ChildCaseDocumentRef,
        CreateChildCasesInput,
        CreateChildCasesOutput,
        ResolveClassifierInput,
        ResolveClassifierOutput,
        SignalCaseWorkflowInput,
        StartChildCaseRunsInput,
    )
    from src.workflows.presentation.workflows.activities.case_runtime_activities import (
        SIGNAL_CASE_WORKFLOW_ACTIVITY,
    )
    from src.workflows.application.pipelines.case_transitions import append_case_event
    from src.workflows.application.workflow_cases.case_run_starter import CASE_SPLIT_SIGNAL
    from src.workflows.domain.services.pipeline_validation import (
        DEFAULT_FAN_OUT_MAX_CHILDREN,
    )
    from src.workflows.presentation.workflows.activities.fan_out_cases import (
        CREATE_CHILD_CASES_ACTIVITY,
        START_CHILD_CASE_RUNS_ACTIVITY,
    )

CASE_SPLIT_EVENT = "case.split"
# E5 · fan-out: batch de children por activity en finalize (límite 2 MiB +
# acotar el blast radius de un retry).
CHILD_SIGNAL_BATCH_SIZE = 20
# F3 · D-C: nombre de la activity (string local — el workflow NO importa el
# módulo de la activity, solo su nombre, igual que el resto de fases).
RESOLVE_CLASSIFIER_ACTIVITY = "resolve_classifier"


async def _resolve_classify_lambda(ctx, phase, data) -> str:
    """Lambda a invocar en classify_pages (F3). ``classifier == "default"`` ⇒
    el lambda base de hoy (byte-idéntico, sin activity extra). Un slug del
    registry se resuelve en ``resolve_classifier``; motores prompt/tool o un slug
    inexistente degradan al lambda base."""
    cfg = ClassifyPagesConfig.model_validate(phase.config or {})
    default_fn = resolve_lambda_function(PhaseKind.CLASSIFY_PAGES.value)
    if cfg.classifier == "default" or data.tenant_id is None:
        return default_fn
    resolved: ResolveClassifierOutput = await workflow.execute_activity(
        RESOLVE_CLASSIFIER_ACTIVITY,
        ResolveClassifierInput(tenant_id=data.tenant_id, slug=cfg.classifier),
        result_type=ResolveClassifierOutput,
        start_to_close_timeout=timedelta(seconds=15),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    if resolved.found and resolved.kind == "lambda" and resolved.lambda_function:
        fn = resolved.lambda_function
        return f"{fn}:{resolved.lambda_alias}" if resolved.lambda_alias else fn
    return default_fn


@register_phase(PhaseKind.INGEST.value, scope="document")
async def ingest(ctx, phase, state: PipelineState) -> None:
    data = state.data
    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.DISPATCHED,
        payload={
            "file_id": str(data.file_id) if data.file_id else None,
            "file_name": data.file_name,
            "temporal_job_id": state.job_id,
            "started_at": workflow.now().isoformat(),
        },
        job_status=JobStatus.PROCESSING,
    )


@register_phase(PhaseKind.EXTRACT_TEXT.value, scope="document")
async def extract_text(ctx, phase, state: PipelineState) -> None:
    data = state.data
    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_STARTED,
        payload={"step": JobStep.EXTRACT_TEXT.value, "pct": 0},
        job_status=JobStatus.PROCESSING,
        current_step=JobStep.EXTRACT_TEXT,
    )
    # E6 · Caso 4 — timeout configurable por fase. Las notas de voz transcriben
    # rápido (default 5 min); las grabaciones de llamadas largas con `asr`/`auto`
    # pueden pedir más vía `config.timeout_seconds` (la Lambda aguanta 900 s).
    cfg = ExtractTextConfig.model_validate(phase.config or {})
    # F1 · per_type_overrides: solo si el upload trae UN único document_type
    # (tipo conocido); en multi-tipo/clasificación se usa el extractor base.
    extractor_value = cfg.extractor.value
    if cfg.per_type_overrides and len(data.document_types) == 1:
        slug = (data.document_types[0] or {}).get("slug")
        override = cfg.per_type_overrides.get(slug) if slug else None
        if override is not None:
            extractor_value = override.value
    timeout_seconds = cfg.timeout_seconds
    extract_timeout = timedelta(seconds=int(timeout_seconds)) if timeout_seconds else timedelta(minutes=5)
    try:
        result = await ctx._invoke_lambda(
            resolve_lambda_function(PhaseKind.EXTRACT_TEXT.value),
            {
                "source_uri": data.object_key,
                # ``.value`` ⇒ string crudo idéntico al payload de hoy (BaseEnum
                # NO es str-subclass) — preserva el fingerprint del golden.
                "extractor": extractor_value,
                "job_id": state.job_id,
                "inline_response": False,
            },
            extract_timeout,
            label="extract_text",
        )
    except Exception as exc:
        await ctx._fail_job(data, JobStep.EXTRACT_TEXT, exc)
        raise

    state.extract_text = result
    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={"step": JobStep.EXTRACT_TEXT.value, "pct": 100},
        job_status=JobStatus.PROCESSING,
        current_step=JobStep.EXTRACT_TEXT,
        extracted_text_key=result.get("output_uri"),
    )


@register_phase(PhaseKind.CLASSIFY_PAGES.value, scope="document")
async def classify_pages(ctx, phase, state: PipelineState) -> None:
    data = state.data
    job_id = state.job_id
    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_STARTED,
        payload={"step": JobStep.CLASSIFY_PAGES.value, "pct": 0},
        job_status=JobStatus.PROCESSING,
        current_step=JobStep.CLASSIFY_PAGES,
    )
    classify_lambda = await _resolve_classify_lambda(ctx, phase, data)
    try:
        result = await ctx._invoke_lambda(
            classify_lambda,
            {
                "source_uri": state.extract_text["output_uri"],
                "document_types": data.document_types,
                "job_id": job_id,
                "inline_response": False,
            },
            timedelta(minutes=3),
            label="classify_pages",
        )
    except Exception as exc:
        await ctx._fail_job(data, JobStep.CLASSIFY_PAGES, exc)
        raise

    state.classify_pages = result
    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={"step": JobStep.CLASSIFY_PAGES.value, "pct": 100},
        job_status=JobStatus.PROCESSING,
        current_step=JobStep.CLASSIFY_PAGES,
        classified_pages_key=result.get("output_uri"),
    )

    # Parse the classify JSON inside the activity → compact refs only (2 MiB limit).
    classified: ReadClassifiedRefsOutput = await workflow.execute_activity(
        READ_CLASSIFIED_REFS_ACTIVITY,
        ReadS3JsonInput(source=result["output_uri"]),
        result_type=ReadClassifiedRefsOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    documents = classified.documents
    state.documents = documents

    if not documents:
        await ctx._checkpoint(
            data,
            type=ProcessingJobEventType.FAILED,
            payload={
                "error_code": "classify_pages.no_documents",
                "message": "classify_pages returned no documents — nothing to extract.",
                "source_step": JobStep.CLASSIFY_PAGES.value,
                "file_name": data.file_name,
                "finished_at": workflow.now().isoformat(),
                "error_data": {
                    "type": "NoDocumentsClassified",
                    "message": "classify_pages returned no documents — nothing to extract.",
                },
            },
            job_status=JobStatus.FAILED,
            current_step=JobStep.CLASSIFY_PAGES,
        )
        state.terminated = True
        state.output = DocumentProcessingOutput(
            job_id=job_id,
            extract_text_source=state.extract_text["output_uri"],
            classify_pages_source=result["output_uri"],
            extract_fields={"extractions": [], "errors": []},
            validate_extraction={"validations": [], "errors": []},
        )
        return

    if data.persist and data.processing_job_uuid is not None:
        persisted: PersistClassifiedDocumentsOutput = await workflow.execute_activity(
            PERSIST_CLASSIFIED_DOCS_ACTIVITY,
            PersistClassifiedDocumentsInput(
                processing_job_uuid=data.processing_job_uuid,
                tenant_id=data.tenant_id,
                workflow_id=data.workflow_id,
                case_id=data.case_id,
                file_id=data.file_id,
                documents=documents,
                # D6': sella la versión del schema de cada doc type usada por
                # este run (viaja en los dicts sellados al despachar).
                document_type_versions=doctype_versions_from_temporal_dicts(data.document_types),
            ),
            result_type=PersistClassifiedDocumentsOutput,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        persisted_docs = persisted.documents
    else:
        persisted_docs = [
            PersistedDocumentRef(
                # workflow.uuid4(): determinista en replay — uuid.uuid4() aquí
                # divergiría y rompería el matching de commands de Temporal.
                document_id=workflow.uuid4(),
                document_type_id=ref.document_type_id,
                document_type_name=ref.document_type_name,
                document_index=ref.document_index,
                page_range=ref.page_range,
            )
            for ref in documents
        ]
    state.persisted_docs = persisted_docs

    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": JobStep.PERSIST_DOCS.value,
            "documents": [
                {
                    "document_id": str(d.document_id),
                    "document_type_id": str(d.document_type_id) if d.document_type_id else None,
                    "document_type_name": d.document_type_name,
                    "document_index": d.document_index,
                    "page_range": d.page_range,
                }
                for d in persisted_docs
            ],
        },
        job_status=JobStatus.PROCESSING,
        current_step=JobStep.PERSIST_DOCS,
    )

    if data.persist and data.tenant_id is not None:
        await workflow.execute_activity(
            CREATE_PROCESS_RECORD_ACTIVITY,
            {
                "tenant_id": str(data.tenant_id),
                "workflow_id": str(data.workflow_id) if data.workflow_id else None,
                "object_key": data.object_key,
                "page_count": count_pages(documents),
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

    # E5 · fan-out (diseño §2.1): partir el caso en child cases. Solo con la
    # config nueva — ausente, el comportamiento E4 (y los golden) quedan
    # byte-idénticos.
    cfg = ClassifyPagesConfig.model_validate(phase.config or {})
    if (
        cfg.fan_out == "child_cases"
        and data.persist
        and data.case_id is not None
        and data.tenant_id is not None
        and data.workflow_id is not None
    ):
        await _fan_out_child_cases(ctx, phase, state, persisted_docs)


async def _fan_out_child_cases(ctx, phase, state: PipelineState, persisted_docs) -> None:
    """Crea los children (activity idempotente) + case_event ``case.split``."""
    data = state.data
    # fan_out_types: solo estos tipos se parten a children; el resto (p. ej. la
    # portada de la circular) permanece en el caso padre. Ausente = todos.
    cfg = ClassifyPagesConfig.model_validate(phase.config or {})
    fan_out_types = cfg.fan_out_types or None
    if fan_out_types is not None:
        persisted_docs = [d for d in persisted_docs if d.document_type_name in fan_out_types]
    if not persisted_docs:
        return
    max_children = cfg.fan_out_max_children or DEFAULT_FAN_OUT_MAX_CHILDREN
    if len(persisted_docs) > max_children:
        exc = ApplicationError(
            f"[classify_pages.fan_out_max_children] classify produced "
            f"{len(persisted_docs)} documents > fan_out_max_children={max_children}.",
            "classify_pages.fan_out_max_children",
            non_retryable=True,
        )
        await ctx._fail_job(data, JobStep.CLASSIFY_PAGES, exc)
        raise exc

    created: CreateChildCasesOutput = await workflow.execute_activity(
        CREATE_CHILD_CASES_ACTIVITY,
        CreateChildCasesInput(
            tenant_id=data.tenant_id,
            workflow_id=data.workflow_id,
            parent_case_id=data.case_id,
            documents=[
                ChildCaseDocumentRef(
                    document_id=doc.document_id,
                    document_index=doc.document_index,
                    document_type_name=doc.document_type_name,
                )
                for doc in sorted(persisted_docs, key=lambda d: d.document_index)
            ],
            # C2: discrimina la clave del child por origen — un 2º archivo al
            # mismo padre crea HERMANOS nuevos en vez de absorber children ajenos.
            file_id=data.file_id,
            processing_job_uuid=data.processing_job_uuid,
        ),
        result_type=CreateChildCasesOutput,
        start_to_close_timeout=timedelta(minutes=2),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    # Refs compactos en scratch: finalize señala a cada child y case_split al padre.
    state.scratch["fan_out_children"] = [
        {
            "caseId": str(ref.case_id),
            "documentIndex": ref.document_index,
            "externalRef": ref.external_ref,
        }
        for ref in created.children
    ]

    task_key = f"{workflow.info().workflow_id}:{phase.id}"
    await append_case_event(
        state,
        CASE_SPLIT_EVENT,
        {
            "total": len(created.children),
            "children": [{"caseId": str(ref.case_id), "externalRef": ref.external_ref} for ref in created.children],
        },
        dedupe_key=f"{task_key}:{CASE_SPLIT_EVENT}",
    )


@register_phase(PhaseKind.EXTRACT_FIELDS.value, scope="document")
async def extract_fields(ctx, phase, state: PipelineState) -> None:
    """One Lambda invocation **per classified document** (E4).

    The classify_pages artifact is first split into per-document S3 slices
    (``split_classified_documents`` — refs only through workflow history),
    then the extract_fields Lambda is invoked once per document with the same
    payload contract as the old batch call (``source_uri`` + ``job_id`` +
    ``inline_response``). Invocations run concurrently via ``asyncio.gather``;
    the coroutines are created in ``document_index`` order so the activity
    schedule is deterministic, and ALL checkpoints / merges happen
    sequentially outside the gather so the SSE ``seq`` progression stays
    stable regardless of completion order.

    The Lambda re-indexes a single-document payload as ``document_index: 0``
    (it enumerates the ``documents`` array it receives), so results are
    re-mapped to the document's ORIGINAL index when merging. The merged
    artifact keeps the exact batch shape downstream consumers rely on:
    ``{status, extractions, errors, metadata}``.

    A failing document no longer kills the run: it is failed individually
    (``_fail_document``) and the rest continue. If EVERY document fails the
    phase fails like the old batch did (``_fail_job`` + raise).
    """
    data = state.data
    cfg = ExtractFieldsConfig.model_validate(phase.config or {})
    # F2: la proyección a eventos vive en extract_fields.emit pero el evento
    # DOCUMENT_PERSISTED lo emite validate_extraction ⇒ se pasa por scratch.
    state.scratch["emit"] = cfg.emit.model_dump()
    docs = sorted(state.persisted_docs, key=lambda d: d.document_index)
    # F2 · document_types: extrae solo el subconjunto de tipos (match por nombre
    # o id). None (default) ⇒ todos (byte-idéntico).
    if cfg.document_types is not None:
        allow = set(cfg.document_types)
        docs = [
            d
            for d in docs
            if d.document_type_name in allow or (d.document_type_id and str(d.document_type_id) in allow)
        ]
    for doc in docs:
        await ctx._checkpoint(
            data,
            type=ProcessingJobEventType.STEP_STARTED,
            payload={"step": JobStep.EXTRACT_FIELDS.value},
            job_status=JobStatus.PROCESSING,
            current_step=JobStep.EXTRACT_FIELDS,
            document_id=doc.document_id,
        )

    try:
        split: SplitClassifiedDocumentsOutput = await workflow.execute_activity(
            SPLIT_CLASSIFIED_DOCS_ACTIVITY,
            ReadS3JsonInput(source=state.classify_pages["output_uri"]),
            result_type=SplitClassifiedDocumentsOutput,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except Exception as exc:
        await ctx._fail_job(data, JobStep.EXTRACT_FIELDS, exc)
        raise

    uri_by_index = {ref.document_index: ref.source_uri for ref in split.documents}
    function_name = resolve_lambda_function(PhaseKind.EXTRACT_FIELDS.value)

    async def _extract_one(doc: PersistedDocumentRef) -> dict:
        return await ctx._invoke_lambda(
            function_name,
            {
                "source_uri": uri_by_index[doc.document_index],
                "job_id": state.job_id,
                "inline_response": True,
            },
            timedelta(minutes=5),
            label=f"extract_fields:{doc.document_index}",
        )

    runnable = [d for d in docs if d.document_index in uri_by_index]
    results = await asyncio.gather(*(_extract_one(d) for d in runnable), return_exceptions=True)
    result_by_index = {doc.document_index: res for doc, res in zip(runnable, results)}

    extractions: list[dict] = []
    errors: list[dict] = []
    failed_by_index: dict[int, dict] = {}
    process_time = 0.0

    for doc in docs:
        res = result_by_index.get(doc.document_index)
        if isinstance(res, asyncio.CancelledError):
            raise res
        if res is None:
            err = {
                "document_index": doc.document_index,
                "error": "document missing from the classify_pages output — nothing to extract.",
                "error_type": "DocumentMissingFromClassifyOutput",
            }
        elif isinstance(res, BaseException):
            err = {
                "document_index": doc.document_index,
                "error": str(res),
                "error_type": type(res).__name__,
            }
        else:
            # Single-doc invocation: the Lambda enumerates the payload it gets,
            # so the entry comes back as index 0 — restore the original index.
            for entry in res.get("extractions") or []:
                extractions.append({**entry, "document_index": doc.document_index})
            metadata = res.get("metadata") or {}
            if isinstance(metadata.get("process_time"), (int, float)):
                process_time += metadata["process_time"]
            continue
        errors.append(err)
        failed_by_index[doc.document_index] = err

    if docs and not extractions:
        exc = next(
            (r for r in results if isinstance(r, BaseException)),
            None,
        ) or ApplicationError(
            f"[extract_fields.all_failed] All {len(docs)} document(s) failed.",
            "extract_fields.all_failed",
        )
        await ctx._fail_job(data, JobStep.EXTRACT_FIELDS, exc)
        raise exc

    state.extract_fields = {
        "status": "partial" if errors else "success",
        "extractions": extractions,
        "errors": errors,
        "metadata": {
            "process_time": process_time,
            "total": len(docs),
            "succeeded": len(extractions),
            "failed": len(errors),
            "job_id": state.job_id,
        },
    }

    survivors: list[PersistedDocumentRef] = []
    for doc in docs:
        if doc.document_index in failed_by_index:
            await ctx._fail_document(data, doc, JobStep.EXTRACT_FIELDS, failed_by_index[doc.document_index])
            continue
        survivors.append(doc)
    state.survivors = survivors


@register_phase(PhaseKind.VALIDATE_EXTRACTION.value, scope="document")
async def validate_extraction(ctx, phase, state: PipelineState) -> None:
    data = state.data
    cfg = ValidateExtractionConfig.model_validate(phase.config or {})
    for doc in state.survivors:
        await ctx._checkpoint(
            data,
            type=ProcessingJobEventType.STEP_STARTED,
            payload={"step": JobStep.VALIDATE.value},
            job_status=JobStatus.PROCESSING,
            current_step=JobStep.VALIDATE,
            document_id=doc.document_id,
        )

    try:
        result = await ctx._invoke_lambda(
            resolve_lambda_function(PhaseKind.VALIDATE_EXTRACTION.value),
            {
                "extractions": state.extract_fields.get("extractions", []),
                "job_id": state.job_id,
                "inline_response": True,
            },
            parse_duration(cfg.timeout, timedelta(minutes=5)),
            label="validate_extraction",
        )
    except Exception as exc:
        await ctx._fail_job(data, JobStep.VALIDATE, exc)
        raise

    state.validate_extraction = result
    extractions_by_idx = {
        int(e["document_index"]): e
        for e in (state.extract_fields.get("extractions") or [])
        if e.get("document_index") is not None
    }
    validations_by_idx = {
        int(v["document_index"]): v for v in (result.get("validations") or []) if v.get("document_index") is not None
    }
    vx_errors_by_idx = {
        int(v["document_index"]): v for v in (result.get("errors") or []) if v.get("document_index") is not None
    }
    # F2/G4 · rule_severities: un survivor cuyo validation_results tenga una
    # severidad bloqueante (status failed) también falla. [] (default) ⇒ solo
    # fallan los docs en `errors` de la lambda (comportamiento de hoy).
    if cfg.rule_severities:
        blocking = set(cfg.rule_severities)
        for idx, v in validations_by_idx.items():
            if idx in vx_errors_by_idx:
                continue
            results = v.get("validation_results") or []
            if any(r.get("severity") in blocking and r.get("status") == "failed" for r in results):
                vx_errors_by_idx[idx] = {"document_index": idx, "error": "blocking_severity"}

    to_complete = [d for d in state.survivors if d.document_index not in vx_errors_by_idx]
    if data.persist and state.extract_text.get("output_uri") and to_complete:
        try:
            await workflow.execute_activity(
                PERSIST_DOCUMENT_TEXTS_ACTIVITY,
                PersistDocumentTextsInput(
                    source=state.extract_text["output_uri"],
                    documents=to_complete,
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
        except Exception as exc:
            workflow.logger.warning(f"pipeline.persist_texts_failed job_id={state.job_id} error={exc}")

    completed: list[PersistedDocumentRef] = []
    for doc in state.survivors:
        if doc.document_index in vx_errors_by_idx:
            await ctx._fail_document(data, doc, JobStep.VALIDATE, vx_errors_by_idx[doc.document_index])
            continue

        extraction_entry = extractions_by_idx.get(doc.document_index, {})
        validation_entry = validations_by_idx.get(doc.document_index, {})

        field_confidence = None
        if data.persist:
            field_confidence = compute_field_confidence(
                extraction_entry.get("mapped_output"), extraction_entry.get("output")
            )
            await workflow.execute_activity(
                MARK_DOCUMENT_STATUS_ACTIVITY,
                MarkDocumentInput(
                    document_id=doc.document_id,
                    status=DocumentStatus.COMPLETED,
                    extraction=extraction_entry.get("output") or None,
                    mapped_extraction=extraction_entry.get("mapped_output") or None,
                    field_confidence=field_confidence or None,
                    validation=validation_entry.get("validation_results") or None,
                ),
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        persisted_payload = {
            "document_id": str(doc.document_id),
            "document_type_id": str(doc.document_type_id) if doc.document_type_id else None,
            "document_type_name": doc.document_type_name,
            "document_index": doc.document_index,
            "page_range": doc.page_range,
            "processing_status": "completed",
            "summary": {
                "extracted_field_count": count_fields(extraction_entry.get("output")),
                "validation_pass_count": count_validations(validation_entry.get("validation_results"), passed=True),
                "validation_fail_count": count_validations(validation_entry.get("validation_results"), passed=False),
            },
        }
        # F2: proyección opt-in de campos/bbox/confianza (extract_fields.emit vía
        # scratch). ``None`` (default emit) ⇒ payload byte-idéntico al de hoy.
        emit = FieldEmitConfig.model_validate(state.scratch.get("emit") or {})
        projected = project_emit_fields(extraction_entry.get("mapped_output"), field_confidence, emit)
        if projected is not None:
            persisted_payload["fields"] = projected

        await ctx._checkpoint(
            data,
            type=ProcessingJobEventType.DOCUMENT_PERSISTED,
            payload=persisted_payload,
            job_status=JobStatus.PROCESSING,
            current_step=JobStep.VALIDATE,
            document_id=doc.document_id,
        )
        completed.append(doc)
    state.completed = completed


@register_phase(PhaseKind.FINALIZE.value, scope="document")
async def finalize(ctx, phase, state: PipelineState) -> None:
    data = state.data
    completed = state.completed
    failed_ids = [d.document_id for d in state.persisted_docs if d not in completed]
    if not failed_ids:
        final_status, final_type = JobStatus.COMPLETED, ProcessingJobEventType.COMPLETED
    elif completed:
        final_status, final_type = JobStatus.PARTIAL, ProcessingJobEventType.COMPLETED
    else:
        final_status, final_type = JobStatus.FAILED, ProcessingJobEventType.FAILED

    await ctx._checkpoint(
        data,
        type=final_type,
        payload={
            "status": final_status.value,
            "file_name": data.file_name,
            "finished_at": workflow.now().isoformat(),
            "document_ids": [str(d.document_id) for d in completed],
            "failed_document_ids": [str(d) for d in failed_ids],
        },
        job_status=final_status,
    )

    finalize_cfg = FinalizeConfig.model_validate(phase.config or {})
    dispatch_webhook = finalize_cfg.dispatch_webhook
    if dispatch_webhook and data.persist and data.processing_job_uuid is not None and data.workflow_id is not None:
        await workflow.execute_activity(
            DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY,
            DispatchProcessingJobWebhookInput(
                processing_job_uuid=data.processing_job_uuid,
                workflow_id=data.workflow_id,
                run_id=workflow.info().run_id,
                final_status=final_status.value,
                webhook_projection=finalize_cfg.webhook_projection,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

    # E4: un run document-scope que pertenece a un caso avisa al CASE# para que
    # ``await_documents`` re-evalúe la completitud con los docs recién
    # persistidos. Solo aplica a runs document-scope: en runs full (recetas sin
    # await_documents) no hay workflow de caso esperando. Best-effort: el fallo
    # de la señal jamás tumba el run de extracción.
    # E5 · fan-out (§2.1): si classify partió el caso, en vez de señalar el
    # CASE# del padre se arranca/señala el CASE# de cada child (batches de 20
    # por activity) y al padre se le señala ``case_split``.
    if data.persist and data.case_id is not None and state.scratch.get("run_scope") == "document":
        fan_out_children = state.scratch.get("fan_out_children") or []
        if fan_out_children:
            await _signal_fan_out_cases(state, fan_out_children)
        else:
            try:
                await workflow.execute_activity(
                    SIGNAL_CASE_WORKFLOW_ACTIVITY,
                    SignalCaseWorkflowInput(case_id=data.case_id),
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )
            except Exception:  # noqa: BLE001 — señal best-effort
                workflow.logger.warning(f"finalize.case_signal_failed case_id={data.case_id}")

    # E7 · F1 (caso universal · straight-through): el intérprete siembra
    # ``finalize_closes_case`` cuando el run es full (scope=None) y la receta no
    # tiene fases case-scope (analyze/output/deliver) — entonces nadie más cerraría
    # el caso, así que lo cierra finalize: RECEIVING→PROCESSING→COMPLETED (o →FAILED
    # si la extracción falló entera). Con fases case-scope lo cierra ``deliver``; con
    # scope="document" lo maneja el CASE# (ramas de arriba). Ausente (tests de fase /
    # golden) ⇒ no-op. Best-effort/idempotente: re-extracción sobre un caso ya
    # COMPLETED es un no-op loggeado.
    if data.persist and data.case_id is not None and state.scratch.get("finalize_closes_case"):
        if final_status == JobStatus.FAILED:
            await transition_case(state, WorkflowCaseStatus.FAILED.value, reason="extraction.failed")
        else:
            await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason="extraction.done")
            await transition_case(state, WorkflowCaseStatus.COMPLETED.value, reason="straight_through")

    # `.get` y no `[...]`: un run extract-only (re-extracción) no tiene
    # artefacto extract_text propio.
    state.output = DocumentProcessingOutput(
        job_id=state.job_id,
        extract_text_source=state.extract_text.get("output_uri", ""),
        classify_pages_source=state.classify_pages.get("output_uri", ""),
        extract_fields=state.extract_fields,
        validate_extraction=state.validate_extraction,
    )


async def _signal_fan_out_cases(state: PipelineState, fan_out_children: list[dict]) -> None:
    """E5 §2.1: arranca/señala el CASE# de cada child y ``case_split`` al padre.

    Best-effort (patrón de la señal E4): el ciclo de los children es
    recuperable por señales posteriores; el run de extracción jamás se cae por
    una señal fallida.
    """
    data = state.data
    child_ids = [child["caseId"] for child in fan_out_children]
    for start in range(0, len(child_ids), CHILD_SIGNAL_BATCH_SIZE):
        batch = child_ids[start : start + CHILD_SIGNAL_BATCH_SIZE]
        try:
            await workflow.execute_activity(
                START_CHILD_CASE_RUNS_ACTIVITY,
                StartChildCaseRunsInput(tenant_id=data.tenant_id, case_ids=batch),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
        except Exception:  # noqa: BLE001 — best-effort por batch
            workflow.logger.warning(f"finalize.child_runs_batch_failed case_id={data.case_id} batch_start={start}")
    try:
        await workflow.execute_activity(
            SIGNAL_CASE_WORKFLOW_ACTIVITY,
            SignalCaseWorkflowInput(case_id=data.case_id, signal=CASE_SPLIT_SIGNAL),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
    except Exception:  # noqa: BLE001 — señal best-effort
        workflow.logger.warning(f"finalize.case_split_signal_failed case_id={data.case_id}")
