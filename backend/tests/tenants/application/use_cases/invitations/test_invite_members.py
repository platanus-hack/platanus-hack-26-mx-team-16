from uuid import uuid4

import pytest
from expects import be_a, equal, expect, have_len

from src.common.application.commands.common import SendEmailCommand
from src.common.domain.enums.tenants import (
    TenantRoleStatus,
    TenantUserInvitationStatus,
)
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.common.domain.models.user import User
from src.tenants.application.use_cases.invitations.invite_members import (
    InviteTenantMembers,
    MemberInvitationInput,
    SkippedExistingMember,
)


@pytest.fixture
def invited_by():
    return User(uuid=uuid4(), username="inviter")


@pytest.fixture
def admin_role(tenant_id):
    return TenantRole(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Admin",
        slug="admin",
        status=TenantRoleStatus.ACTIVE,
    )


def _make_use_case(
    *,
    tenant,
    invited_by_user_id,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
    members=None,
    skip_email: bool = False,
    existing_members: dict | None = None,
):
    """Helper that wires the repos with safe defaults. `user_repository`
    must be configured by the caller — defaulting it here would silently
    overwrite per-test setup."""
    tenant_role_repository.find_by_slug.return_value = admin_role
    existing_members = existing_members or {}

    async def fake_find_by_args(user_id, tenant_id, status=None):
        return existing_members.get((user_id, tenant_id))

    tenant_user_repository.find_by_args.side_effect = fake_find_by_args
    tenant_user_invitation_repository.persist_many.side_effect = lambda drafts: drafts
    return InviteTenantMembers(
        tenant=tenant,
        members=members or [],
        invited_by_user_id=invited_by_user_id,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        skip_email=skip_email,
    )


# ---------- empty list ----------------------------------------------------


async def test_execute__no_members_returns_empty_lists(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    user_repository.find_by_email.return_value = None
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
    )

    result = await use_case.execute()

    expect(result.invitations).to(have_len(0))
    expect(result.skipped_existing_members).to(have_len(0))
    command_bus.dispatch.assert_not_called()
    tenant_user_invitation_repository.persist_many.assert_not_called()


# ---------- requires_password derivation ---------------------------------


async def test_execute__new_email_marks_requires_password_true(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    user_repository.find_by_email.return_value = None
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[MemberInvitationInput(email="new@test.com", role_slug="admin")],
    )

    result = await use_case.execute()

    expect(result.invitations).to(have_len(1))
    invitation = result.invitations[0]
    expect(invitation).to(be_a(TenantUserInvitation))
    expect(invitation.email).to(equal("new@test.com"))
    expect(invitation.requires_password).to(equal(True))
    expect(invitation.status).to(equal(TenantUserInvitationStatus.PENDING))
    expect(invitation.created_by_id).to(equal(invited_by.uuid))


async def test_execute__existing_user_in_other_tenant_marks_requires_password_false(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    other_user = User(uuid=uuid4(), username="returning")
    user_repository.find_by_email.return_value = other_user
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[
            MemberInvitationInput(email="returning@test.com", role_slug="admin"),
        ],
    )

    result = await use_case.execute()

    expect(result.invitations).to(have_len(1))
    expect(result.invitations[0].requires_password).to(equal(False))
    expect(result.skipped_existing_members).to(have_len(0))


# ---------- skip-already-member ------------------------------------------


async def test_execute__existing_tenant_user_is_skipped(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    already = User(uuid=uuid4(), username="already")
    user_repository.find_by_email.return_value = already
    existing_members = {
        (already.uuid, tenant.uuid): TenantUser(
            uuid=uuid4(),
            user_id=already.uuid,
            tenant_id=tenant.uuid,
            is_owner=False,
            status=TenantUserStatus.ACTIVE,
        )
    }
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[MemberInvitationInput(email="already@test.com", role_slug="admin")],
        existing_members=existing_members,
    )

    result = await use_case.execute()

    expect(result.invitations).to(have_len(0))
    expect(result.skipped_existing_members).to(have_len(1))
    expect(result.skipped_existing_members[0]).to(be_a(SkippedExistingMember))
    expect(result.skipped_existing_members[0].email).to(equal("already@test.com"))
    command_bus.dispatch.assert_not_called()


# ---------- normalization -------------------------------------------------


async def test_execute__normalizes_email_lowercase_and_trimmed(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    user_repository.find_by_email.return_value = None
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[
            MemberInvitationInput(email="  Mixed@Test.Com  ", role_slug="admin"),
        ],
    )

    result = await use_case.execute()

    expect(result.invitations[0].email).to(equal("mixed@test.com"))


# ---------- email dispatch ------------------------------------------------


async def test_execute__dispatches_one_email_per_invitation(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    user_repository.find_by_email.return_value = None
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[
            MemberInvitationInput(email="a@test.com", role_slug="admin"),
            MemberInvitationInput(email="b@test.com", role_slug="admin"),
        ],
    )

    await use_case.execute()

    expect(command_bus.dispatch.call_count).to(equal(2))
    command = command_bus.dispatch.call_args_list[0].kwargs["command"]
    expect(command).to(be_a(SendEmailCommand))
    expect(command.template_name).to(equal("invitation"))
    expect(command.subject).to(equal(f"Invitación para unirte a {tenant.name}"))
    expect(command.context["tenant_name"]).to(equal(tenant.name))
    expect(command.context["invitation_url"].startswith(use_case.invite_base_url)).to(
        equal(True)
    )


async def test_execute__skip_email_does_not_dispatch(
    tenant,
    invited_by,
    admin_role,
    command_bus,
    tenant_user_invitation_repository,
    tenant_user_repository,
    tenant_role_repository,
    user_repository,
):
    user_repository.find_by_email.return_value = None
    use_case = _make_use_case(
        tenant=tenant,
        invited_by_user_id=invited_by.uuid,
        admin_role=admin_role,
        command_bus=command_bus,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_user_repository=tenant_user_repository,
        tenant_role_repository=tenant_role_repository,
        user_repository=user_repository,
        members=[MemberInvitationInput(email="a@test.com", role_slug="admin")],
        skip_email=True,
    )

    await use_case.execute()

    command_bus.dispatch.assert_not_called()
