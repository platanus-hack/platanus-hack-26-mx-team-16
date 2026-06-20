from fastapi import APIRouter

from src.admin.presentation.router import tasks_router
from src.auth.presentation.router import auth_router
from src.common.presentation.router import common_router
from src.profile.presentation.router import me_router
from src.tenants.presentation.router import invitations_router, tenant_router
from src.users.presentation.router import user_router

# FASTAPI
api_router = APIRouter()

api_router.include_router(common_router, tags=["common"])
api_router.include_router(user_router, prefix="/v1", tags=["users"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(me_router, prefix="/v1", tags=["me"])
api_router.include_router(tenant_router, prefix="/v1", tags=["tenants"])
api_router.include_router(invitations_router, prefix="/v1", tags=["invitations"])
api_router.include_router(tasks_router, prefix="/v1", tags=["tasks"])
