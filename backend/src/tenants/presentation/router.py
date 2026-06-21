from fastapi import APIRouter

from src.tenants.presentation.endpoints.permissions import get_missing_permissions
from src.tenants.presentation.endpoints.tenant_role import delete_tenant_role, get_tenant_role, update_tenant_role
from src.tenants.presentation.endpoints.tenant_roles import (
    create_tenant_role,
    get_tenant_roles,
)
from src.tenants.presentation.endpoints.tenant_roles_bootstrap import bootstrap_tenant_roles
from src.tenants.presentation.endpoints.tenant_user import (
    create_tenant_user,
    delete_tenant_user,
    get_tenant_user,
    update_tenant_user,
)
from src.tenants.presentation.endpoints.tenant_user_stats import get_tenant_user_stats
from src.tenants.presentation.endpoints.tenant_users import get_tenant_users
from src.tenants.presentation.endpoints.settings.getter import get_tenant_settings
from src.tenants.presentation.endpoints.settings.updater import update_tenant_settings
from src.tenants.presentation.endpoints.settings.avatar_updater import update_tenant_avatar
from src.tenants.presentation.endpoints.settings.webhook_key_regenerator import regenerate_webhook_key
from src.tenants.presentation.endpoints.settings.soft_deleter import soft_delete_tenant
from src.tenants.presentation.endpoints.tenants import register_tenant, update_tenant
from src.tenants.presentation.endpoints.tenant_onboard import onboard_tenant
from src.tenants.presentation.endpoints.invitations import (
    accept_invitation,
    get_invitation_by_token,
)
from src.tenants.presentation.endpoints.invitations_create import (
    cancel_tenant_invitation,
    create_tenant_invitations,
    list_tenant_invitations,
)
from src.tenants.presentation.endpoints.member_password_reset import (
    send_member_password_reset,
)
from src.tenants.presentation.endpoints.member_photo import update_member_photo
from src.tenants.presentation.endpoints.api_keys import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)

tenant_router = APIRouter(prefix="/tenants", tags=["tenants"])

tenant_router.add_api_route(
    "/api-keys",
    list_api_keys,
    methods=["GET"],
    summary="List tenant M2M API keys (F9)",
)
tenant_router.add_api_route(
    "/api-keys",
    create_api_key,
    methods=["POST"],
    summary="Mint a tenant M2M API key — returns the cleartext once (F9)",
)
tenant_router.add_api_route(
    "/api-keys/{key_id}",
    revoke_api_key,
    methods=["DELETE"],
    summary="Revoke a tenant M2M API key (F9)",
)

tenant_router.add_api_route(
    "",
    register_tenant,
    methods=["POST"],
    summary="Register a new Tenant",
)
tenant_router.add_api_route(
    "/onboard",
    onboard_tenant,
    methods=["POST"],
    summary="Onboard a new Tenant (superuser): tenant + roles + invitations + emails",
)

tenant_router.add_api_route(
    "/{tenant_id}",
    update_tenant,
    methods=["PUT"],
    summary="Update Tenant",
)
tenant_router.add_api_route(
    "/{tenant_id}",
    soft_delete_tenant,
    methods=["DELETE"],
    summary="Soft-Delete Tenant",
)
tenant_router.add_api_route(
    "/{tenant_id}/settings",
    get_tenant_settings,
    methods=["GET"],
    summary="Get Tenant Settings",
)
tenant_router.add_api_route(
    "/{tenant_id}/settings",
    update_tenant_settings,
    methods=["PATCH"],
    summary="Update Tenant Name",
)
tenant_router.add_api_route(
    "/{tenant_id}/settings/avatar",
    update_tenant_avatar,
    methods=["POST"],
    summary="Update Tenant Avatar",
)
tenant_router.add_api_route(
    "/{tenant_id}/settings/webhook-key",
    regenerate_webhook_key,
    methods=["POST"],
    summary="Regenerate Webhook Signature Key",
)

tenant_router.add_api_route(
    "/permissions/missing",
    get_missing_permissions,
    methods=["POST"],
    summary="Get Missing Permissions",
    response_model=list[str],
)
#
# ~ USERS
#
tenant_router.add_api_route(
    "/users/stats",
    get_tenant_user_stats,
    methods=["GET"],
    summary="Get Tenant User Stats",
)
tenant_router.add_api_route(
    "/users",
    get_tenant_users,
    methods=["GET"],
    summary="Get Tenant Users",
)
tenant_router.add_api_route(
    "/users",
    create_tenant_user,
    methods=["POST"],
    summary="Create a Tenant User (member). `reuse=true` is idempotent.",
)
tenant_router.add_api_route(
    "/invitations",
    create_tenant_invitations,
    methods=["POST"],
    summary="Invite members to the current tenant",
)
tenant_router.add_api_route(
    "/invitations",
    list_tenant_invitations,
    methods=["GET"],
    summary="List pending invitations for the current tenant",
)
tenant_router.add_api_route(
    "/invitations/{invitation_id}",
    cancel_tenant_invitation,
    methods=["DELETE"],
    summary="Cancel a pending invitation (sets it to EXPIRED)",
)
tenant_router.add_api_route(
    "/users/{tenant_user_id}",
    get_tenant_user,
    methods=["GET"],
    summary="Retrieve Tenant User Detail",
)
tenant_router.add_api_route(
    "/users/{tenant_user_id}/send-password-reset",
    send_member_password_reset,
    methods=["POST"],
    summary="Email a password-reset link to a tenant member",
)
tenant_router.add_api_route(
    "/users/{tenant_user_id}/photo",
    update_member_photo,
    methods=["POST"],
    summary="Upload a profile photo for a tenant member",
)
tenant_router.add_api_route(
    "/users/{tenant_user_id}",
    update_tenant_user,
    methods=["PUT"],
    summary="Update Tenant User",
)
tenant_router.add_api_route(
    "/users/{tenant_user_id}",
    delete_tenant_user,
    methods=["DELETE"],
    summary="Remove Tenant User",
)
#
# ~ ROLES
#
tenant_router.add_api_route(
    "/roles",
    get_tenant_roles,
    methods=["GET"],
    summary="Get Tenant Roles",
)
tenant_router.add_api_route(
    "/roles",
    create_tenant_role,
    methods=["POST"],
    summary="Create Tenant Role",
)
tenant_router.add_api_route(
    "/roles/bootstrap",
    bootstrap_tenant_roles,
    methods=["POST"],
    summary="Bootstrap Default Tenant Roles",
)
tenant_router.add_api_route(
    "/roles/{role_id}",
    get_tenant_role,
    methods=["GET"],
    summary="Get Tenant Role Detail",
)
tenant_router.add_api_route(
    "/roles/{role_id}",
    update_tenant_role,
    methods=["PUT"],
    summary="Update Tenant Role",
)
tenant_router.add_api_route(
    "/roles/{role_id}",
    delete_tenant_role,
    methods=["DELETE"],
    summary="Delete Tenant Role",
)


# =============================================================================
# Invitations router (public — token-gated, no auth)
# =============================================================================
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])

invitations_router.add_api_route(
    "/{token}",
    get_invitation_by_token,
    methods=["GET"],
    summary="Lookup a pending invitation by token (public)",
)
invitations_router.add_api_route(
    "/{token}/accept",
    accept_invitation,
    methods=["POST"],
    summary="Accept an invitation (single-use). Sets password + returns session.",
)
