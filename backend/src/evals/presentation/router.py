"""Router for the Evals module (F11 · A5). JWT-admin eval platform."""

from fastapi import APIRouter

from src.evals.presentation.endpoints.datasets import (
    create_case,
    create_dataset,
    list_datasets,
)
from src.evals.presentation.endpoints.runs import create_run, get_run

evals_router = APIRouter(prefix="/evals", tags=["Evals"])

# ── Datasets + cases ──────────────────────────────────────────────────────
evals_router.add_api_route("/datasets", create_dataset, methods=["POST"], summary="Create an eval dataset (F11)")
evals_router.add_api_route("/datasets", list_datasets, methods=["GET"], summary="List eval datasets (F11)")
evals_router.add_api_route(
    "/datasets/{id}/cases",
    create_case,
    methods=["POST"],
    summary="Add a golden case to a dataset (F11)",
)

# ── Runs ──────────────────────────────────────────────────────────────────
evals_router.add_api_route("/runs", create_run, methods=["POST"], summary="Create an eval run (F11)")
evals_router.add_api_route("/runs/{id}", get_run, methods=["GET"], summary="Get an eval run (F11)")
