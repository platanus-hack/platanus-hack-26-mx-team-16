"""PipelineInterpreterWorkflow — the single generic engine (F1 · M0 · A1 · E1).

Walks a sealed, immutable recipe: ``for phase in version.phases: run handler``.
Desde el cutover E1 (D4) es el ÚNICO motor: todo upload, ingesta y re-extracción
corre por aquí. Un run de la receta ``standard@v1`` produce las mismas filas
``WorkflowDocument`` + eventos ``processing_job.*`` que producía el motor legacy
(paridad congelada en tests/fixtures/pipelines/golden/standard_v1/). New
capabilities are registered handlers, never edits to this body.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

from src.workflows.presentation.workflows.base import (
    DEFAULT_RETRY_POLICY,
    RECORD_PHASE_EXECUTION_ACTIVITY,
    ProcessingJobWorkflowBase,
)

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.document_processing import (
        DocumentProcessingOutput,
    )
    from src.common.domain.entities.workflows.pipeline_run import (
        LoadPipelineVersionInput,
        LoadPipelineVersionOutput,
        PipelineRunInput,
    )
    from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
        PersistedDocumentRef,
        RecordPhaseExecutionInput,
    )

# Claves de `initial_artifacts` que viajan como JSON y deben rehidratarse a
# sus tipos antes de que los handlers de fase las consuman.
_TYPED_ARTIFACT_KEYS = {
    "persisted_docs": PersistedDocumentRef,
}

LOAD_PIPELINE_VERSION_ACTIVITY = "load_pipeline_version"


@workflow.defn
class PipelineInterpreterWorkflow(ProcessingJobWorkflowBase):
    """Generic interpreter for a pipeline-as-data."""

    @workflow.signal
    async def cancel(self) -> None:
        self._cancel_requested = True

    @workflow.signal
    async def pause(self) -> None:
        self._paused = True

    @workflow.signal
    async def resume(self) -> None:
        self._paused = False

    @workflow.signal
    async def task_resolved(self, task_key: str, resolution: dict) -> None:
        """Resume a durable pause (F6). Posted by the resolve endpoint / callback.

        F4: cada resolución se acumula como voto (quórum N-de-M); el gate single
        (N=1) sigue leyendo ``_resolved_tasks`` (compat byte-idéntica)."""
        self._resolved_tasks[task_key] = resolution
        self._votes.setdefault(task_key, []).append(resolution)

    @workflow.signal
    async def corrections(self, task_key: str, payload: dict) -> None:
        """E5 · §3.3: corrección de campos llegó mientras un stage de revisión
        espera resolución — ``args=[task_key, {"fields": [...refs cortos]}]``.
        El stage la consume, re-analiza (child workflow) y sigue esperando."""
        self._pending_corrections.setdefault(task_key, []).append(payload or {})

    @workflow.signal
    async def case_docs_changed(self) -> None:
        """E4: el expediente recibió/perdió documentos — ``await_documents``
        re-evalúa la completitud. Sin payload: el contador es la señal."""
        self._case_docs_changed_count += 1

    @workflow.signal
    async def case_split(self) -> None:
        """E5 · fan-out: el run document-scope partió el expediente en child
        cases — el CASE# del padre sale de ``await_documents``, salta las
        fases case-scope restantes y termina OK (el padre queda PROCESSING)."""
        self._case_split = True

    @workflow.signal
    async def case_ready(self, payload: dict | None = None) -> None:
        """E4: ready explícito (POST /v1/cases/{id}/ready) — ``{force: bool}``.

        ``force`` es pegajoso: una vez forzado, la espera procede aunque
        re-evaluaciones posteriores sigan insatisfechas."""
        self._case_ready_count += 1
        self._case_ready_requested = True
        if payload and payload.get("force"):
            self._case_ready_force = True

    @workflow.run
    async def run(self, payload: PipelineRunInput) -> DocumentProcessingOutput:
        # Lazy import keeps the sandbox import probe minimal; importing the
        # phase modules registers their handlers into PHASE_LIBRARY.
        from src.workflows.application.pipelines import (  # noqa: F401
            analysis_phases,
            assess_phases,
            enrich_phases,
            extraction_phases,
            pause_phases,
        )
        from src.workflows.application.pipelines.entry_points import select_phases
        from src.workflows.application.pipelines.runtime import (
            PHASE_SCOPES,
            PipelineState,
            execute_pipeline,
            filter_phases_by_scope,
            phase_output_snapshot,
        )
        from src.workflows.domain.models.phase_configs import (
            activation_dict_from_version,
            completeness_dict_from_version,
        )
        from src.workflows.domain.models.pipeline import PhaseSpec

        payload = PipelineRunInput.model_validate(payload)
        data = payload.document

        # Re-extracción y futuros runs parciales: continuar el seq del set y
        # arrancar con los artefactos del run original ya sembrados.
        self._seq = payload.starting_seq

        version: LoadPipelineVersionOutput = await workflow.execute_activity(
            LOAD_PIPELINE_VERSION_ACTIVITY,
            LoadPipelineVersionInput(pipeline_id=payload.pipeline_id, version=payload.version),
            result_type=LoadPipelineVersionOutput,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        phases = [PhaseSpec.model_validate(p) for p in version.phases]
        # E4 · diseño §3: scope=None ⇒ receta completa (golden E1–E3 intactos);
        # "document"/"case" ⇒ solo las fases de ese scope (PHASE_SCOPES).
        phases = filter_phases_by_scope(phases, payload.scope)
        # ADR 0002 · §3.3: sub-segmento por punto de entrada del pipeline propio
        # (None/"ingest" = sin cambios; "reextract" = cola de extracción;
        # "data" = desde la primera ``analyze``).
        phases = select_phases(phases, payload.entry_point)

        artifacts = dict(payload.initial_artifacts)
        for key, model in _TYPED_ARTIFACT_KEYS.items():
            if key in artifacts:
                artifacts[key] = [model.model_validate(item) for item in artifacts[key]]

        state = PipelineState(data=data, job_id=data.job_id, artifacts=artifacts)
        # E4 · D5: policies selladas con la versión, disponibles para las fases
        # case-scope (await_documents/extraction_gate/human_review en W2a).
        state.scratch["policies"] = {
            "activation": activation_dict_from_version(version),
            # D-A: completitud plegada en await_documents.config (sin fallback version-level).
            "completeness": completeness_dict_from_version(version),
        }
        # E4: las fases pueden condicionar side-effects al tipo de run (p. ej.
        # finalize solo señala al CASE# desde runs document-scope).
        state.scratch["run_scope"] = payload.scope
        # E7 · F1 (caso universal · straight-through): un run full (scope=None)
        # cuya receta NO tiene fases case-scope (analyze/output/deliver…) no tendría
        # quién cierre el caso ⇒ lo cierra ``finalize``. Es una INSTRUCCIÓN explícita
        # sembrada SOLO por el intérprete: ausente ⇒ no cerrar. Así los tests de fase
        # que llaman ``execute_pipeline`` sin sembrarla, y el golden de extracción,
        # quedan byte-idénticos.
        has_case_scope_phase = any(
            PHASE_SCOPES.get(phase.kind.value if hasattr(phase.kind, "value") else str(phase.kind), "document")
            == "case"
            for phase in phases
        )
        state.scratch["finalize_closes_case"] = payload.scope is None and not has_case_scope_phase

        # Per-phase execution timeline ("Ejecuciones"): record each phase boundary
        # via an activity. Passed as ``on_phase`` so ``execute_pipeline`` stays
        # byte-identical for the golden harness (which omits it). Gated on persist
        # + ids so dry/ephemeral runs write nothing.
        async def _record_phase(event, index, phase, run_state, started_at, error):
            if not data.persist or data.processing_job_uuid is None or data.tenant_id is None:
                return
            await workflow.execute_activity(
                RECORD_PHASE_EXECUTION_ACTIVITY,
                RecordPhaseExecutionInput(
                    processing_job_uuid=data.processing_job_uuid,
                    tenant_id=data.tenant_id,
                    seq=index,
                    phase_id=phase.id,
                    phase_kind=phase.kind.value if hasattr(phase.kind, "value") else str(phase.kind),
                    event=event,
                    started_at=started_at,
                    finished_at=workflow.now() if event != "STARTED" else None,
                    output_snapshot=(
                        phase_output_snapshot(phase, run_state) if event == "COMPLETED" else None
                    ),
                    error=error,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        state = await execute_pipeline(self, phases, state, on_phase=_record_phase)

        if state.output is not None:
            return state.output
        # A recipe with no finalize phase still returns a well-formed result.
        return DocumentProcessingOutput(
            job_id=data.job_id,
            extract_text_source=state.extract_text.get("output_uri", ""),
            classify_pages_source=state.classify_pages.get("output_uri", ""),
            extract_fields=state.extract_fields,
            validate_extraction=state.validate_extraction,
        )
