from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.common.domain.enums.tenants import (
    TenantRoleStatus,
    TenantUserInvitationStatus,
)
from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.application.use_cases.invitations.get_invitation import (
    GetInvitation,
    InvitationView,
)


@pytest.fixture
def role_id():
    return uuid4()


@pytest.fixture
def role(role_id, tenant_id):
    return TenantRole(
        uuid=role_id,
        tenant_id=tenant_id,
        name="Admin",
        slug="admin",
        status=TenantRoleStatus.ACTIVE,
        permissions=[],
    )


@pytest.fixture
def invitation(tenant_id, role_id):
    return TenantUserInvitation(
        uuid=uuid4(),
        tenant_id=tenant_id,
        email="invitee@test.com",
        tenant_role_id=role_id,
        token="token-abc",  # noqa: S106 — fake invitation token, not a credential
        status=TenantUserInvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        requires_password=True,
    )


@pytest.fixture
def use_case(
    invitation,
    tenant,
    role,
    tenant_user_invitation_repository,
    tenant_repository,
    tenant_role_repository,
):
    tenant_user_invitation_repository.find_by_token.return_value = invitation
    tenant_repository.find.return_value = tenant
    tenant_role_repository.find.return_value = role
    return GetInvitation(
        token=invitation.token,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_repository=tenant_repository,
        tenant_role_repository=tenant_role_repository,
    )


async def test_execute__returns_view_with_tenant_and_role(use_case, tenant):
    result = await use_case.execute()

    expect(result).to(be_a(InvitationView))
    expect(result.tenant_name).to(equal(tenant.name))
    expect(result.role_name).to(equal("Admin"))


async def test_execute__role_id_missing_returns_none_role(use_case, invitation, tenant_role_repository):
    invitation.tenant_role_id = None

    result = await use_case.execute()

    expect(result.role_name).to(be_none)
    tenant_role_repository.find.assert_not_called()


async def test_execute__not_found_raises(use_case, tenant_user_invitation_repository):
    tenant_user_invitation_repository.find_by_token.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()


async def test_execute__accepted_raises_already_accepted(use_case, invitation):
    invitation.status = TenantUserInvitationStatus.ACCEPTED

    with pytest.raises(InvitationAlreadyAcceptedError):
        await use_case.execute()


async def test_execute__past_expires_at_raises_expired(use_case, invitation):
    invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    with pytest.raises(InvitationExpiredError):
        await use_case.execute()


async def test_execute__status_expired_raises_expired(use_case, invitation):
    invitation.status = TenantUserInvitationStatus.EXPIRED

    with pytest.raises(InvitationExpiredError):
        await use_case.execute()


async def test_execute__tenant_missing_raises_not_found(use_case, tenant_repository):
    tenant_repository.find.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()
