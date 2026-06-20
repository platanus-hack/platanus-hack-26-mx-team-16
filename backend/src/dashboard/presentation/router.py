from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.dashboard.presentation.endpoints.get_overview import get_overview
from src.dashboard.presentation.endpoints.get_processing import get_processing
from src.dashboard.presentation.endpoints.stream_dashboard_events import (
    stream_dashboard_events,
)

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

dashboard_router.add_api_route(
    "/overview",
    get_overview,
    methods=["GET"],
    summary="Get dashboard Overview tab data",
)

dashboard_router.add_api_route(
    "/processing",
    get_processing,
    methods=["GET"],
    summary="Get dashboard Processing tab data",
)

dashboard_router.add_api_route(
    "/events",
    stream_dashboard_events,
    methods=["GET"],
    summary="SSE — dashboard invalidation events",
    response_class=EventSourceResponse,
)
