from fastapi import APIRouter

from src.admin.presentation.router import tasks_router
from src.auth.presentation.router import auth_router
from src.common.presentation.router import common_router
from src.connections.presentation.router import (
    channels_router,
    connections_router,
    ingest_router,
)
from src.evals.presentation.router import evals_router
from src.workflows.presentation.endpoints.human_task import human_tasks_router
from src.workflows.presentation.endpoints.m2m_cases import m2m_cases_router
from src.workflows.presentation.endpoints.m2m_corrections import m2m_corrections_router
from src.workflows.presentation.endpoints.m2m_control import m2m_router
from src.workflows.presentation.endpoints.m2m_extract import m2m_extract_router
from src.workflows.presentation.endpoints.pipeline_admin import pipelines_router
from src.workflows.presentation.endpoints.workflow_templates import workflow_templates_router
from src.dashboard.presentation.router import dashboard_router
from src.industries.presentation.router import industries_router
from src.knowledge_base.presentation.router import knowledge_base_router, workflow_kb_router
from src.profile.presentation.router import me_router
from src.staff.presentation.router import staff_router
from src.storage.presentation.router import storage_router
from src.tenants.presentation.router import invitations_router, tenant_router
from src.usage.presentation.router import usage_router
from src.users.presentation.router import user_router
from src.workflows.presentation.router import (
    case_extraction_router,
    document_types_router,
    workflow_analysis_runs_router,
    workflow_document_router,
    workflow_rules_router,
    workflows_router,
)

# FASTAPI
api_router = APIRouter()

api_router.include_router(common_router, tags=["common"])
api_router.include_router(user_router, prefix="/v1", tags=["users"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(me_router, prefix="/v1", tags=["me"])
api_router.include_router(tenant_router, prefix="/v1", tags=["tenants"])
api_router.include_router(invitations_router, prefix="/v1", tags=["invitations"])
api_router.include_router(tasks_router, prefix="/v1", tags=["tasks"])
api_router.include_router(industries_router, prefix="/v1", tags=["industries"])
api_router.include_router(workflows_router, prefix="/v1", tags=["workflows"])
api_router.include_router(workflow_rules_router, prefix="/v1", tags=["workflow-rules"])
api_router.include_router(workflow_analysis_runs_router, prefix="/v1", tags=["workflow-analysis-runs"])
api_router.include_router(document_types_router, prefix="/v1", tags=["document-types"])
api_router.include_router(storage_router, prefix="/v1", tags=["documents"])
api_router.include_router(knowledge_base_router, prefix="/v1", tags=["knowledge-base"])
api_router.include_router(workflow_kb_router, prefix="/v1", tags=["workflow-knowledge-base"])
api_router.include_router(workflow_document_router, prefix="/v1", tags=["workflow-documents"])
api_router.include_router(case_extraction_router, prefix="/v1", tags=["case-document-extraction"])
api_router.include_router(usage_router, prefix="/v1", tags=["usage"])
api_router.include_router(dashboard_router, prefix="/v1", tags=["dashboard"])
api_router.include_router(connections_router, prefix="/v1", tags=["connections"])
api_router.include_router(ingest_router, prefix="/v1", tags=["ingest"])
api_router.include_router(channels_router, prefix="/v1", tags=["channels"])
api_router.include_router(human_tasks_router, prefix="/v1", tags=["human-tasks"])
api_router.include_router(pipelines_router, prefix="/v1", tags=["pipelines"])
api_router.include_router(workflow_templates_router, prefix="/v1", tags=["workflow-templates"])
api_router.include_router(m2m_router, prefix="/v1", tags=["m2m"])
api_router.include_router(m2m_extract_router, prefix="/v1", tags=["m2m"])
api_router.include_router(m2m_cases_router, prefix="/v1", tags=["m2m"])
api_router.include_router(m2m_corrections_router, prefix="/v1", tags=["m2m"])
api_router.include_router(evals_router, prefix="/v1", tags=["evals"])
# Tercer plano de auth (ADR 0001): consola staff cross-tenant. Prefix propio
# `/staff/v1` — X-Tenant prohibido, gate por claim is_staff + fila activa.
api_router.include_router(staff_router, prefix="/staff/v1", tags=["staff"])
