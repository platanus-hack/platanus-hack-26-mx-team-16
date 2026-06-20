"""Router for the Industries module."""

from fastapi import APIRouter

from src.industries.presentation.endpoints.industry_endpoints import (
    create_industry,
    delete_industry,
    list_industries,
    update_industry,
)

industries_router = APIRouter(prefix="/industries", tags=["Industries"])

industries_router.add_api_route(
    "",
    list_industries,
    methods=["GET"],
    summary="List industries",
)

industries_router.add_api_route(
    "",
    create_industry,
    methods=["POST"],
    summary="Create industry",
)

industries_router.add_api_route(
    "/{industry_id}",
    update_industry,
    methods=["PUT"],
    summary="Update industry",
)

industries_router.add_api_route(
    "/{industry_id}",
    delete_industry,
    methods=["DELETE"],
    summary="Delete industry",
)
