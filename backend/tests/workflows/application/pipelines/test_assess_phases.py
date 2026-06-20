"""E3 · handler de la fase `assess` (label-only, 1 activity por documento).

Mismo harness que test_confidence_gate: el runtime de `temporalio.workflow`
se parchea y el handler se ejecuta directo. Se verifica el skip sin campos,
el contrato label-only (fallo de activity ⇒ warning + continúa) y el
checkpoint STEP_COMPLETED con el resumen {fields_assessed, flagged}.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from expects import be_empty, equal, expect, have_keys
from temporalio import workflow as tw

from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.enums.processing_job_events import ProcessingJobEventType
from src.workflows.application.pipelines import assess_phases as ap
from src.workflows.application.pipelines.runtime import PipelineState
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    AssessDocumentOutput,
    PersistedDocumentRef,
)

_DOC_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_DOC_ID_2 = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


class FakeCtx:
    """El handler solo usa `_checkpoint` del PhaseContext."""

    def __init__(self) -> None:
        self.checkpoints: list[dict] = []

    async def _checkpoint(self, data, **kwargs) -> None:
        self.checkpoints.append(kwargs)


def _patch(monkeypatch, *, record: list, results: dict | None = None, failing: set | None = None):
    results = results or {}
    failing = failing or set()

    async def fake_execute_activity(name, arg=None, **kwargs):
        record.append((name, arg))
        if name == ap.ASSESS_DOCUMENT_ACTIVITY:
            if str(arg.document_id) in failing:
                raise RuntimeError("activity exploded")
            return results.get(str(arg.document_id), AssessDocumentOutput())
        return None

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(
        tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    )


def _state(*, persist: bool = True, extractions: list | None = None, docs: list | None = None) -> PipelineState:
    data = DocumentProcessingInput(
        object_key="s3://b/in.pdf",
        document_types=[],
        job_id="JOB-1",
        workflow_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        processing_job_uuid=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        persist=persist,
    )
    state = PipelineState(data=data, job_id="JOB-1")
    state.extract_text = {"output_uri": "s3://b/jobs/JOB-1/extract_text.json"}
    state.extract_fields = {"extractions": extractions if extractions is not None else []}
    state.survivors = (
        docs
        if docs is not None
        else [PersistedDocumentRef(document_id=_DOC_ID, document_index=0, page_range={"from": 1, "to": 2})]
    )
    return state


def _entry(document_index: int = 0) -> dict:
    return {
        "document_index": document_index,
        "output": {"nombre": "Juan"},
        "mapped_output": {"nombre": {"value": "Juan", "bbox": [{"confidence": 0.9}]}},
    }


# ── compact_fields_for_assess ───────────────────────────────────────────────


def test_compact_fields__unwraps_mapped_leaves_dropping_bboxes():
    fields = ap.compact_fields_for_assess(_entry())

    expect(fields).to(equal({"nombre": "Juan"}))


def test_compact_fields__falls_back_to_raw_output():
    fields = ap.compact_fields_for_assess({"output": {"total": 100}, "mapped_output": None})

    expect(fields).to(equal({"total": 100}))


def test_compact_fields__degrades_to_scalars_when_entry_is_huge():
    huge_list = ["x" * 100] * 2000  # serializado > _MAX_FIELDS_CHARS
    entry = {"mapped_output": {"escalar": {"value": "ok"}, "gigante": {"value": huge_list}}}

    fields = ap.compact_fields_for_assess(entry)

    expect(fields).to(equal({"escalar": "ok"}))


# ── handler ─────────────────────────────────────────────────────────────────


async def test_assess__one_activity_per_document_and_checkpoint_summary(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        record=calls,
        results={str(_DOC_ID): AssessDocumentOutput(assessed=True, fields_assessed=1, flagged=["nombre"])},
    )
    ctx = FakeCtx()
    state = _state(extractions=[_entry()])

    await ap.assess(ctx, SimpleNamespace(config={}), state)

    assess_calls = [arg for name, arg in calls if name == ap.ASSESS_DOCUMENT_ACTIVITY]
    expect(len(assess_calls)).to(equal(1))
    expect(assess_calls[0].document_id).to(equal(_DOC_ID))
    expect(assess_calls[0].extract_text_source).to(equal("s3://b/jobs/JOB-1/extract_text.json"))
    expect(assess_calls[0].fields).to(equal({"nombre": "Juan"}))

    expect(len(ctx.checkpoints)).to(equal(1))
    expect(ctx.checkpoints[0]["type"]).to(equal(ProcessingJobEventType.STEP_COMPLETED))
    expect(ctx.checkpoints[0]["payload"]).to(
        have_keys(
            step="assess",
            summary={"fields_assessed": 1, "flagged": ["nombre"]},
        )
    )
    expect(state.scratch["assess"][str(_DOC_ID)]).to(
        equal({"fields_assessed": 1, "flagged": ["nombre"]})
    )


async def test_assess__skips_documents_without_extracted_fields(monkeypatch):
    calls: list = []
    _patch(monkeypatch, record=calls)
    ctx = FakeCtx()
    # entry sin output/mapped_output ⇒ skip barato, sin llamada LLM
    state = _state(extractions=[{"document_index": 0, "output": {}, "mapped_output": {}}])

    await ap.assess(ctx, SimpleNamespace(config={}), state)

    expect(calls).to(be_empty)
    expect(ctx.checkpoints).to(be_empty)


async def test_assess__label_only_activity_failure_never_fails_run(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        record=calls,
        results={str(_DOC_ID_2): AssessDocumentOutput(assessed=True, fields_assessed=1, flagged=[])},
        failing={str(_DOC_ID)},
    )
    ctx = FakeCtx()
    state = _state(
        extractions=[_entry(0), _entry(1)],
        docs=[
            PersistedDocumentRef(document_id=_DOC_ID, document_index=0),
            PersistedDocumentRef(document_id=_DOC_ID_2, document_index=1),
        ],
    )

    # no debe levantar pese al fallo del primer documento
    await ap.assess(ctx, SimpleNamespace(config={}), state)

    assess_calls = [arg for name, arg in calls if name == ap.ASSESS_DOCUMENT_ACTIVITY]
    expect(len(assess_calls)).to(equal(2))
    # solo el documento exitoso emite checkpoint y resumen
    expect(len(ctx.checkpoints)).to(equal(1))
    expect(ctx.checkpoints[0]["payload"]["document_id"]).to(equal(str(_DOC_ID_2)))
    expect(list(state.scratch["assess"])).to(equal([str(_DOC_ID_2)]))


async def test_assess__skips_entirely_without_extract_text_artifact(monkeypatch):
    calls: list = []
    _patch(monkeypatch, record=calls)
    ctx = FakeCtx()
    state = _state(extractions=[_entry()])
    state.extract_text = {}

    await ap.assess(ctx, SimpleNamespace(config={}), state)

    expect(calls).to(be_empty)


async def test_assess__skips_when_run_does_not_persist(monkeypatch):
    calls: list = []
    _patch(monkeypatch, record=calls)
    ctx = FakeCtx()
    state = _state(persist=False, extractions=[_entry()])

    await ap.assess(ctx, SimpleNamespace(config={}), state)

    expect(calls).to(be_empty)
