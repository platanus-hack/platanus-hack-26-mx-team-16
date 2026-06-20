"""E7 · F3: endpoint del wizard «agregar capacidad».

Inserta las fases de la capacidad sobre la versión vigente y publica v+1 (mismo
camino que el editor). Idempotente a nivel API: capacidad presente ⇒ 409.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from expects import contain, equal, expect, have_keys

import src.workflows.presentation.endpoints.pipeline_admin as admin
from src.common.domain.enums.pipelines import PipelineKind
from src.workflows.domain.models.pipeline import PhaseSpec, Pipeline, PipelineVersion
from src.workflows.domain.recipes import standard_analysis_phases, standard_extraction_phases
from src.workflows.presentation.endpoints.pipeline_admin import (
    AddCapabilityRequest,
    add_workflow_capability,
)


def _tenant():
    return SimpleNamespace(uuid=uuid4())


def _payload(response) -> dict:
    body = json.loads(response.body)
    return body.get("data", body)


def _patch_repo(monkeypatch, repo):
    monkeypatch.setattr(admin, "SQLPipelineRepository", lambda session: repo)


def _pipeline(current_version: int | None = 1) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=uuid4(),
        tenant_id=uuid4(),
        slug="wf-pipeline",
        name="WF pipeline",
        kind=PipelineKind.EXTRACTION,
        current_version=current_version,
    )


def _version(pipeline: Pipeline, phases: list[dict]) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=pipeline.uuid,
        version=pipeline.current_version,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


def _repo(monkeypatch, *, pipeline=None, current=None):
    repo = MagicMock()
    repo.find_by_workflow = AsyncMock(return_value=pipeline)
    repo.get_version = AsyncMock(return_value=current)
    repo.add_version = AsyncMock(side_effect=lambda version: version)
    repo.upsert = AsyncMock(side_effect=lambda p: p)
    _patch_repo(monkeypatch, repo)
    return repo


async def test_add_capability__publishes_next_version_with_the_phase(monkeypatch):
    pipeline = _pipeline(current_version=1)
    repo = _repo(monkeypatch, pipeline=pipeline, current=_version(pipeline, standard_extraction_phases()))

    response = await add_workflow_capability(
        workflow_id=uuid4(),
        request=AddCapabilityRequest(capability="analysis"),
        session=MagicMock(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(201))
    payload = _payload(response)
    expect(payload).to(have_keys("version", "addedCapability", "capabilities"))
    expect(payload["version"]).to(equal(2))
    expect(payload["addedCapability"]).to(equal("analysis"))
    expect(payload["capabilities"]).to(contain("analysis"))
    sealed = repo.add_version.call_args.args[0]
    expect("analyze" in [p.kind.value for p in sealed.phases]).to(equal(True))
    expect(sealed.version).to(equal(2))
    repo.upsert.assert_awaited_once()


async def test_add_capability__409_when_already_present(monkeypatch):
    pipeline = _pipeline(current_version=3)
    # standard_analysis ya tiene analyze ⇒ analysis no es agregable.
    repo = _repo(monkeypatch, pipeline=pipeline, current=_version(pipeline, standard_analysis_phases()))

    response = await add_workflow_capability(
        workflow_id=uuid4(),
        request=AddCapabilityRequest(capability="analysis"),
        session=MagicMock(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(409))
    repo.add_version.assert_not_called()


async def test_add_capability__422_unknown_capability(monkeypatch):
    _repo(monkeypatch, pipeline=_pipeline(), current=None)

    response = await add_workflow_capability(
        workflow_id=uuid4(),
        request=AddCapabilityRequest(capability="teleport"),
        session=MagicMock(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(422))
    expect(_payload(response)["error"]).to(equal("capability.unknown"))


async def test_add_capability__422_base_extraction_not_addable(monkeypatch):
    _repo(monkeypatch, pipeline=_pipeline(), current=None)

    response = await add_workflow_capability(
        workflow_id=uuid4(),
        request=AddCapabilityRequest(capability="extraction"),
        session=MagicMock(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(422))
    expect(_payload(response)["error"]).to(equal("capability.not_addable"))


async def test_add_capability__404_when_pipeline_missing(monkeypatch):
    repo = _repo(monkeypatch, pipeline=None, current=None)

    response = await add_workflow_capability(
        workflow_id=uuid4(),
        request=AddCapabilityRequest(capability="analysis"),
        session=MagicMock(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(404))
    repo.add_version.assert_not_called()
