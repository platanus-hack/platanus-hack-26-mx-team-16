"""E5 · W4: StaffUserRepository — fila activa, revocación, upsert idempotente."""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.staff.application.access import GrantStaffAccess, RevokeStaffAccess
from src.staff.domain.models.staff_user import StaffRole, StaffUser, StaffUserStatus
from src.staff.infrastructure.repositories.sql_staff_user import SQLStaffUserRepository


@pytest.fixture
def staff_repo(async_session):
    return SQLStaffUserRepository(session=async_session)


async def test_find_active__returns_active_row(staff_repo, user_orm):
    created = await staff_repo.add(
        StaffUser(uuid=uuid4(), user_id=user_orm.uuid, role=StaffRole.STAFF_ANALYST_L1)
    )

    found = await staff_repo.find_active_by_user_id(user_orm.uuid)

    expect(found.uuid).to(equal(created.uuid))
    expect(found.role).to(equal(StaffRole.STAFF_ANALYST_L1))
    expect(found.is_active).to(equal(True))


async def test_find_active__ignores_revoked_row(staff_repo, user_orm):
    staff = await staff_repo.add(
        StaffUser(uuid=uuid4(), user_id=user_orm.uuid, role=StaffRole.STAFF_ANALYST_L1)
    )
    await RevokeStaffAccess(user_id=user_orm.uuid, repository=staff_repo).execute()

    expect(await staff_repo.find_active_by_user_id(user_orm.uuid)).to(be_none)
    # La fila no se borra: el audit trail la necesita.
    survivor = await staff_repo.find_by_user_id(user_orm.uuid)
    expect(survivor.uuid).to(equal(staff.uuid))
    expect(survivor.status).to(equal(StaffUserStatus.REVOKED))
    expect(survivor.revoked_at).not_to(be_none)


async def test_grant__is_idempotent_and_reactivates(staff_repo, user_orm):
    first = await GrantStaffAccess(
        user_id=user_orm.uuid, role=StaffRole.STAFF_ANALYST_L1, repository=staff_repo
    ).execute()
    # Re-otorgar sin cambios: no crea fila nueva.
    again = await GrantStaffAccess(
        user_id=user_orm.uuid, role=StaffRole.STAFF_ANALYST_L1, repository=staff_repo
    ).execute()
    expect(again.uuid).to(equal(first.uuid))

    # Revocar y re-otorgar con rol nuevo: reactiva la MISMA fila.
    await RevokeStaffAccess(user_id=user_orm.uuid, repository=staff_repo).execute()
    regranted = await GrantStaffAccess(
        user_id=user_orm.uuid, role=StaffRole.STAFF_ADMIN, repository=staff_repo
    ).execute()

    expect(regranted.uuid).to(equal(first.uuid))
    expect(regranted.role).to(equal(StaffRole.STAFF_ADMIN))
    expect(regranted.status).to(equal(StaffUserStatus.ACTIVE))
    expect(regranted.revoked_at).to(be_none)


async def test_revoke__missing_user_is_noop(staff_repo):
    result = await RevokeStaffAccess(user_id=uuid4(), repository=staff_repo).execute()
    expect(result).to(be_none)
