"""E4 · extract_fields por documento — tests del handler.

El handler invoca la Lambda UNA VEZ POR documento clasificado (slices S3 de
``split_classified_documents``) en vez del batch único pre-E4. Aquí se prueba
el contrato nuevo a nivel handler con un ctx fake:

- una invocación por doc, schedule estable en orden de ``document_index``,
- payload por invocación idéntico al contrato batch (``source_uri`` del slice
  + ``job_id`` + ``inline_response``),
- fusión que re-mapea el ``document_index: 0`` que devuelve la Lambda para un
  payload de 1 doc al índice ORIGINAL, conservando el shape exacto del
  artefacto (``{status, extractions, errors, metadata}``),
- un doc que falla ⇒ ``_fail_document`` y el resto continúa; TODOS fallan ⇒
  ``_fail_job`` + raise (comportamiento de fase, como el batch).

La paridad de orquestación completa vive en ``test_standard_v1_regression.py``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_empty, equal, expect, have_length
from temporalio import workflow as tw

from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingInput,
)
from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import (
    extraction_phases,  # noqa: F401 — side effect requerido: puebla PHASE_LIBRARY
)
from src.workflows.application.pipelines.runtime import PHASE_LIBRARY, PipelineState
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import standard_extraction_phases
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    PersistedDocumentRef,
    SplitClassifiedDocumentsOutput,
    SplitDocumentRef,
)
from src.workflows.presentation.workflows.base import SPLIT_CLASSIFIED_DOCS_ACTIVITY

_JOB_ID = "CASE#11111111111111111111111111111111_FILE#22222222222222222222222222222222"
_CLASSIFY_URI = "s3://bucket/jobs/run-1/classify_pages.json"


def _uri(index: int) -> str:
    return f"s3://bucket/jobs/run-1/classify_pages.doc_{index:03d}.json"


def _doc(index: int) -> PersistedDocumentRef:
    return PersistedDocumentRef(
        document_id=UUID(int=index + 1),
        document_type_id=uuid4(),
        document_type_name="Cedula de Identidad",
        document_index=index,
        page_range={"from": index + 1, "to": index + 1},
    )


def _lambda_response(value: str, process_time: float = 1.5) -> dict:
    """Respuesta de la Lambda para UN doc: re-indexa su entry como 0 (enumerate)."""
    return {
        "status": "success",
        "extractions": [
            {
                "document_type": {"uuid": "36aab742-879e-4a3b-b688-5bdb5702ac0b", "name": "Cedula"},
                "document_index": 0,
                "output": {"nombres": value},
                "mapped_output": {"nombres": {"value": value, "source_text": value, "page_number": 1}},
            }
        ],
        "errors": [],
        "metadata": {"process_time": process_time, "total": 1, "succeeded": 1, "failed": 0, "job_id": _JOB_ID},
    }


class _FakeCtx:
    """PhaseContext fake: registra checkpoints/invocaciones/fallos en orden."""

    def __init__(self, lambda_results: dict[str, dict | Exception]):
        self.lambda_results = lambda_results
        self.ops: list[tuple] = []
        self.invocations: list[dict] = []
        self.failed_docs: list[tuple[int, dict]] = []
        self.failed_jobs: list = []

    async def _checkpoint(self, data, **kwargs) -> None:
        self.ops.append(("checkpoint", str(kwargs.get("document_id"))))

    async def _invoke_lambda(self, function_name: str, payload: dict, timeout, label: str) -> dict:
        self.ops.append(("invoke", payload["source_uri"]))
        self.invocations.append({"function_name": function_name, "payload": payload, "label": label})
        result = self.lambda_results[payload["source_uri"]]
        if isinstance(result, Exception):
            raise result
        return result

    async def _fail_document(self, data, doc, source_step, err: dict) -> None:
        self.failed_docs.append((doc.document_index, err))

    async def _fail_job(self, data, source_step, exc) -> None:
        self.failed_jobs.append((source_step, exc))


def _phase() -> PhaseSpec:
    spec = next(p for p in standard_extraction_phases() if p["kind"] == PhaseKind.EXTRACT_FIELDS.value)
    return PhaseSpec.model_validate(spec)


def _state(docs: list[PersistedDocumentRef]) -> PipelineState:
    data = DocumentProcessingInput(
        object_key="s3://bucket/samples/tres_docs.pdf",
        document_types=[{"uuid": "36aab742-879e-4a3b-b688-5bdb5702ac0b", "name": "Cedula"}],
        job_id=_JOB_ID,
    )
    return PipelineState(
        data=data,
        job_id=_JOB_ID,
        artifacts={"classify_pages": {"output_uri": _CLASSIFY_URI}, "persisted_docs": docs},
    )


def _patch_split(monkeypatch, indexes: list[int]) -> None:
    split = SplitClassifiedDocumentsOutput(
        documents=[SplitDocumentRef(document_index=i, source_uri=_uri(i)) for i in indexes]
    )

    async def fake_execute_activity(name, arg=None, **kwargs):
        expect(name).to(equal(SPLIT_CLASSIFIED_DOCS_ACTIVITY))
        expect(arg.source).to(equal(_CLASSIFY_URI))
        return split

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)


async def _run(ctx: _FakeCtx, state: PipelineState) -> None:
    await PHASE_LIBRARY[PhaseKind.EXTRACT_FIELDS.value](ctx, _phase(), state)


# ─── Happy path multi-doc ────────────────────────────────────────────────────


async def test_extract_fields__invokes_lambda_once_per_document_in_index_order(monkeypatch):
    # Arrange — persisted_docs deliberadamente desordenado: el schedule debe
    # ser estable por document_index (determinismo Temporal).
    docs = [_doc(2), _doc(0), _doc(1)]
    _patch_split(monkeypatch, [0, 1, 2])
    ctx = _FakeCtx({_uri(i): _lambda_response(f"DOC-{i}") for i in range(3)})
    state = _state(docs)

    # Act
    await _run(ctx, state)

    # Assert — 3 invocaciones, en orden de document_index
    expect(ctx.invocations).to(have_length(3))
    expect([i["payload"]["source_uri"] for i in ctx.invocations]).to(equal([_uri(0), _uri(1), _uri(2)]))
    # Payload por doc: MISMO contrato que el batch (source_uri/job_id/inline_response)
    for index, invocation in enumerate(ctx.invocations):
        expect(invocation["payload"]).to(
            equal({"source_uri": _uri(index), "job_id": _JOB_ID, "inline_response": True})
        )
        # activity_id único por doc (Temporal exige ids únicos en vuelo)
        expect(invocation["label"]).to(equal(f"extract_fields:{index}"))


async def test_extract_fields__checkpoints_step_started_per_doc_before_any_invocation(monkeypatch):
    # Arrange
    docs = [_doc(0), _doc(1), _doc(2)]
    _patch_split(monkeypatch, [0, 1, 2])
    ctx = _FakeCtx({_uri(i): _lambda_response(f"DOC-{i}") for i in range(3)})

    # Act
    await _run(ctx, _state(docs))

    # Assert — la progresión SSE no cambia: N STEP_STARTED (uno por doc, en
    # orden) ANTES de cualquier invocación, como hacía el handler batch.
    kinds = [op[0] for op in ctx.ops]
    expect(kinds).to(equal(["checkpoint"] * 3 + ["invoke"] * 3))
    expect([op[1] for op in ctx.ops[:3]]).to(equal([str(UUID(int=1)), str(UUID(int=2)), str(UUID(int=3))]))


async def test_extract_fields__merges_remapping_lambda_zero_index_to_original(monkeypatch):
    # Arrange
    docs = [_doc(0), _doc(1), _doc(2)]
    _patch_split(monkeypatch, [0, 1, 2])
    ctx = _FakeCtx({_uri(i): _lambda_response(f"DOC-{i}", process_time=0.5) for i in range(3)})
    state = _state(docs)

    # Act
    await _run(ctx, state)

    # Assert — shape EXACTO del artefacto batch, con índices originales
    artifact = state.extract_fields
    expect(sorted(artifact)).to(equal(["errors", "extractions", "metadata", "status"]))
    expect(artifact["status"]).to(equal("success"))
    expect(artifact["errors"]).to(be_empty)
    expect([e["document_index"] for e in artifact["extractions"]]).to(equal([0, 1, 2]))
    for index, entry in enumerate(artifact["extractions"]):
        # Cada entry conserva TODAS las claves del shape Lambda (document_type,
        # output, mapped_output) — solo se re-mapea el document_index.
        expect(entry["output"]).to(equal({"nombres": f"DOC-{index}"}))
        expect(sorted(entry)).to(equal(["document_index", "document_type", "mapped_output", "output"]))
    expect(artifact["metadata"]).to(
        equal({"process_time": 1.5, "total": 3, "succeeded": 3, "failed": 0, "job_id": _JOB_ID})
    )
    # Todos sobreviven a validate_extraction
    expect([d.document_index for d in state.survivors]).to(equal([0, 1, 2]))
    expect(ctx.failed_docs).to(be_empty)
    expect(ctx.failed_jobs).to(be_empty)


# ─── Fallos por documento ────────────────────────────────────────────────────


async def test_extract_fields__one_failed_document_does_not_kill_the_run(monkeypatch):
    # Arrange — el doc 1 falla (la Lambda de 1 doc reporta all_failed ⇒ la
    # activity revienta); 0 y 2 siguen.
    docs = [_doc(0), _doc(1), _doc(2)]
    _patch_split(monkeypatch, [0, 1, 2])
    ctx = _FakeCtx(
        {
            _uri(0): _lambda_response("DOC-0"),
            _uri(1): RuntimeError("[extract_fields.all_failed] doc 1 reventó"),
            _uri(2): _lambda_response("DOC-2"),
        }
    )
    state = _state(docs)

    # Act — no debe levantar
    await _run(ctx, state)

    # Assert — solo el doc 1 se falla individualmente
    expect(ctx.failed_jobs).to(be_empty)
    expect(ctx.failed_docs).to(have_length(1))
    failed_index, err = ctx.failed_docs[0]
    expect(failed_index).to(equal(1))
    expect(err["document_index"]).to(equal(1))
    expect(err["error_type"]).to(equal("RuntimeError"))

    artifact = state.extract_fields
    expect(artifact["status"]).to(equal("partial"))
    expect([e["document_index"] for e in artifact["extractions"]]).to(equal([0, 2]))
    expect([e["document_index"] for e in artifact["errors"]]).to(equal([1]))
    expect(artifact["metadata"]["succeeded"]).to(equal(2))
    expect(artifact["metadata"]["failed"]).to(equal(1))
    expect(artifact["metadata"]["total"]).to(equal(3))
    expect([d.document_index for d in state.survivors]).to(equal([0, 2]))


async def test_extract_fields__all_failed_fails_the_phase_like_the_old_batch(monkeypatch):
    # Arrange
    docs = [_doc(0), _doc(1)]
    _patch_split(monkeypatch, [0, 1])
    boom_0, boom_1 = RuntimeError("doc 0"), RuntimeError("doc 1")
    ctx = _FakeCtx({_uri(0): boom_0, _uri(1): boom_1})
    state = _state(docs)

    # Act / Assert — comportamiento de fallo de FASE: _fail_job + raise
    with pytest.raises(RuntimeError):
        await _run(ctx, state)
    expect(ctx.failed_jobs).to(have_length(1))
    expect(ctx.failed_jobs[0][1]).to(equal(boom_0))
    # El artefacto no se escribe y nadie sobrevive
    expect(state.extract_fields).to(equal({}))
    expect(state.survivors).to(be_empty)


async def test_extract_fields__split_failure_fails_the_job_and_raises(monkeypatch):
    # Arrange
    docs = [_doc(0)]
    boom = RuntimeError("S3 caput")

    async def failing_execute_activity(name, arg=None, **kwargs):
        raise boom

    monkeypatch.setattr(tw, "execute_activity", failing_execute_activity)
    ctx = _FakeCtx({})
    state = _state(docs)

    # Act / Assert
    with pytest.raises(RuntimeError):
        await _run(ctx, state)
    expect(ctx.failed_jobs).to(have_length(1))
    expect(ctx.invocations).to(be_empty)


async def test_extract_fields__doc_missing_from_split_is_failed_individually(monkeypatch):
    # Arrange — el split no trae slice para el doc 1 (corrupción recuperable):
    # se falla SOLO ese doc, sin invocar la Lambda para él.
    docs = [_doc(0), _doc(1)]
    _patch_split(monkeypatch, [0])
    ctx = _FakeCtx({_uri(0): _lambda_response("DOC-0")})
    state = _state(docs)

    # Act
    await _run(ctx, state)

    # Assert
    expect(ctx.invocations).to(have_length(1))
    expect(ctx.failed_docs).to(have_length(1))
    expect(ctx.failed_docs[0][0]).to(equal(1))
    expect([d.document_index for d in state.survivors]).to(equal([0]))
    expect(state.extract_fields["status"]).to(equal("partial"))


async def test_extract_fields__document_types_subset_only_extracts_listed_types(monkeypatch):
    # phases-config · extract_fields.document_types: solo el subconjunto se extrae.
    cedula = PersistedDocumentRef(
        document_id=UUID(int=1), document_type_name="Cedula", document_index=0, page_range={"from": 1, "to": 1}
    )
    factura = PersistedDocumentRef(
        document_id=UUID(int=2), document_type_name="Factura", document_index=1, page_range={"from": 2, "to": 2}
    )
    _patch_split(monkeypatch, [0, 1])
    ctx = _FakeCtx({_uri(0): _lambda_response("CEDULA"), _uri(1): _lambda_response("FACTURA")})
    state = _state([cedula, factura])
    phase = PhaseSpec(id="extract_fields", kind=PhaseKind.EXTRACT_FIELDS, config={"document_types": ["Cedula"]})

    await PHASE_LIBRARY[PhaseKind.EXTRACT_FIELDS.value](ctx, phase, state)

    # solo el doc Cedula (index 0) recibe la Lambda; el Factura (index 1) se omite.
    expect(ctx.invocations).to(have_length(1))
    expect(ctx.invocations[0]["payload"]["source_uri"]).to(equal(_uri(0)))
