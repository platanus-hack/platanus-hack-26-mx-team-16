from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationNotFoundError,
)
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.application.use_cases.invitations.cancel_invitation import (
    CancelInvitation,
)


@pytest.fixture
def invitation_id():
    return uuid4()


@pytest.fixture
def pending_invitation(invitation_id, tenant_id):
    return TenantUserInvitation(
        uuid=invitation_id,
        tenant_id=tenant_id,
        email="x@test.com",
        token="tok-abc",  # noqa: S106 — fake token
        status=TenantUserInvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )


@pytest.fixture
def use_case(invitation_id, tenant_id, tenant_user_invitation_repository):
    tenant_user_invitation_repository.mark_expired.side_effect = (
        lambda inv_id: TenantUserInvitation(
            uuid=inv_id,
            tenant_id=tenant_id,
            email="x@test.com",
            token="tok-abc",  # noqa: S106 — fake token
            status=TenantUserInvitationStatus.EXPIRED,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    return CancelInvitation(
        invitation_id=invitation_id,
        tenant_id=tenant_id,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
    )


async def test_execute__cancels_pending_invitation(
    use_case,
    invitation_id,
    pending_invitation,
    tenant_user_invitation_repository,
):
    tenant_user_invitation_repository.find_by_id.return_value = pending_invitation

    result = await use_case.execute()

    expect(result.status).to(equal(TenantUserInvitationStatus.EXPIRED))
    tenant_user_invitation_repository.mark_expired.assert_called_once_with(
        invitation_id
    )


async def test_execute__not_found_raises(
    use_case, tenant_user_invitation_repository
):
    tenant_user_invitation_repository.find_by_id.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()

    tenant_user_invitation_repository.mark_expired.assert_not_called()


async def test_execute__cross_tenant_invitation_treated_as_not_found(
    use_case,
    invitation_id,
    tenant_user_invitation_repository,
):
    """Defensive: never leak an invitation id that belongs to another
    tenant. Returning 'not found' is intentional."""
    other_tenant_invitation = TenantUserInvitation(
        uuid=invitation_id,
        tenant_id=uuid4(),
        email="x@test.com",
        token="tok-abc",  # noqa: S106 — fake token
        status=TenantUserInvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    tenant_user_invitation_repository.find_by_id.return_value = (
        other_tenant_invitation
    )

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()

    tenant_user_invitation_repository.mark_expired.assert_not_called()


async def test_execute__already_accepted_raises(
    use_case,
    invitation_id,
    tenant_id,
    tenant_user_invitation_repository,
):
    accepted = TenantUserInvitation(
        uuid=invitation_id,
        tenant_id=tenant_id,
        email="x@test.com",
        token="tok-abc",  # noqa: S106 — fake token
        status=TenantUserInvitationStatus.ACCEPTED,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    tenant_user_invitation_repository.find_by_id.return_value = accepted

    with pytest.raises(InvitationAlreadyAcceptedError):
        await use_case.execute()

    tenant_user_invitation_repository.mark_expired.assert_not_called()
