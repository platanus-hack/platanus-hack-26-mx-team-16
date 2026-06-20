"""Suite de regresión E1: el intérprete reproduce el golden del legacy.

El golden (``tests/fixtures/pipelines/golden/standard_v1/``) congeló el
comportamiento observable de ``run_extraction_pipeline`` ANTES de su borrado
(cutover D4, plan ``product/plans/re-architecture/re-architecture.md``): canned results por activity,
la secuencia ORDENADA de fingerprints y el output final. Tras el cutover, esta
suite re-ejecuta los mismos canned results a través de ``execute_pipeline``
(el intérprete, único motor) con la receta REAL ``standard_extraction_phases()``
de ``src/workflows/domain/recipes.py`` y asserta paridad campo a campo:

- secuencia de fingerprints == ``activity_sequence.json`` (39 entradas),
- output final == ``final_state.json``,
- los fingerprints de ``mark_document_status`` (keys de ``field_confidence`` y
  cuáles son ``source="bbox"``) idénticos — la paridad de confianza congelada.

Nota E4 (extract_fields por documento): el golden original (37 entradas, 1
``invoke_lambda`` batch de extract_fields) se re-grabó DELIBERADAMENTE: el
handler ahora hace ``split_classified_documents`` (1 activity nueva) + N
invocaciones Lambda (una por documento clasificado, 2 en doble_ci.pdf) ⇒ 39
entradas. Los canned per-doc se derivaron partiendo la respuesta batch
congelada por ``document_index`` (la Lambda re-indexa un payload de 1 doc como
``document_index: 0`` — el handler re-mapea al fusionar). ``final_state.json``
NO cambió: la fusión reproduce byte a byte el artefacto batch — eso es lo que
prueba la paridad E4. Ver README del golden.

Nota de harness: el golden se grabó corriendo el motor legacy directo (sin
worker Temporal, monkeypatcheando ``temporalio.workflow``), por lo que NO
contiene el fingerprint de ``load_pipeline_version`` (activity propia de
``PipelineInterpreterWorkflow.run``). Este harness corre ``execute_pipeline``
directo también, así que las secuencias son comparables 1:1 sin ajustes.

Los ``function_name`` del golden embeben ``settings.STAGE`` (``dev`` en el
entorno docker de test): correr solo vía el flujo docker estándar.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from expects import equal, expect, have_length
from temporalio import workflow as tw

from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingInput,
)
from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import (
    extraction_phases,  # noqa: F401 — side effect requerido: puebla PHASE_LIBRARY
)
from src.workflows.application.pipelines.runtime import (
    PHASE_LIBRARY,
    PipelineState,
    execute_pipeline,
)
from src.workflows.domain.lambda_catalog import resolve_lambda_function
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import (
    field_re_extraction_phases,
    standard_extraction_phases,
)
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    PersistClassifiedDocumentsOutput,
    PersistedDocumentRef,
    ReadClassifiedRefsOutput,
    SplitClassifiedDocumentsOutput,
)
from src.workflows.presentation.workflows.base import (
    CREATE_PROCESS_RECORD_ACTIVITY,
    DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY,
    INVOKE_LAMBDA_ACTIVITY,
    MARK_DOCUMENT_STATUS_ACTIVITY,
    PERSIST_CLASSIFIED_DOCS_ACTIVITY,
    PERSIST_DOCUMENT_TEXTS_ACTIVITY,
    PUBLISH_PROCESSING_JOB_EVENT_ACTIVITY,
    READ_CLASSIFIED_REFS_ACTIVITY,
    SPLIT_CLASSIFIED_DOCS_ACTIVITY,
    UPDATE_WORKFLOW_PROCESSING_JOB_STATUS_ACTIVITY,
    ProcessingJobWorkflowBase,
)

GOLDEN_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "pipelines" / "golden" / "standard_v1"

_FIXED_DT = datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC)
_JOB_ID = "CASE#aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa_FILE#eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
_DOCTYPE_UUID = "36aab742-879e-4a3b-b688-5bdb5702ac0b"

_LAMBDA_KINDS = (
    PhaseKind.EXTRACT_TEXT.value,
    PhaseKind.CLASSIFY_PAGES.value,
    PhaseKind.EXTRACT_FIELDS.value,
    PhaseKind.VALIDATE_EXTRACTION.value,
)


def _load_golden() -> tuple[dict, list, dict]:
    canned = json.loads((GOLDEN_DIR / "canned_results.json").read_text())
    sequence = json.loads((GOLDEN_DIR / "activity_sequence.json").read_text())
    state = json.loads((GOLDEN_DIR / "final_state.json").read_text())
    return canned, sequence, state


def _standard_phases() -> list[PhaseSpec]:
    """La receta REAL que siembran el onboarder y la migración — no una copia."""
    return [PhaseSpec.model_validate(p) for p in standard_extraction_phases()]


def _lambda_name_by_kind() -> dict[str, str]:
    """``kind lógico → function_name`` resuelto con la config de la receta real."""
    by_kind: dict[str, str] = {}
    for phase in standard_extraction_phases():
        if phase["kind"] in _LAMBDA_KINDS:
            by_kind[phase["kind"]] = resolve_lambda_function(phase["kind"])
    return by_kind


def _make_canned(canned: dict):
    names = _lambda_name_by_kind()
    by_function = {names[kind]: canned["invoke_lambda"][kind] for kind in _LAMBDA_KINDS}

    def _canned(name: str, arg):
        if name == INVOKE_LAMBDA_ACTIVITY:
            value = by_function[arg.function_name]
            if "status" not in value:
                # E4: extract_fields per-doc — canned keyed por el source_uri
                # del slice por documento (ver canned["split_classified_documents"]).
                return value[arg.payload["source_uri"]]
            return value
        if name == READ_CLASSIFIED_REFS_ACTIVITY:
            return ReadClassifiedRefsOutput.model_validate(canned["read_classified_refs"])
        if name == SPLIT_CLASSIFIED_DOCS_ACTIVITY:
            return SplitClassifiedDocumentsOutput.model_validate(canned["split_classified_documents"])
        if name == PERSIST_CLASSIFIED_DOCS_ACTIVITY:
            return PersistClassifiedDocumentsOutput.model_validate(canned["persist_classified_documents"])
        return None

    return _canned


def _fingerprint(name: str, arg) -> list:
    """Firma JSON-serializable y libre de ids volátiles de una activity.

    DEBE ser idéntica a la usada por el grabador del golden
    (``test_record_golden.py``, borrado con el legacy — ver README del golden):
    las lambdas llevan ``function_name`` completo + keys del payload, y
    ``mark_document_status`` congela qué entries de ``field_confidence`` se
    poblaron y cuáles son ``source="bbox"``.
    """
    if name == INVOKE_LAMBDA_ACTIVITY:
        return [name, arg.function_name, sorted(arg.payload.keys())]
    if name == READ_CLASSIFIED_REFS_ACTIVITY:
        return [name, arg.source]
    if name == SPLIT_CLASSIFIED_DOCS_ACTIVITY:
        return [name, arg.source]
    if name == PERSIST_CLASSIFIED_DOCS_ACTIVITY:
        return [name, len(arg.documents)]
    if name == PERSIST_DOCUMENT_TEXTS_ACTIVITY:
        return [name, arg.source, len(arg.documents)]
    if name == UPDATE_WORKFLOW_PROCESSING_JOB_STATUS_ACTIVITY:
        return [
            name,
            str(arg.status),
            str(arg.current_step),
            arg.last_seq,
            arg.extracted_text_key,
            arg.classified_pages_key,
        ]
    if name == PUBLISH_PROCESSING_JOB_EVENT_ACTIVITY:
        return [
            name,
            str(arg.type),
            arg.seq,
            str(arg.payload.get("step")),
            str(arg.payload.get("status")),
            str(arg.document_id),
        ]
    if name == MARK_DOCUMENT_STATUS_ACTIVITY:
        confidence = arg.field_confidence or {}
        bbox_fields = sorted(
            field
            for field, entry in confidence.items()
            if isinstance(entry, dict) and entry.get("source") == "bbox"
        )
        return [name, str(arg.document_id), str(arg.status), sorted(confidence), bbox_fields]
    if name == CREATE_PROCESS_RECORD_ACTIVITY:
        return [name, arg.get("page_count")]
    if name == DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY:
        return [name, str(arg.final_status)]
    return [name]


def _patch_workflow_runtime(monkeypatch, record: list, canned) -> None:
    async def fake_execute_activity(name, arg=None, **kwargs):
        record.append(_fingerprint(name, arg))
        return canned(name, arg)

    async def fake_wait_condition(*args, **kwargs):
        return None

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "wait_condition", fake_wait_condition)
    monkeypatch.setattr(tw, "now", lambda: _FIXED_DT)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(run_id="run-1"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


def _golden_input() -> DocumentProcessingInput:
    """Mismo input que usó el grabador del golden (ids fijos, ``persist=True``).

    Los valores de ``document_types`` no participan de ningún fingerprint (solo
    las KEYS de los payloads lambda se graban), así que basta el stub uuid+name.
    """
    return DocumentProcessingInput(
        object_key="s3://vnext-assets-dev/samples/doble_ci.pdf",
        document_types=[{"uuid": _DOCTYPE_UUID, "name": "Cedula de Identidad"}],
        job_id=_JOB_ID,
        case_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        workflow_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        tenant_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        file_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        file_name="doble_ci.pdf",
        processing_job_uuid=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        persist=True,
    )


async def _replay_standard(monkeypatch) -> tuple[list, PipelineState]:
    canned, _, _ = _load_golden()
    calls: list = []
    _patch_workflow_runtime(monkeypatch, calls, _make_canned(canned))
    state = PipelineState(data=_golden_input(), job_id=_JOB_ID)
    state = await execute_pipeline(ProcessingJobWorkflowBase(), _standard_phases(), state)
    return calls, state


# ─── Regresión: paridad con el golden del legacy ─────────────────────────────


async def test_standard_v1__activity_sequence_matches_golden(monkeypatch):
    # Arrange
    _, golden_sequence, _ = _load_golden()

    # Act
    calls, _ = await _replay_standard(monkeypatch)

    # Assert — paridad de orquestación, fingerprint a fingerprint y en orden
    expect(calls).to(have_length(len(golden_sequence)))
    for index, (got, expected) in enumerate(zip(calls, golden_sequence)):
        expect((index, got)).to(equal((index, expected)))


async def test_standard_v1__final_output_matches_golden(monkeypatch):
    # Arrange
    _, _, golden_state = _load_golden()

    # Act
    _, state = await _replay_standard(monkeypatch)

    # Assert — output final campo a campo (mensajes por campo, no un equal gigante)
    dumped = state.output.model_dump(mode="json")
    expect(sorted(dumped)).to(equal(sorted(golden_state)))
    for field, expected in golden_state.items():
        expect((field, dumped[field])).to(equal((field, expected)))


async def test_standard_v1__field_confidence_fingerprints_frozen(monkeypatch):
    """La paridad de ``field_confidence`` (keys pobladas + cuáles son bbox) que
    el golden congeló en los fingerprints de ``mark_document_status``."""
    # Arrange
    _, golden_sequence, _ = _load_golden()
    golden_marks = [c for c in golden_sequence if c[0] == MARK_DOCUMENT_STATUS_ACTIVITY]

    # Act
    calls, _ = await _replay_standard(monkeypatch)

    # Assert
    marks = [c for c in calls if c[0] == MARK_DOCUMENT_STATUS_ACTIVITY]
    expect(marks).to(have_length(2))  # doble_ci.pdf: dos cédulas, una por página
    expect(marks).to(equal(golden_marks))


async def test_standard_v1__emits_terminal_completed_webhook_last(monkeypatch):
    # Act
    calls, _ = await _replay_standard(monkeypatch)

    # Assert
    expect(calls[-1]).to(equal([DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY, "COMPLETED"]))


def test_phase_library__registers_all_standard_recipe_kinds():
    registered = set(PHASE_LIBRARY)

    for phase in standard_extraction_phases():
        expect((phase["kind"], phase["kind"] in registered)).to(equal((phase["kind"], True)))


# ─── Regresión: receta field-re-extraction@v1 (run extract-only) ─────────────


async def test_field_re_extraction__skips_ocr_classify_and_webhook(monkeypatch):
    """El run extract-only arranca con los artefactos del run original
    sembrados (como hace ``CaseFieldReExtractionStarter`` vía
    ``initial_artifacts``) y NO re-invoca OCR/clasificación ni re-dispara el
    webhook de finalize (``dispatch_webhook: False`` en la receta)."""
    # Arrange
    canned, _, _ = _load_golden()
    calls: list = []
    _patch_workflow_runtime(monkeypatch, calls, _make_canned(canned))
    persisted = [
        PersistedDocumentRef.model_validate(doc)
        for doc in canned["persist_classified_documents"]["documents"]
    ]
    state = PipelineState(
        data=_golden_input(),
        job_id=_JOB_ID,
        artifacts={
            "classify_pages": {"output_uri": canned["invoke_lambda"]["classify_pages"]["output_uri"]},
            "persisted_docs": persisted,
        },
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._seq = 13  # continúa el seq del set original (PipelineRunInput.starting_seq)
    phases = [PhaseSpec.model_validate(p) for p in field_re_extraction_phases()]

    # Act
    state = await execute_pipeline(ctx, phases, state)

    # Assert — sin re-OCR ni re-clasificación ni webhook. E4: extract_fields
    # se invoca una vez POR documento (2 en doble_ci.pdf) tras el split.
    names = _lambda_name_by_kind()
    invoked = [c[1] for c in calls if c[0] == INVOKE_LAMBDA_ACTIVITY]
    expect(invoked).to(
        equal(
            [
                names[PhaseKind.EXTRACT_FIELDS.value],
                names[PhaseKind.EXTRACT_FIELDS.value],
                names[PhaseKind.VALIDATE_EXTRACTION.value],
            ]
        )
    )
    splits = [c for c in calls if c[0] == SPLIT_CLASSIFIED_DOCS_ACTIVITY]
    expect(splits).to(have_length(1))
    webhook_calls = [c for c in calls if c[0] == DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY]
    expect(webhook_calls).to(have_length(0))
    # Los dos documentos se re-marcan COMPLETED y el seq continúa tras el 13 sembrado
    marks = [c for c in calls if c[0] == MARK_DOCUMENT_STATUS_ACTIVITY]
    expect(marks).to(have_length(2))
    first_update = next(c for c in calls if c[0] == UPDATE_WORKFLOW_PROCESSING_JOB_STATUS_ACTIVITY)
    expect(first_update[3]).to(equal(14))
    # Output bien formado aunque el run no tenga artefacto extract_text propio
    expect(state.output.extract_text_source).to(equal(""))
    expect(state.output.classify_pages_source).to(
        equal(canned["invoke_lambda"]["classify_pages"]["output_uri"])
    )
