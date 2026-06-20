from fastapi import APIRouter

from src.usage.presentation.endpoints.process_record import (
    create_process_record,
    get_usage_summary,
    list_process_records,
)

usage_router = APIRouter(prefix="/usage", tags=["usage"])

usage_router.add_api_route(
    "/process-records",
    create_process_record,
    methods=["POST"],
    summary="Register a successful document processing event (server-to-server)",
)
usage_router.add_api_route(
    "/process-records",
    list_process_records,
    methods=["GET"],
    summary="List processing history for the tenant",
)
usage_router.add_api_route(
    "/summary",
    get_usage_summary,
    methods=["GET"],
    summary="Get current period usage summary",
)
