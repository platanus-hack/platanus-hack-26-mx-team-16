from fastapi import APIRouter

from src.auth.presentation.endpoints.google_login import google_login
from src.auth.presentation.endpoints.login import login
from src.auth.presentation.endpoints.logout import logout
from src.auth.presentation.endpoints.refresh import refresh
from src.auth.presentation.endpoints.reset_password import reset_password
from src.auth.presentation.endpoints.reset_password_confirm import (
    reset_password_confirm,
)
from src.auth.presentation.endpoints.session import session

auth_router = router = APIRouter(prefix="/auth", tags=["auth"])


auth_router.add_api_route(
    path="/login",
    endpoint=login,
    methods=["POST"],
)
auth_router.add_api_route(
    path="/google-login",
    endpoint=google_login,
    methods=["POST"],
)
auth_router.add_api_route(
    path="/reset-password",
    endpoint=reset_password,
    methods=["POST"],
)
auth_router.add_api_route(
    path="/reset-password/confirm",
    endpoint=reset_password_confirm,
    methods=["POST"],
)
auth_router.add_api_route(
    path="/refresh",
    endpoint=refresh,
    methods=["POST"],
)
auth_router.add_api_route(
    path="/logout",
    endpoint=logout,
    methods=["POST"],
)

# -> Session Configuration

auth_router.add_api_route(
    path="/session",
    endpoint=session,
    methods=["GET"],
)
