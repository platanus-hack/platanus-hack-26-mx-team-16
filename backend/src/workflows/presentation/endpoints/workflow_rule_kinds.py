"""Endpoint to list registered rule kinds + their schemas (spec §4.3, §11)."""

from __future__ import annotations

from fastapi import status

from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.infrastructure.services.rules import registry
from src.workflows.presentation.presenters.workflow_rule_kind import (
    WorkflowRuleKindPresenter,
)


async def list_workflow_rule_kinds() -> ApiJSONResponse:
    kinds = registry.list_all()
    return ApiJSONResponse(
        content=[WorkflowRuleKindPresenter(instance=k).to_dict for k in kinds],
        status_code=status.HTTP_200_OK,
    )
