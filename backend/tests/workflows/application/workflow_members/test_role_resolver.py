"""E5 · ResolveWorkflowRole: rol efectivo según diseño §5.

tenant owner/admin ⇒ admin; miembro explícito ⇒ su rol (también en org);
creador ⇒ admin (paridad EnsureWorkflowAccess); org sin fila ⇒ member
implícito; private sin fila ⇒ None (sin acceso).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.workflows.application.workflow_members.role_resolver import ResolveWorkflowRole

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_USER = UUID("55555555-5555-5555-5555-555555555555")


def _workflow(access_type="organization", created_by_id=None):
    return SimpleNamespace(uuid=_WORKFLOW, access_type=access_type, created_by_id=created_by_id)


def _tenant_user(*, is_owner=False, role_slug=None):
    tenant_role = SimpleNamespace(slug=role_slug) if role_slug else None
    return SimpleNamespace(is_owner=is_owner, tenant_role=tenant_role, user_id=_USER)


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


def _resolver(workflow, tenant_user, member=None):
    return ResolveWorkflowRole(
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        tenant_user=tenant_user,
        workflow_repository=_FakeWorkflowRepo(workflow),
        member_repository=_FakeMemberRepo(member),
    )


async def test_tenant_owner_is_admin_everywhere():
    role = await _resolver(_workflow("private"), _tenant_user(is_owner=True)).execute()
    expect(role).to(equal("admin"))


async def test_tenant_admin_role_is_admin_everywhere():
    role = await _resolver(_workflow("private"), _tenant_user(role_slug="admin")).execute()
    expect(role).to(equal("admin"))


async def test_explicit_member_keeps_its_row_role_even_in_org_workflow():
    member = SimpleNamespace(role="viewer")
    role = await _resolver(_workflow("organization"), _tenant_user(), member).execute()
    expect(role).to(equal("viewer"))


async def test_org_workflow_without_row_is_implicit_member():
    role = await _resolver(_workflow("organization"), _tenant_user()).execute()
    expect(role).to(equal("member"))


async def test_private_workflow_without_row_has_no_access():
    role = await _resolver(_workflow("private"), _tenant_user()).execute()
    expect(role).to(be_none)


async def test_creator_is_admin_of_its_workflow():
    role = await _resolver(
        _workflow("private", created_by_id=_USER), _tenant_user()
    ).execute()
    expect(role).to(equal("admin"))


async def test_missing_workflow_raises_404():
    with pytest.raises(WorkflowNotFoundError):
        await _resolver(None, _tenant_user()).execute()
