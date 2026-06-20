"""Unit tests del runtime del intérprete (E1).

Cubre el contrato generalizado de ``PipelineState`` (mapa de artefactos +
accessors tipados de la familia de extracción) y los fallos no reintentables de
``execute_pipeline`` (``pipeline.unknown_phase_kind``).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from expects import be_none, equal, expect
from temporalio import workflow as tw
from temporalio.exceptions import ApplicationError

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import (
    extraction_phases,  # noqa: F401 — side effect requerido: puebla PHASE_LIBRARY
)
from src.workflows.application.pipelines.runtime import (
    PHASE_LIBRARY,
    PipelineState,
    execute_pipeline,
)
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    PersistedDocumentRef,
)


def _state(**kwargs) -> PipelineState:
    return PipelineState(data=SimpleNamespace(), job_id="JOB-1", **kwargs)


def _silence_workflow_logger(monkeypatch) -> None:
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


# ─── PipelineState: mapa de artefactos genérico ──────────────────────────────


def test_pipeline_state__artifact_returns_default_when_missing():
    state = _state()

    expect(state.artifact("anything")).to(be_none)
    expect(state.artifact("anything", default={"x": 1})).to(equal({"x": 1}))


def test_pipeline_state__put_artifact_roundtrips():
    state = _state()

    state.put_artifact("my_phase", {"output_uri": "s3://b/x.json"})

    expect(state.artifact("my_phase")).to(equal({"output_uri": "s3://b/x.json"}))
    expect(state.artifacts["my_phase"]).to(equal({"output_uri": "s3://b/x.json"}))


@pytest.mark.parametrize(
    "prop",
    ["extract_text", "classify_pages", "extract_fields", "validate_extraction"],
)
def test_pipeline_state__dict_accessors_map_artifacts_key(prop):
    # El setter escribe bajo la clave homónima; el getter lee de artifacts.
    state = _state()
    value = {"output_uri": f"s3://b/{prop}.json"}

    setattr(state, prop, value)

    expect(state.artifacts[prop]).to(equal(value))
    expect(getattr(_state(artifacts={prop: value}), prop)).to(equal(value))
    expect(getattr(_state(), prop)).to(equal({}))  # default: dict vacío, nunca None


@pytest.mark.parametrize(
    ("prop", "key"),
    [
        ("documents", "classified_documents"),
        ("persisted_docs", "persisted_docs"),
        ("survivors", "survivors"),
        ("completed", "completed"),
    ],
)
def test_pipeline_state__list_accessors_map_artifacts_key(prop, key):
    state = _state()
    ref = PersistedDocumentRef(
        document_id=uuid4(),
        document_type_id=None,
        document_type_name="X",
        document_index=0,
        page_range={"from": 1, "to": 1},
    )

    setattr(state, prop, [ref])

    expect(state.artifacts[key]).to(equal([ref]))
    expect(getattr(_state(artifacts={key: [ref]}), prop)).to(equal([ref]))
    expect(getattr(_state(), prop)).to(equal([]))  # default: lista vacía, nunca None


def test_pipeline_state__initial_artifacts_feed_typed_accessors():
    # Lo que siembra la re-extracción vía PipelineRunInput.initial_artifacts.
    state = _state(artifacts={"classify_pages": {"output_uri": "s3://b/classify.json"}})

    expect(state.classify_pages).to(equal({"output_uri": "s3://b/classify.json"}))
    expect(state.extract_text).to(equal({}))


# ─── execute_pipeline: fallos no reintentables y control de flujo ────────────


async def test_execute_pipeline__unknown_phase_kind_raises_non_retryable_application_error(monkeypatch):
    # Tras E2 TODOS los kinds tienen handler: simulamos un deploy desfasado
    # (receta publicada con un kind cuyo handler aún no está registrado)
    # despoblando PHASE_LIBRARY para ese kind.
    monkeypatch.delitem(PHASE_LIBRARY, PhaseKind.ANALYZE.value, raising=False)
    expect(PhaseKind.ANALYZE.value in PHASE_LIBRARY).to(equal(False))
    phases = [PhaseSpec(id="analyze", kind=PhaseKind.ANALYZE)]

    with pytest.raises(ApplicationError) as exc_info:
        await execute_pipeline(SimpleNamespace(), phases, _state())

    expect(exc_info.value.type).to(equal("pipeline.unknown_phase_kind"))
    expect(exc_info.value.non_retryable).to(equal(True))


async def test_execute_pipeline__terminated_state_short_circuits(monkeypatch):
    _silence_workflow_logger(monkeypatch)
    ran: list[str] = []

    async def terminator(ctx, phase, state):
        ran.append(phase.id)
        state.terminated = True

    async def never_reached(ctx, phase, state):
        ran.append(phase.id)

    monkeypatch.setitem(PHASE_LIBRARY, PhaseKind.ENRICH.value, terminator)
    monkeypatch.setitem(PHASE_LIBRARY, PhaseKind.HUMAN_REVIEW.value, never_reached)
    phases = [
        PhaseSpec(id="first", kind=PhaseKind.ENRICH),
        PhaseSpec(id="second", kind=PhaseKind.HUMAN_REVIEW),
    ]

    await execute_pipeline(SimpleNamespace(), phases, _state())

    expect(ran).to(equal(["first"]))
