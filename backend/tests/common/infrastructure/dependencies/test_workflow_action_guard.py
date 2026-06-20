"""E5 · require_workflow_action: guard de la matriz rol×acción por ruta.

Se invoca la dependencia directamente (mismos params que inyecta FastAPI):
viewer ⇒ 403 en operate; member ⇒ 403 en manage; org sin fila ⇒ member
implícito pasa operate; private sin fila ⇒ 403; superficie tenant-level
(sin workflow_id en el path) ⇒ solo owner/admin.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import equal, expect

from src.common.domain.permissions.workflow_actions import WorkflowActionForbiddenError
from src.common.infrastructure.dependencies.workflow_access import require_workflow_action

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_USER = UUID("55555555-5555-5555-5555-555555555555")


class _FakeWorkflowRepo:
    def __init__(self, workflow):
        self._workflow = workflow

    async def find_by_id(self, workflow_id, tenant_id):
        return self._workflow


class _FakeMemberRepo:
    def __init__(self, member=None):
        self._member = member

    async def find(self, workflow_id, user_id, tenant_id):
        return self._member


class _FakeRuleRepo:
    def __init__(self, rule=None):
        self._rule = rule

    async def find_by_id(self, rule_id, tenant_id):
        return self._rule


def _ctx(workflow=None, member=None, rule=None):
    return SimpleNamespace(
        domain=SimpleNamespace(
            workflow_repository=_FakeWorkflowRepo(workflow),
            workflow_member_repository=_FakeMemberRepo(member),
            workflow_rule_repository=_FakeRuleRepo(rule),
        )
    )


def _request(**path_params):
    return SimpleNamespace(path_params=path_params)


def _tenant_user(*, is_owner=False, role_slug=None):
    tenant_role = SimpleNamespace(slug=role_slug) if role_slug else None
    return SimpleNamespace(is_owner=is_owner, tenant_role=tenant_role, user_id=_USER)


_TENANT_NS = SimpleNamespace(uuid=_TENANT)
_ORG_WORKFLOW = SimpleNamespace(uuid=_WORKFLOW, access_type="organization", created_by_id=None)
_PRIVATE_WORKFLOW = SimpleNamespace(uuid=_WORKFLOW, access_type="private", created_by_id=None)


async def test_viewer_gets_403_on_operate():
    guard = require_workflow_action("operate")
    with pytest.raises(WorkflowActionForbiddenError) as exc_info:
        await guard(
            _request(workflow_id=str(_WORKFLOW)),
            _ctx(_ORG_WORKFLOW, member=SimpleNamespace(role="viewer")),
            _TENANT_NS,
            _tenant_user(),
        )
    expect(exc_info.value.status_code).to(equal(403))
    expect(exc_info.value.context["role"]).to(equal("viewer"))


async def test_member_gets_403_on_manage():
    guard = require_workflow_action("manage")
    with pytest.raises(WorkflowActionForbiddenError):
        await guard(
            _request(workflow_id=str(_WORKFLOW)),
            _ctx(_ORG_WORKFLOW, member=SimpleNamespace(role="member")),
            _TENANT_NS,
            _tenant_user(),
        )


async def test_org_without_row_is_implicit_member_and_operates():
    guard = require_workflow_action("operate")
    # No levanta: member implícito en workflows organization (no-regresión).
    await guard(_request(workflow_id=str(_WORKFLOW)), _ctx(_ORG_WORKFLOW), _TENANT_NS, _tenant_user())


async def test_private_without_row_gets_403_even_for_view():
    guard = require_workflow_action("view")
    with pytest.raises(WorkflowActionForbiddenError):
        await guard(
            _request(workflow_id=str(_WORKFLOW)), _ctx(_PRIVATE_WORKFLOW), _TENANT_NS, _tenant_user()
        )


async def test_tenant_admin_passes_manage():
    guard = require_workflow_action("manage")
    await guard(
        _request(workflow_id=str(_WORKFLOW)),
        _ctx(_ORG_WORKFLOW),
        _TENANT_NS,
        _tenant_user(role_slug="admin"),
    )


async def test_rule_route_resolves_workflow_via_rule_id():
    guard = require_workflow_action("manage")
    rule = SimpleNamespace(uuid=uuid4(), workflow_id=_WORKFLOW)
    with pytest.raises(WorkflowActionForbiddenError):
        await guard(
            _request(rule_id=str(rule.uuid)),
            _ctx(_ORG_WORKFLOW, member=SimpleNamespace(role="member"), rule=rule),
            _TENANT_NS,
            _tenant_user(),
        )


async def test_tenant_level_surface_requires_tenant_admin():
    guard = require_workflow_action("manage")
    with pytest.raises(WorkflowActionForbiddenError):
        await guard(_request(), _ctx(), _TENANT_NS, _tenant_user())
    await guard(_request(), _ctx(), _TENANT_NS, _tenant_user(is_owner=True))
