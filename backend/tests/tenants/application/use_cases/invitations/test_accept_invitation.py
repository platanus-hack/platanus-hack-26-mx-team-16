from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationPasswordRequiredError,
)
from src.common.domain.models.email_address import EmailAddress
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.common.domain.models.user import User
from src.tenants.application.use_cases.invitations.accept_invitation import (
    AcceptInvitation,
)


@pytest.fixture
def role_id():
    return uuid4()


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
def existing_user():
    return User(
        uuid=uuid4(),
        username="existing-user",
        first_name="Pre",
        last_name="Existing",
        has_password=True,
        email_address=EmailAddress(uuid=uuid4(), email="invitee@test.com"),
    )


def _make_use_case(
    invitation,
    tenant,
    tenant_user_invitation_repository,
    tenant_repository,
    tenant_role_repository,
    tenant_user_repository,
    user_repository,
    email_repository,
    token_service,
    *,
    password: str | None = "secret123",  # noqa: S107 — fake test password
    first_name: str | None = "Jane",
    last_name: str | None = "Doe",
):
    tenant_user_invitation_repository.find_by_token.return_value = invitation
    tenant_repository.find.return_value = tenant
    # Default: the new TenantUser persist returns the same instance.
    tenant_user_repository.persist.side_effect = lambda instance: instance
    # `find_by_args` is called twice — once inside `_ensure_tenant_user` and
    # once at the end to refetch the persisted row. Default to None first
    # (so `_ensure_tenant_user` takes the create path) and a built TenantUser
    # on the final read. Individual tests override as needed.
    tenant_user_repository.find_by_args.side_effect = None
    tenant_user_repository.find_by_args.return_value = None
    user_repository.set_password.return_value = True
    user_repository.update_current_tenant.return_value = None
    email_repository.get_or_create.side_effect = lambda email: EmailAddress(uuid=uuid4(), email=email)
    user_repository.create_user.side_effect = lambda user, password: user
    return AcceptInvitation(
        token=invitation.token,
        password=password,
        first_name=first_name,
        last_name=last_name,
        tenant_user_invitation_repository=tenant_user_invitation_repository,
        tenant_repository=tenant_repository,
        tenant_role_repository=tenant_role_repository,
        tenant_user_repository=tenant_user_repository,
        user_repository=user_repository,
        email_repository=email_repository,
        token_service=token_service,
    )


@pytest.fixture
def use_case(
    invitation,
    tenant,
    tenant_user_invitation_repository,
    tenant_repository,
    tenant_role_repository,
    tenant_user_repository,
    user_repository,
    email_repository,
    token_service,
):
    return _make_use_case(
        invitation,
        tenant,
        tenant_user_invitation_repository,
        tenant_repository,
        tenant_role_repository,
        tenant_user_repository,
        user_repository,
        email_repository,
        token_service,
    )


# ---------- error states --------------------------------------------------


async def test_execute__not_found_raises(use_case, tenant_user_invitation_repository):
    tenant_user_invitation_repository.find_by_token.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()


async def test_execute__already_accepted_raises(use_case, invitation):
    invitation.status = TenantUserInvitationStatus.ACCEPTED

    with pytest.raises(InvitationAlreadyAcceptedError):
        await use_case.execute()


async def test_execute__expired_raises(use_case, invitation):
    invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    with pytest.raises(InvitationExpiredError):
        await use_case.execute()


async def test_execute__tenant_missing_raises_not_found(use_case, tenant_repository):
    tenant_repository.find.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await use_case.execute()


# ---------- password handling --------------------------------------------


async def test_execute__requires_password_but_none_raises_password_required(
    invitation,
    tenant,
    tenant_user_invitation_repository,
    tenant_repository,
    tenant_role_repository,
    tenant_user_repository,
    user_repository,
    email_repository,
    token_service,
):
    """Regression: a missing password must NOT create any User row."""
    user_repository.find_by_email.return_value = None
    uc = _make_use_case(
        invitation,
        tenant,
        tenant_user_invitation_repository,
        tenant_repository,
        tenant_role_repository,
        tenant_user_repository,
        user_repository,
        email_repository,
        token_service,
        password=None,
    )

    with pytest.raises(InvitationPasswordRequiredError):
        await uc.execute()

    user_repository.create_user.assert_not_called()
    email_repository.get_or_create.assert_not_called()
    user_repository.set_password.assert_not_called()
    tenant_user_invitation_repository.mark_accepted.assert_not_called()


async def test_execute__new_user_creates_user_sets_password_and_marks_accepted(
    use_case,
    invitation,
    user_repository,
    email_repository,
    tenant_user_invitation_repository,
):
    user_repository.find_by_email.return_value = None

    result = await use_case.execute()

    expect(result).to(be_a(TenantUserSession))
    email_repository.get_or_create.assert_called_once_with(invitation.email)
    user_repository.create_user.assert_called_once()
    user_repository.set_password.assert_called_once()
    set_password_kwargs = user_repository.set_password.call_args.kwargs
    expect(set_password_kwargs["new_password"]).to(equal("secret123"))
    tenant_user_invitation_repository.mark_accepted.assert_called_once_with(invitation.uuid)


async def test_execute__existing_user_never_overwrites_password(use_case, existing_user, user_repository):
    """Defensive guard: even if invitation.requires_password=True, an
    existing User's password must not be touched (TOCTOU between invite
    creation and accept)."""
    user_repository.find_by_email.return_value = existing_user

    await use_case.execute()

    user_repository.set_password.assert_not_called()
    user_repository.create_user.assert_not_called()


