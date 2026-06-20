"""E5 · §C4 — endurecimiento del endpoint M2M ``/v1/tasks/{id}/resolve``.

El M2M (API key) sólo debe resolver el gate único E4 (``stage=None``); las
tareas de revisión L1/L2 exigen un actor humano (L1 staff, L2 tenant con
``approve``). Para el gate que sí sirve, debe pasar un actor explícito
(atribución) y el repo de documentos (reactiva el invariante open_flags §3.4).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.presentation.endpoints import m2m_control
from src.workflows.presentation.endpoints.m2m_control import (
    M2MStageForbiddenError,
    ResolveTaskRequest,
    resolve_task_m2m,
)

_TENANT = uuid4()


def _tenant() -> SimpleNamespace:
    return SimpleNamespace(uuid=_TENANT)


def _task(stage: str | None) -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-1:gate",
        kind=HumanTaskKind.APPROVAL,
        status=HumanTaskStatus.PENDING,
        stage=stage,
        pipeline_run_id="run-1",
    )


class _FakeTaskRepo:
    def __init__(self, task: HumanTask | None):
        self._task = task

    async def find_by_id(self, task_id, tenant_id):
        return self._task


def _patch_repos(monkeypatch, task: HumanTask | None):
    monkeypatch.setattr(
        m2m_control, "SQLHumanTaskRepository", lambda session: _FakeTaskRepo(task)
    )
    doc_repo_sentinel = SimpleNamespace(_marker="doc-repo")
    monkeypatch.setattr(
        m2m_control,
        "SQLWorkflowDocumentRepository",
        lambda session: doc_repo_sentinel,
    )
    return doc_repo_sentinel


class _ResolveSpy:
    """Captura los kwargs con que se construye ResolveHumanTask y no toca DB."""

    last_kwargs: dict = {}

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs

    async def execute(self):
        return None


async def test_resolve_task_m2m__rejects_staged_task_with_403(monkeypatch):
    _patch_repos(monkeypatch, _task(stage="review_l1"))
    monkeypatch.setattr(m2m_control, "ResolveHumanTask", _ResolveSpy)

    with pytest.raises(M2MStageForbiddenError) as exc_info:
        await resolve_task_m2m(
            task_id=uuid4(),
            request=ResolveTaskRequest(resolution={"approved": True}),
            session=object(),
            temporal_client=object(),
            tenant=_tenant(),
        )

    expect(exc_info.value.status_code).to(equal(403))
    expect(exc_info.value.context["stage"]).to(equal("review_l1"))


async def test_resolve_task_m2m__rejects_review_l2_too(monkeypatch):
    _patch_repos(monkeypatch, _task(stage="review_l2"))
    monkeypatch.setattr(m2m_control, "ResolveHumanTask", _ResolveSpy)

    with pytest.raises(M2MStageForbiddenError) as exc_info:
        await resolve_task_m2m(
            task_id=uuid4(),
            request=ResolveTaskRequest(resolution={"approved": True}),
            session=object(),
            temporal_client=object(),
            tenant=_tenant(),
        )

    expect(exc_info.value.status_code).to(equal(403))
    expect(exc_info.value.context["stage"]).to(equal("review_l2"))


async def test_resolve_task_m2m__stage_none_passes_actor_and_doc_repo(monkeypatch):
    doc_repo = _patch_repos(monkeypatch, _task(stage=None))
    monkeypatch.setattr(m2m_control, "ResolveHumanTask", _ResolveSpy)

    response = await resolve_task_m2m(
        task_id=uuid4(),
        request=ResolveTaskRequest(resolution={"approved": True}),
        session=object(),
        temporal_client=object(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(200))
    # Actor explícito (atribución) + repo de documentos (reactiva open_flags).
    expect(_ResolveSpy.last_kwargs["actor"]).to(equal("external:apikey"))
    expect(_ResolveSpy.last_kwargs["document_repository"]).to(equal(doc_repo))


async def test_resolve_task_m2m__missing_task_returns_404(monkeypatch):
    _patch_repos(monkeypatch, None)
    monkeypatch.setattr(m2m_control, "ResolveHumanTask", _ResolveSpy)

    response = await resolve_task_m2m(
        task_id=uuid4(),
        request=ResolveTaskRequest(resolution={"approved": True}),
        session=object(),
        temporal_client=object(),
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(404))
