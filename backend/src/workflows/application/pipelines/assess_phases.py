"""Assess phase handler (E3 · capa-2 de confianza).

Corre tras ``extract_fields`` (orden document-scope del plan §4.2:
``extract_fields → assess → validate_extraction``): por cada documento
superviviente con campos extraídos lanza UNA activity ``assess_document``
(⇒ una llamada LLM) que compara los campos contra el texto fuente y persiste
``extract_confidence`` + ``signals`` + merge de ``needs_clarification``.

LABEL-ONLY (espíritu B1/confidence_gate): un fallo de la activity ⇒ warning y
se continúa con el siguiente documento — jamás falla el run ni el documento.

GOTCHA de orden: en este punto ``workflow_documents.extracted_text`` AÚN no
está en BD (``persist_document_texts`` corre dentro de ``validate_extraction``),
por eso la activity recibe la URI S3 del artefacto extract_text y slicea ella
misma. El workflow solo manda refs + campos compactos (límite 2 MiB).

Importing this module registers the handler into ``PHASE_LIBRARY``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.common.domain.enums.processing_job_events import (
        ProcessingJobEventType,
        JobStatus,
    )
    from src.common.domain.enums.pipelines import PhaseKind
    from src.workflows.application.pipelines.runtime import (
        PipelineState,
        register_phase,
    )
    from src.workflows.domain.models.phase_configs import AssessConfig, parse_duration
    from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
        AssessDocumentInput,
        AssessDocumentOutput,
    )

ASSESS_DOCUMENT_ACTIVITY = "assess_document"

# LLM puede tardar; 2 intentos como mucho — el fallo es barato porque la fase
# es label-only y sigue de largo.
_ASSESS_TIMEOUT = timedelta(seconds=90)
_ASSESS_RETRY_POLICY = RetryPolicy(maximum_attempts=2)

# Presupuesto del payload `fields` (límite Temporal 2 MiB): si el entry
# serializado excede esto, se degradan los valores a escalares.
_MAX_FIELDS_CHARS = 100_000
_MAX_VALUE_CHARS = 2_000


def compact_fields_for_assess(extraction_entry: dict | None) -> dict[str, Any]:
    """`{campo: valor}` compacto desde un entry de ``extract_fields``.

    Prefiere ``mapped_output`` (hojas ``{value, bbox, inferred}`` → ``value``,
    sin bboxes) y cae a ``output`` crudo. Si aun así el payload es muy grande,
    conserva solo los valores escalares — la activity nunca debe acercarse al
    límite de 2 MiB de Temporal.
    """
    entry = extraction_entry or {}
    mapped = entry.get("mapped_output")
    if isinstance(mapped, dict) and mapped:
        fields = {name: _leaf_value(value) for name, value in mapped.items()}
    else:
        output = entry.get("output")
        fields = dict(output) if isinstance(output, dict) else {}
    if not fields:
        return {}

    import json  # noqa: PLC0415

    serialized = json.dumps(fields, ensure_ascii=False, default=str)
    if len(serialized) > _MAX_FIELDS_CHARS:
        fields = {
            name: value
            for name, value in fields.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
    return {name: (value[:_MAX_VALUE_CHARS] if isinstance(value, str) else value) for name, value in fields.items()}


def _leaf_value(value: Any) -> Any:
    """Quita la envoltura `{value, bbox, inferred}` recursivamente."""
    if isinstance(value, dict):
        if "value" in value:
            return _leaf_value(value["value"])
        return {k: _leaf_value(v) for k, v in value.items() if k not in ("bbox", "inferred")}
    if isinstance(value, list):
        return [_leaf_value(v) for v in value]
    return value


@register_phase(PhaseKind.ASSESS.value, scope="document")
async def assess(ctx, phase, state: PipelineState) -> None:
    data = state.data
    source = state.extract_text.get("output_uri")
    if not source or not data.persist:
        # Sin artefacto extract_text (p.ej. run extract-only) o sin filas en BD
        # que anotar — no hay nada útil que pagar al LLM.
        return

    cfg = AssessConfig.model_validate(phase.config or {})
    assess_timeout = parse_duration(cfg.timeout, _ASSESS_TIMEOUT)
    assess_retry = RetryPolicy(maximum_attempts=cfg.max_attempts)

    extractions_by_idx = {
        int(e["document_index"]): e
        for e in (state.extract_fields.get("extractions") or [])
        if e.get("document_index") is not None
    }
    summary = state.scratch.setdefault("assess", {})

    for doc in state.survivors:
        entry = extractions_by_idx.get(doc.document_index)
        fields = compact_fields_for_assess(entry)
        if not fields:
            continue  # documento sin campos extraídos: skip barato
        try:
            result: AssessDocumentOutput = await workflow.execute_activity(
                ASSESS_DOCUMENT_ACTIVITY,
                AssessDocumentInput(
                    document_id=doc.document_id,
                    tenant_id=data.tenant_id,
                    extract_text_source=source,
                    page_range=doc.page_range,
                    document_type_name=doc.document_type_name,
                    fields=fields,
                    provider=cfg.provider,
                    min_confidence=cfg.min_confidence,
                ),
                result_type=AssessDocumentOutput,
                start_to_close_timeout=assess_timeout,
                retry_policy=assess_retry,
            )
        except Exception as exc:
            workflow.logger.warning(f"pipeline.assess_failed document_id={doc.document_id} error={exc}")
            continue

        doc_summary = {"fields_assessed": result.fields_assessed, "flagged": result.flagged}
        summary[str(doc.document_id)] = doc_summary
        await ctx._checkpoint(
            data,
            type=ProcessingJobEventType.STEP_COMPLETED,
            payload={
                "step": PhaseKind.ASSESS.value,
                "document_id": str(doc.document_id),
                "summary": doc_summary,
            },
            job_status=JobStatus.PROCESSING,
            document_id=doc.document_id,
        )
