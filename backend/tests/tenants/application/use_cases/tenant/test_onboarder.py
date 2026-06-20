"""Tests for the onboarder. The per-member invitation behavior (skip
existing, requires_password derivation, normalization, email dispatch)
is covered in `tests/.../invitations/test_invite_members.py` since
:class:`TenantOnboarder` delegates to :class:`InviteTenantMembers`.
"""

from unittest.mock import create_autospec, patch
from uuid import uuid4

import pytest
from expects import equal, expect, have_len

from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.industries import IndustryNotFoundError
from src.common.domain.models.industry import Industry
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.tenants.application.use_cases.tenant.onboarder import (
    OnboardingMemberInput,
    TenantOnboarder,
)
from src.workflows.domain.repositories.pipeline import PipelineRepository


@pytest.fixture
def owner():
    return User(uuid=uuid4(), username="owner", first_name="Owner")


@pytest.fixture
def admin_role(tenant_id):
    return TenantRole(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Admin",
        slug="admin",
        status=TenantRoleStatus.ACTIVE,
    )


@pytest.fixture
def owner_tenant_user(owner, tenant_id):
    return TenantUser(
        uuid=uuid4(),
        user_id=owner.uuid,
        tenant_id=tenant_id,
        is_owner=True,
        is_support=False,
        status=TenantUserStatus.ACTIVE,
    )


@pytest.fixture
def use_case(
    owner,
    tenant,
    admin_role,
    owner_tenant_user,
    command_bus,
    tenant_repository,
    tenant_role_repository,
    tenant_user_repository,
    tenant_user_invitation_repository,
    user_repository,
    industry_repository,
):
    tenant_role_repository.find_by_slug.return_value = admin_role
    lookups = {(owner.uuid, tenant.uuid): owner_tenant_user}

    async def fake_find_by_args(user_id, tenant_id, status=None):
        return lookups.get((user_id, tenant_id))

    tenant_user_repository.find_by_args.side_effect = fake_find_by_args
    tenant_user_repository.persist.side_effect = lambda instance: instance
    user_repository.find_by_email.return_value = None
    tenant_user_invitation_repository.persist_many.side_effect = lambda drafts: drafts
    return TenantOnboarder(
        name="Acme",
        owner=owner,
        country_code=CountryIsoCode.MEXICO,
        members=[],
        command_bus=command_bus,
        tenant_repository=tenant_repository,
        tenant_role_repository=tenant_role_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        user_repository=user_repository,
        industry_repository=industry_repository,
    )


def _patched_registerer(tenant):
    """Skip the real `TenantRegisterer` so these tests stay focused on
    the onboarder's wiring (owner-as-support + delegation to the
    invitations use case)."""

    class _Registerer:
        def __init__(self, **_kwargs):
            pass

        async def execute(self):
            return tenant

    return patch(
        "src.tenants.application.use_cases.tenant.onboarder.TenantRegisterer",
        _Registerer,
    )


async def test_execute__no_members_returns_empty_invitations(use_case, tenant):
    with _patched_registerer(tenant):
        result = await use_case.execute()

    expect(result.tenant.uuid).to(equal(tenant.uuid))
    expect(result.invitations).to(have_len(0))
    expect(result.skipped_existing_members).to(have_len(0))


async def test_execute__flips_owner_to_support(
    use_case, tenant, owner_tenant_user, tenant_user_repository
):
    with _patched_registerer(tenant):
        await use_case.execute()

    persisted_owner_call = tenant_user_repository.persist.call_args_list[0]
    persisted = persisted_owner_call.args[0]
    expect(persisted.uuid).to(equal(owner_tenant_user.uuid))
    expect(persisted.is_support).to(equal(True))


async def test_execute__delegates_member_invitations(
    use_case, tenant, tenant_user_invitation_repository
):
    """Integration check: the onboarder hands off to InviteTenantMembers,
    which produces one invitation per listed member."""
    use_case.members = [
        OnboardingMemberInput(email="a@test.com", role_slug="admin"),
        OnboardingMemberInput(email="b@test.com", role_slug="admin"),
    ]

    with _patched_registerer(tenant):
        result = await use_case.execute()

    expect(result.invitations).to(have_len(2))
    expect({inv.email for inv in result.invitations}).to(
        equal({"a@test.com", "b@test.com"})
    )
    tenant_user_invitation_repository.persist_many.assert_called_once()


async def test_execute__skip_email_propagates_to_inviter(
    use_case, tenant, command_bus
):
    use_case.skip_email = True
    use_case.members = [OnboardingMemberInput(email="a@test.com", role_slug="admin")]

    with _patched_registerer(tenant):
        await use_case.execute()

    command_bus.dispatch.assert_not_called()


# ---------- industry ------------------------------------------------------


async def test_execute__no_industry_id_does_not_touch_industry_repo(
    use_case, tenant, industry_repository
):
    with _patched_registerer(tenant):
        await use_case.execute()

    industry_repository.find_by_id.assert_not_called()
    industry_repository.assign_to_tenant.assert_not_called()


async def test_execute__industry_id_provided_assigns_to_tenant(
    use_case, tenant, industry_repository
):
    industry = Industry(
        uuid=uuid4(), slug="finance", name="Finance"
    )
    industry_repository.find_by_id.return_value = industry
    use_case.industry_id = industry.uuid

    with _patched_registerer(tenant):
        await use_case.execute()

    industry_repository.find_by_id.assert_called_once_with(industry.uuid)
    industry_repository.assign_to_tenant.assert_called_once_with(
        tenant_id=tenant.uuid,
        industry_id=industry.uuid,
    )


async def test_execute__unknown_industry_id_raises(
    use_case, tenant, industry_repository
):
    industry_repository.find_by_id.return_value = None
    use_case.industry_id = uuid4()

    with _patched_registerer(tenant), pytest.raises(IndustryNotFoundError):
        await use_case.execute()

    industry_repository.assign_to_tenant.assert_not_called()


# ---------- pipeline seeding (ADR 0002) -----------------------------------


@pytest.fixture
def pipeline_repository():
    return create_autospec(spec=PipelineRepository, spec_set=True, instance=True)


async def test_execute__does_not_seed_pipelines(
    use_case, tenant, pipeline_repository
):
    # Arrange — ADR 0002: el onboarder ya NO siembra pipelines tenant-level.
    # Cada workflow nace dueño de su pipeline (copy-on-create en WorkflowCreator),
    # así que el onboarding no debe tocar el repo de pipelines.
    use_case.pipeline_repository = pipeline_repository

    # Act
    with _patched_registerer(tenant):
        await use_case.execute()

    # Assert — ni upsert ni add_version se invocan durante el onboarding.
    pipeline_repository.upsert.assert_not_awaited()
    pipeline_repository.add_version.assert_not_awaited()


async def test_execute__without_pipeline_repository_does_not_fail(use_case, tenant):
    # Arrange — wiring viejo sin repo de pipelines: el onboarding no explota
    use_case.pipeline_repository = None

    # Act
    with _patched_registerer(tenant):
        result = await use_case.execute()

    # Assert
    expect(result.tenant.uuid).to(equal(tenant.uuid))
