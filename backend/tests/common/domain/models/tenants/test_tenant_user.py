from uuid import uuid4

import pytest
from expects import be_false, be_none, be_true, equal, expect

from src.common.domain.models.email_address import EmailAddress
from src.common.domain.models.phone_number import PhoneNumber
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.enums.users import TenantUserStatus


@pytest.fixture(scope="function", autouse=True)
def base_tenant_user() -> TenantUser:
    return TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.ACTIVE,
    )


@pytest.fixture(scope="function", autouse=True)
def owner_tenant_user() -> TenantUser:
    return TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )


@pytest.fixture(scope="function", autouse=True)
def tenant_role() -> TenantRole:
    return TenantRole(
        uuid=uuid4(),
        tenant_id=uuid4(),
        name="Manager",
        slug="manager",
        status=TenantRoleStatus.ACTIVE,
        permissions=["users.read", "users.write", "posts.read"],
    )


@pytest.fixture
def user_with_details() -> User:
    return User(
        uuid=uuid4(),
        username="testuser",
        first_name="John",
        last_name="Doe",
        email_address=EmailAddress(
            uuid=uuid4(),
            email="test@example.com",
        ),
        phone_number=PhoneNumber(
            uuid=uuid4(),
            phone_number="23456789",
            dial_code=1,
            iso_code=CountryIsoCode.UNITED_STATES,
        ),
    )


def test_check_permission_returns_true_for_owner():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )

    result = tenant_user.check_permission("any.permission")

    expect(result).to(be_true)


def test_check_permission_returns_true_when_user_has_permission(base_tenant_user: TenantUser, tenant_role: TenantRole):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["custom.permission"]

    result = base_tenant_user.check_permission("users.read")

    expect(result).to(be_true)


def test_check_permission_returns_true_for_user_specific_permission(
    base_tenant_user: TenantUser, tenant_role: TenantRole
):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["special.permission"]

    result = base_tenant_user.check_permission("special.permission")

    expect(result).to(be_true)


def test_check_permission_returns_false_when_user_lacks_permission(
    base_tenant_user: TenantUser, tenant_role: TenantRole
):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = []

    result = base_tenant_user.check_permission("posts.write")

    expect(result).to(be_false)


def test_check_permission_returns_false_with_empty_permission_string(
    base_tenant_user: TenantUser, tenant_role: TenantRole
):
    base_tenant_user.tenant_role = tenant_role

    result = base_tenant_user.check_permission("")

    expect(result).to(be_false)


def test_check_permission_returns_false_without_tenant_role(base_tenant_user: TenantUser):
    base_tenant_user.tenant_role = None
    base_tenant_user.permissions = []

    result = base_tenant_user.check_permission("any.permission")

    expect(result).to(be_false)  # Anonymous role has no permissions


def test_check_permission_returns_false_for_inactive_user(tenant_role: TenantRole):
    inactive_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.INACTIVE,
    )
    inactive_user.tenant_role = tenant_role
    inactive_user.permissions = []

    result = inactive_user.check_permission("users.read")

    expect(result).to(be_false)


def test_check_permission_returns_false_for_inactive_owner():
    inactive_owner = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.INACTIVE,
    )

    result = inactive_owner.check_permission("any.permission")

    expect(result).to(be_false)


def test_check_permissions_returns_true_for_owner():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )

    result = tenant_user.check_permissions(["any.permission", "another.permission"])

    expect(result).to(be_true)


def test_check_permissions_returns_true_when_user_has_all_permissions(
    base_tenant_user: TenantUser, tenant_role: TenantRole
):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["posts.write"]

    result = base_tenant_user.check_permissions(["users.read", "posts.read"])

    expect(result).to(be_true)


def test_check_permissions_returns_false_when_missing_one_permission(
    base_tenant_user: TenantUser, tenant_role: TenantRole
):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = []

    result = base_tenant_user.check_permissions(["users.read", "posts.write"])

    expect(result).to(be_false)


def test_check_permissions_returns_false_with_empty_list(base_tenant_user: TenantUser, tenant_role: TenantRole):
    base_tenant_user.tenant_role = tenant_role

    result = base_tenant_user.check_permissions([])

    expect(result).to(be_false)


def test_check_permissions_returns_false_without_tenant_role(base_tenant_user: TenantUser):
    base_tenant_user.tenant_role = None
    base_tenant_user.permissions = []

    result = base_tenant_user.check_permissions(["any.permission"])

    expect(result).to(be_false)  # Anonymous role has no permissions


def test_check_permissions_with_mixed_user_and_role_permissions(base_tenant_user: TenantUser, tenant_role: TenantRole):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["posts.write", "comments.write"]

    result = base_tenant_user.check_permissions(["users.read", "posts.write", "comments.write"])

    expect(result).to(be_true)


def test_check_permissions_returns_false_for_inactive_user(tenant_role: TenantRole):
    inactive_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.INACTIVE,
    )
    inactive_user.tenant_role = tenant_role
    inactive_user.permissions = []

    result = inactive_user.check_permissions(["users.read", "posts.read"])

    expect(result).to(be_false)


def test_check_permissions_returns_false_for_inactive_owner():
    inactive_owner = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.INACTIVE,
    )

    result = inactive_owner.check_permissions(["any.permission", "another.permission"])

    expect(result).to(be_false)


def test_tenant_role_meta_returns_owner_meta_for_owner():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )

    role_meta = tenant_user.tenant_role_meta

    expect(role_meta).not_to(be_none)
    expect(role_meta.name).to(equal("Owner"))
    expect(role_meta.is_owner).to(be_true)
    expect(role_meta.status).to(equal(TenantRoleStatus.ACTIVE))


