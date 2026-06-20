"""Workflow templates catalog endpoint (E6 · W4 · diseño §4.4).

``GET /v1/workflow-templates`` lists the static bundle envelopes shipped under
``backend/fixtures/templates/``. Tenant-authenticated read; no per-workflow guard
(it's catalog metadata, not a workflow-scoped resource).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflows.import_export.templates import (
    WorkflowTemplatesLister,
)


async def list_workflow_templates(
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    templates = WorkflowTemplatesLister().execute()
    return ApiJSONResponse(content=templates, status_code=status.HTTP_200_OK)


workflow_templates_router = APIRouter(prefix="/workflow-templates", tags=["Workflow Templates"])

workflow_templates_router.add_api_route(
    "",
    list_workflow_templates,
    methods=["GET"],
    summary="List workflow bundle templates (static envelopes)",
)
