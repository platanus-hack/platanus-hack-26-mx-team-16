from fastapi import APIRouter

from src.admin.presentation.router import tasks_router
from src.auth.presentation.router import auth_router
from src.common.presentation.router import common_router
from src.profile.presentation.router import me_router
from src.scans.presentation.router import report_router, scans_router
from src.sites.presentation.router import (
    me_router as alerts_me_router,
)
from src.sites.presentation.router import (
    ranking_router,
    sites_router,
    watchlist_router,
)
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

# -> OWLIVER PENTEST ENGINE (12-api): scans + sites HTTP surface
api_router.include_router(scans_router, prefix="/v1", tags=["scans"])
api_router.include_router(report_router, prefix="/v1", tags=["public-report"])
api_router.include_router(sites_router, prefix="/v1", tags=["sites"])
api_router.include_router(ranking_router, prefix="/v1", tags=["ranking"])
api_router.include_router(watchlist_router, prefix="/v1", tags=["watchlist"])
api_router.include_router(alerts_me_router, prefix="/v1", tags=["me-alerts"])
