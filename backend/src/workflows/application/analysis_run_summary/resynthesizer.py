"""Re-run the synthesizer for an existing summary without recomputing the verdict.

Verdict layer is immutable per run (results don't change). `force=True`
bypasses the input_hash cache.
"""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.application.analysis_run_summary.synthesis_runner import SynthesisRunner
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
)


@dataclass
class ResynthesizeSummary(UseCase):
    run_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    run_repository: WorkflowAnalysisRunRepository
    result_repository: WorkflowRuleResultRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository
    agent: SynthesizerAgent
    tenant: Tenant | None = None
    force: bool = False
    # E2: optional — when wired, re-synthesis also re-runs the x-source projection.
    document_repository: WorkflowDocumentRepository | None = None
    document_type_repository: DocumentTypeRepository | None = None
    rule_repository: WorkflowRuleRepository | None = None

    async def execute(self) -> WorkflowAnalysisRunSummary:
        return await SynthesisRunner(
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            workflow_repository=self.workflow_repository,
            run_repository=self.run_repository,
            result_repository=self.result_repository,
            summary_repository=self.summary_repository,
            agent=self.agent,
            tenant=self.tenant,
            force=self.force,
            document_repository=self.document_repository,
            document_type_repository=self.document_type_repository,
            rule_repository=self.rule_repository,
        ).execute()
