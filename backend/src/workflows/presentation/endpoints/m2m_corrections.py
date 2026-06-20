"""Plano M2M: correcciones por campo de un caso (E5 · diseño §4).

``POST /v1/cases/{case_id}/corrections {fields: [{documentId?, fieldPath,
value}]}`` — mismo use case del Inspection Bench con ``verified_by=external``
y ``level=0`` (external NO cuenta como L1 para el filtro Rossum del stage L2).
Auth por API key ``dxk_`` (X-Api-Key), igual que ``m2m_cases.py``. Si hay una
APPROVAL abierta reclamada, el lock §3.2 aplica también aquí (423).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    DomainContextDep,
    TemporalClientDep,
)
from src.common.infrastructure.dependencies.tenant_api_key import get_tenant_from_api_key
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflow_documents.verify_field import (
    FieldVerification,
    VerifyDocumentField,
)
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository

EXTERNAL_ACTOR = "external"
EXTERNAL_LEVEL = 0


class CorrectionFieldItem(BaseModel):
    # Contrato camelCase del plano M2M (el middleware de requests es no-op).
    model_config = ConfigDict(populate_by_name=True)

    document_id: UUID | None = Field(default=None, alias="documentId")
    field_path: str = Field(..., min_length=1, max_length=255, alias="fieldPath")
    value: Any


class SubmitCaseCorrectionsRequest(BaseModel):
    fields: list[CorrectionFieldItem] = Field(..., min_length=1, max_length=100)


async def submit_case_corrections(
    case_id: UUID,
    request: SubmitCaseCorrectionsRequest,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    temporal_client: TemporalClientDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    # Agrupar por documento: el use case opera un doc por invocación
    # (documentId ausente ⇒ se resuelve solo si el caso tiene un único doc).
    groups: dict[UUID | None, list[CorrectionFieldItem]] = {}
    for item in request.fields:
        groups.setdefault(item.document_id, []).append(item)

    updated: list[dict] = []
    signaled = False
    for document_id, items in groups.items():
        result = await VerifyDocumentField(
            tenant_id=tenant.uuid,
            case_id=case_id,
            document_id=document_id,
            fields=[
                FieldVerification(field_path=i.field_path, action="correct", value=i.value)
                for i in items
            ],
            verified_by=EXTERNAL_ACTOR,
            level=EXTERNAL_LEVEL,
            case_repository=domain.workflow_case_repository,
            document_repository=domain.document_repository,
            case_event_repository=domain.case_event_repository,
            human_task_repository=SQLHumanTaskRepository(session),
            temporal_client=temporal_client,
        ).execute()
        signaled = signaled or result.corrections_signaled
        updated.extend(
            {"document_id": str(result.document.uuid), "field_path": path}
            for path in result.verified_paths
        )

    return ApiJSONResponse(
        content={
            "case_id": str(case_id),
            "updated": updated,
            "corrections_signaled": signaled,
        },
        status_code=status.HTTP_200_OK,
    )


# ── Router ──────────────────────────────────────────────────────────────────
m2m_corrections_router = APIRouter(prefix="", tags=["M2M"])

m2m_corrections_router.add_api_route(
    "/cases/{case_id}/corrections",
    submit_case_corrections,
    methods=["POST"],
    summary="Apply external field corrections to a case (verified_by=external, level 0)",
)
