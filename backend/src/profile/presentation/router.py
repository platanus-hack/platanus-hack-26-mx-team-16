from fastapi import APIRouter

from src.profile.presentation.endpoints.get_profile import get_profile
from src.profile.presentation.endpoints.get_user_tenants import get_user_tenants
from src.profile.presentation.endpoints.update_me_tenant import update_me_tenant
from src.profile.presentation.endpoints.update_password import update_password
from src.profile.presentation.endpoints.update_profile import update_profile

me_router = APIRouter(prefix="/me", tags=["me"])

me_router.add_api_route(
    "/profile",
    get_profile,
    methods=["GET"],
    summary="Get current user profile",
)

me_router.add_api_route(
    "/profile",
    update_profile,
    methods=["PUT"],
    summary="Update current user profile",
)

me_router.add_api_route(
    "/password",
    update_password,
    methods=["PUT"],
    summary="Update current user password",
)

me_router.add_api_route(
    "/tenants",
    get_user_tenants,
    methods=["GET"],
    summary="Get user tenants",
    description="Returns all tenants where the authenticated user is a member",
)

me_router.add_api_route(
    "/tenants/{tenant_id}",
    update_me_tenant,
    methods=["PUT"],
    summary="Update current tenant",
    description="Updates the authenticated user's current tenant",
)
