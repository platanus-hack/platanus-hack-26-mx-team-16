"""E5 · W4: claim `is_staff` — emisión condicional y re-derivación en refresh.

El claim solo gatea (ADR 0001): se emite en login si hay fila staff activa y
el refresh lo RE-DERIVA con lookup fresco — sin esto, el claim moriría al
primer refresh (el access dura 10 min).
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.auth.application.use_cases.session_builder import TenantUserSessionBuilder
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.infrastructure.services.jwt_token_builder import JwtTokenBuilder
from src.common.infrastructure.services.jwt_token_service import JwtTokenService
from src.staff.domain.models.staff_user import StaffRole, StaffUser


class _FakeTokenStore:
    async def blacklist_token_sub(self, sub, ttl, namespace):
        return None

    async def store_token(self, jti, sub, ttl, namespace):
        return None

    async def is_blacklisted(self, jti, namespace):
        return False

    async def clean(self, jti, sub, namespace):
        return None


class _FakeStaffRepo:
    def __init__(self, active: bool):
        self._active = active

    async def find_active_by_user_id(self, user_id):
        if not self._active:
            return None
        return StaffUser(uuid=uuid4(), user_id=user_id, role=StaffRole.STAFF_ANALYST_L1)


def _service(active_staff: bool | None) -> JwtTokenService:
    repo = None if active_staff is None else _FakeStaffRepo(active_staff)
    return JwtTokenService(
        token_store=_FakeTokenStore(),
        token_builder=JwtTokenBuilder(),
        staff_user_repository=repo,
    )


async def test_generate_token__emits_is_staff_only_via_extra_claims():
    service = _service(active_staff=None)
    sub = str(uuid4())

    plain = await service.generate_token(sub=sub, namespace="USER")
    staff = await service.generate_token(
        sub=sub, namespace="USER", extra_claims={"is_staff": True}
    )

    builder = JwtTokenBuilder()
    plain_claims = builder.verify_token(plain.access_token, JwtTokenScope.ACCESS)
    staff_claims = builder.verify_token(staff.access_token, JwtTokenScope.ACCESS)
    expect(plain_claims.is_staff).to(equal(False))
    expect(staff_claims.is_staff).to(equal(True))


async def test_extra_claims__cannot_override_reserved_claims():
    service = _service(active_staff=None)
    sub = str(uuid4())

    session = await service.generate_token(
        sub=sub, namespace="USER", extra_claims={"sub": "attacker", "is_staff": True}
    )

    claims = JwtTokenBuilder().verify_token(session.access_token, JwtTokenScope.ACCESS)
    expect(claims.sub).to(equal(sub))
    expect(claims.is_staff).to(equal(True))


@pytest.mark.parametrize("active", [True, False])
async def test_refresh_token__re_derives_is_staff_from_live_row(active: bool):
    service = _service(active_staff=active)
    sub = str(uuid4())
    # Login SIN claim (p. ej. promovido a staff después del login, o revocado).
    session = await service.generate_token(sub=sub, namespace="USER")

    _, refreshed = await service.refresh_token(session.refresh_token)

    claims = JwtTokenBuilder().verify_token(refreshed.access_token, JwtTokenScope.ACCESS)
    expect(claims.is_staff).to(equal(active))


async def test_session_builder__staff_lookup():
    builder = TenantUserSessionBuilder(
        email="x@y.z",
        password="irrelevant",
        query_bus=None,
        token_service=None,
        staff_user_repository=_FakeStaffRepo(active=True),
    )
    staff = await builder._find_staff_user(uuid4())
    expect(staff).not_to(be_none)

    builder_inactive = TenantUserSessionBuilder(
        email="x@y.z",
        password="irrelevant",
        query_bus=None,
        token_service=None,
        staff_user_repository=_FakeStaffRepo(active=False),
    )
    expect(await builder_inactive._find_staff_user(uuid4())).to(be_none)

    builder_without_repo = TenantUserSessionBuilder(
        email="x@y.z", password="irrelevant", query_bus=None, token_service=None
    )
    expect(await builder_without_repo._find_staff_user(uuid4())).to(be_none)
