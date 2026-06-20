"""Lector read-only de caso agregado para staff (ADR 0001, alcance 3).

La ÚNICA lectura cross-tenant de casos: un select del caso sin filtro de
tenant. Resuelto el tenant desde la fila, todo lo demás (docs, runs,
análisis, timeline) se carga con los repos tenant-scoped existentes sobre
ese tenant — la superficie cross-tenant queda acotada a un solo punto.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.staff.domain.entities import StaffCaseAggregate
from src.staff.domain.repositories.staff_case_reader import StaffCaseReader
from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository
from src.workflows.infrastructure.repositories.sql_document_repository import (
    SQLWorkflowDocumentRepository,
)
from src.workflows.infrastructure.repositories.sql_run_summary import (
    SQLWorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
    SQLWorkflowAnalysisRunRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_case import (
    SQLWorkflowCaseRepository,
)


class SQLStaffCaseReader(StaffCaseReader):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_case_aggregate(self, case_id: UUID) -> StaffCaseAggregate | None:
        # Punto cross-tenant único: localizar el caso y resolver su tenant.
        row = (
            await self.session.execute(
                select(WorkflowCaseORM.tenant_id, TenantORM.name, TenantORM.slug)
                .join(TenantORM, TenantORM.uuid == WorkflowCaseORM.tenant_id, isouter=True)
                .where(WorkflowCaseORM.uuid == case_id)
            )
        ).first()
        if row is None:
            return None
        tenant_id, tenant_name, tenant_slug = row

        # Desde aquí, todo tenant-scoped sobre el tenant resuelto (read-only).
        case = await SQLWorkflowCaseRepository(self.session).find_by_id(case_id, tenant_id)
        if case is None:
            return None
        documents = await SQLWorkflowDocumentRepository(self.session).list_by_case(case_id, tenant_id)
        runs = await SQLWorkflowAnalysisRunRepository(self.session).list_by_case(case_id, tenant_id)
        summary_repo = SQLWorkflowAnalysisRunSummaryRepository(self.session)
        latest_summary = None
        for run in runs:
            if run.status == WorkflowAnalysisRunStatus.COMPLETED:
                latest_summary = await summary_repo.find_by_run(run.uuid, tenant_id)
                if latest_summary is not None:
                    break
        timeline = await SQLCaseEventRepository(self.session).list_by_case(
            case_id, tenant_id, limit=50, desc=True
        )
        return StaffCaseAggregate(
            case=case,
            documents=documents,
            runs=runs,
            latest_summary=latest_summary,
            timeline=timeline,
            tenant_name=tenant_name,
            tenant_slug=tenant_slug,
        )
