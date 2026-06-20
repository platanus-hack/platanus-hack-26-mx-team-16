from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from expects import equal, expect, have_len

from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.application.use_cases.invitations.list_pending import (
    ListPendingInvitations,
)


def _make_invitation(
    *,
    tenant_id,
    email="x@test.com",
    status=TenantUserInvitationStatus.PENDING,
    expires_at=None,
):
    return TenantUserInvitation(
        uuid=uuid4(),
        tenant_id=tenant_id,
        email=email,
        token=f"tok-{uuid4().hex[:12]}",  # noqa: S106 — fake token
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
    )


@pytest.fixture
def use_case(tenant_id, tenant_user_invitation_repository):
    return ListPendingInvitations(
        tenant_id=tenant_id,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
    )


async def test_execute__returns_pending_within_ttl(
    use_case, tenant_id, tenant_user_invitation_repository
):
    fresh = _make_invitation(tenant_id=tenant_id, email="a@test.com")
    tenant_user_invitation_repository.list_pending_by_tenant.return_value = [fresh]

    result = await use_case.execute()

    expect(result).to(have_len(1))
    expect(result[0].email).to(equal("a@test.com"))
    tenant_user_invitation_repository.list_pending_by_tenant.assert_called_once_with(
        tenant_id,
    )


async def test_execute__filters_out_pending_but_past_ttl(
    use_case, tenant_id, tenant_user_invitation_repository
):
    """A row left as PENDING after its expires_at must not appear in the
    listing — pending-by-status alone is not enough."""
    stale = _make_invitation(
        tenant_id=tenant_id,
        email="stale@test.com",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    fresh = _make_invitation(tenant_id=tenant_id, email="fresh@test.com")
    tenant_user_invitation_repository.list_pending_by_tenant.return_value = [
        stale,
        fresh,
    ]

    result = await use_case.execute()

    expect(result).to(have_len(1))
    expect(result[0].email).to(equal("fresh@test.com"))


async def test_execute__empty_when_repo_returns_empty(
    use_case, tenant_user_invitation_repository
):
    tenant_user_invitation_repository.list_pending_by_tenant.return_value = []

    result = await use_case.execute()

    expect(result).to(have_len(0))