async def test_execute__no_password_required_existing_user_only_updates_tenant(
    use_case, existing_user, invitation, user_repository
):
    invitation.requires_password = False
    user_repository.find_by_email.return_value = existing_user
    use_case.password = None

    await use_case.execute()

    user_repository.set_password.assert_not_called()
    user_repository.create_user.assert_not_called()
    user_repository.update_current_tenant.assert_called_once()


# ---------- TenantUser handling ------------------------------------------


async def test_execute__creates_tenant_user_with_form_names(
    use_case, invitation, existing_user, user_repository, tenant_user_repository
):
    user_repository.find_by_email.return_value = existing_user

    await use_case.execute()

    # Inspect the TenantUser argument to the persist call. _ensure_tenant_user
    # creates a draft TenantUser when find_by_args returns None.
    persisted = tenant_user_repository.persist.call_args.args[0]
    expect(persisted).to(be_a(TenantUser))
    expect(persisted.first_name).to(equal("Jane"))
    expect(persisted.last_name).to(equal("Doe"))
    expect(persisted.user_id).to(equal(existing_user.uuid))
    expect(persisted.tenant_id).to(equal(invitation.tenant_id))
    expect(persisted.tenant_role_id).to(equal(invitation.tenant_role_id))
    expect(persisted.status).to(equal(TenantUserStatus.ACTIVE))


async def test_execute__does_not_write_names_on_user(use_case, existing_user, user_repository):
    """Display names live on TenantUser; the shared User row must not be
    mutated by the invitation flow."""
    user_repository.find_by_email.return_value = existing_user

    await use_case.execute()

    user_repository.persist.assert_not_called()


async def test_execute__updates_existing_tenant_user_role_and_names(
    use_case,
    invitation,
    existing_user,
    tenant_id,
    user_repository,
    tenant_user_repository,
):
    """If the TenantUser already exists (e.g. previously deactivated), the
    use case reactivates it and applies the form-provided names."""
    user_repository.find_by_email.return_value = existing_user
    existing_tenant_user = TenantUser(
        uuid=uuid4(),
        user_id=existing_user.uuid,
        tenant_id=tenant_id,
        is_owner=False,
        is_support=False,
        status=TenantUserStatus.INACTIVE,
        tenant_role_id=None,
        first_name="Old",
        last_name="Name",
    )
    tenant_user_repository.find_by_args.side_effect = None
    tenant_user_repository.find_by_args.return_value = existing_tenant_user

    await use_case.execute()

    persisted = tenant_user_repository.persist.call_args.args[0]
    expect(persisted.uuid).to(equal(existing_tenant_user.uuid))
    expect(persisted.status).to(equal(TenantUserStatus.ACTIVE))
    expect(persisted.tenant_role_id).to(equal(invitation.tenant_role_id))
    expect(persisted.first_name).to(equal("Jane"))
    expect(persisted.last_name).to(equal("Doe"))


async def test_execute__preserves_existing_names_when_form_blank(
    use_case,
    existing_user,
    tenant_id,
    user_repository,
    tenant_user_repository,
):
    user_repository.find_by_email.return_value = existing_user
    existing_tenant_user = TenantUser(
        uuid=uuid4(),
        user_id=existing_user.uuid,
        tenant_id=tenant_id,
        is_owner=False,
        is_support=False,
        status=TenantUserStatus.ACTIVE,
        tenant_role_id=None,
        first_name="Old",
        last_name="Name",
    )
    tenant_user_repository.find_by_args.return_value = existing_tenant_user
    use_case.first_name = None
    use_case.last_name = None

    await use_case.execute()

    persisted = tenant_user_repository.persist.call_args.args[0]
    expect(persisted.first_name).to(equal("Old"))
    expect(persisted.last_name).to(equal("Name"))


# ---------- finalization --------------------------------------------------


async def test_execute__marks_accepted_and_updates_current_tenant(
    use_case,
    existing_user,
    user_repository,
    tenant_user_invitation_repository,
    invitation,
    tenant,
):
    user_repository.find_by_email.return_value = existing_user

    await use_case.execute()

    tenant_user_invitation_repository.mark_accepted.assert_called_once_with(invitation.uuid)
    user_repository.update_current_tenant.assert_called_once()
    kwargs = user_repository.update_current_tenant.call_args.kwargs
    expect(kwargs["user_id"]).to(equal(existing_user.uuid))
    expect(kwargs["tenant_id"]).to(equal(tenant.uuid))


async def test_execute__returns_session_with_user_and_tenant(use_case, existing_user, user_repository, tenant):
    user_repository.find_by_email.return_value = existing_user

    result = await use_case.execute()

    expect(result.user.uuid).to(equal(existing_user.uuid))
    expect(result.tenant.uuid).to(equal(tenant.uuid))
    expect(result.session.access_token).to(equal("test-access-token"))


async def test_execute__when_final_tenant_user_lookup_fails_role_is_none(
    use_case, existing_user, user_repository, tenant_user_repository
):
    """If the post-persist refetch returns None (defensive), the session is
    still built but `tenant_role` is None instead of crashing."""
    user_repository.find_by_email.return_value = existing_user
    tenant_user_repository.find_by_args.return_value = None

    result = await use_case.execute()

    expect(result.tenant_role).to(be_none)
