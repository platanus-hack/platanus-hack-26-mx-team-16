from fastapi import APIRouter

from src.users.presentation.endpoints.users import register_user

user_router = APIRouter(prefix="/users", tags=["users"])


user_router.add_api_route(
    "",
    register_user,
    methods=["POST"],
    summary="Register a new user",
)
