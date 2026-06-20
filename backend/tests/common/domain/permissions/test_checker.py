from uuid import uuid4

import pytest
from expects import be_true, expect

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.permissions.checker import check_tenant_permission


@pytest.fixture(scope="function")
def tenant_role() -> TenantRole:
    return TenantRole(
        uuid=uuid4(),
        tenant_id=uuid4(),
        name="Manager",
        slug="manager",
        status=TenantRoleStatus.ACTIVE,
        permissions=["users.read", "users.write", "posts.read"],
    )


@pytest.fixture(scope="function")
def tenant_user_with_role(tenant_role: TenantRole) -> TenantUser:
    user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.ACTIVE,
    )
    user.tenant_role = tenant_role
    user.permissions = []
    return user


@pytest.fixture(scope="function")
def owner_tenant_user() -> TenantUser:
    """Create an owner tenant user (fresh instance per test)."""
    return TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )


def test_check_tenant_permission_returns_true_when_user_has_all_permissions(
    tenant_user_with_role: TenantUser,
):
    required_permissions = ["users.read", "posts.read"]

    result = check_tenant_permission(tenant_user_with_role, required_permissions)

    expect(result).to(be_true)


def test_check_tenant_permission_returns_true_for_owner(owner_tenant_user: TenantUser):
    required_permissions = ["any.permission", "another.permission"]

    result = check_tenant_permission(owner_tenant_user, required_permissions)

    expect(result).to(be_true)


def test_check_tenant_permission_returns_true_with_mixed_permissions(
    tenant_user_with_role: TenantUser,
):
    tenant_user_with_role.permissions = ["custom.permission"]
    required_permissions = ["users.read", "custom.permission"]

    result = check_tenant_permission(tenant_user_with_role, required_permissions)

    expect(result).to(be_true)


def test_check_tenant_permission_returns_true_with_single_permission(
    tenant_user_with_role: TenantUser,
):
    required_permissions = ["users.read"]

    result = check_tenant_permission(tenant_user_with_role, required_permissions)

    expect(result).to(be_true)