def test_tenant_role_meta_returns_anonymous_meta_without_role(base_tenant_user: TenantUser):
    base_tenant_user.tenant_role = None

    role_meta = base_tenant_user.tenant_role_meta

    expect(role_meta).not_to(be_none)
    expect(role_meta.name).to(equal("Anonymous"))
    expect(role_meta.is_owner).to(be_false)
    expect(role_meta.status).to(equal(TenantRoleStatus.ACTIVE))


def test_tenant_role_meta_combines_role_and_user_permissions(base_tenant_user: TenantUser, tenant_role: TenantRole):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["custom.permission", "users.read"]  # users.read duplicated

    role_meta = base_tenant_user.tenant_role_meta

    expect(role_meta).not_to(be_none)
    expect(role_meta.name).to(equal("Manager"))
    expect(role_meta.is_owner).to(be_false)
    expect(set(role_meta.permissions)).to(equal({"users.read", "users.write", "posts.read", "custom.permission"}))


def test_mixed_permissions_returns_combined_permissions(base_tenant_user: TenantUser, tenant_role: TenantRole):
    base_tenant_user.tenant_role = tenant_role
    base_tenant_user.permissions = ["custom.permission", "users.read"]

    permissions = base_tenant_user.mixed_permissions

    expect(set(permissions)).to(equal({"users.read", "users.write", "posts.read", "custom.permission"}))


def test_mixed_permissions_returns_only_user_permissions_without_role(base_tenant_user: TenantUser):
    base_tenant_user.tenant_role = None
    base_tenant_user.permissions = ["custom.permission"]

    permissions = base_tenant_user.mixed_permissions

    expect(set(permissions)).to(equal({"custom.permission"}))


def test_mixed_permissions_handles_empty_permissions(base_tenant_user: TenantUser):
    base_tenant_user.tenant_role = None
    base_tenant_user.permissions = []

    permissions = base_tenant_user.mixed_permissions

    expect(permissions).to(equal([]))


def test_display_first_name_returns_user_first_name(base_tenant_user: TenantUser):
    base_tenant_user.first_name = "CustomFirst"
    base_tenant_user.user = User(
        uuid=uuid4(),
        username="test",
        first_name="UserFirst",
    )

    result = base_tenant_user.display_first_name

    expect(result).to(equal("CustomFirst"))


def test_display_first_name_falls_back_to_user(base_tenant_user: TenantUser):
    base_tenant_user.first_name = None
    base_tenant_user.user = User(
        uuid=uuid4(),
        username="test",
        first_name="UserFirst",
    )

    result = base_tenant_user.display_first_name

    expect(result).to(equal("UserFirst"))


def test_display_first_name_returns_none_when_both_missing(base_tenant_user: TenantUser):
    base_tenant_user.first_name = None
    base_tenant_user.user = None

    result = base_tenant_user.display_first_name

    expect(result).to(be_none)


def test_display_last_name_returns_user_last_name(base_tenant_user: TenantUser):
    base_tenant_user.last_name = "CustomLast"
    base_tenant_user.user = User(
        uuid=uuid4(),
        username="test",
        last_name="UserLast",
    )

    result = base_tenant_user.display_last_name

    expect(result).to(equal("CustomLast"))


def test_display_last_name_falls_back_to_user(base_tenant_user: TenantUser):
    base_tenant_user.last_name = None
    base_tenant_user.user = User(
        uuid=uuid4(),
        username="test",
        last_name="UserLast",
    )

    result = base_tenant_user.display_last_name

    expect(result).to(equal("UserLast"))


def test_phone_number_returns_user_phone(base_tenant_user: TenantUser, user_with_details: User):
    base_tenant_user.user = user_with_details

    result = base_tenant_user.phone_number

    expect(result).not_to(be_none)
    expect(result.phone_number).to(equal("23456789"))


def test_phone_number_returns_none_without_user(base_tenant_user: TenantUser):
    base_tenant_user.user = None

    result = base_tenant_user.phone_number

    expect(result).to(be_none)


def test_email_address_returns_user_email(base_tenant_user: TenantUser, user_with_details: User):
    base_tenant_user.user = user_with_details

    result = base_tenant_user.email_address

    expect(result).not_to(be_none)
    expect(result.email).to(equal("test@example.com"))


def test_email_address_returns_none_without_user(base_tenant_user: TenantUser):
    base_tenant_user.user = None

    result = base_tenant_user.email_address

    expect(result).to(be_none)


def test_is_active_returns_true_for_active_status():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.ACTIVE,
    )

    expect(tenant_user.is_active).to(be_true)


def test_is_active_returns_false_for_inactive_status():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.INACTIVE,
    )

    expect(tenant_user.is_active).to(be_false)


def test_to_persist_dict_returns_correct_structure(base_tenant_user: TenantUser):
    base_tenant_user.first_name = "John"
    base_tenant_user.last_name = "Doe"
    base_tenant_user.permissions = ["users.read", "users.write"]
    role_id = uuid4()
    base_tenant_user.tenant_role_id = role_id

    result = base_tenant_user.to_persist_dict

    expect(result).to(
        equal(
            {
                "uuid": base_tenant_user.uuid,
                "tenant_id": base_tenant_user.tenant_id,
                "user_id": base_tenant_user.user_id,
                "status": "ACTIVE",
                "is_owner": False,
                "is_support": False,
                "first_name": "John",
                "last_name": "Doe",
                "tenant_role_id": role_id,
                "permissions": ["users.read", "users.write"],
                "photo": None,
            }
        )
    )
