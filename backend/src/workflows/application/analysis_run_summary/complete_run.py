"""Public hook: close a `WorkflowAnalysisRun` and regenerate its summary.

Eventually a full evaluation orchestrator will call this; for now it's the
single entry point that downstream callers (background jobs, manual close
endpoints) use to trigger the deterministic verdict + LLM narrative.

E2 split: runs with ``trigger == SYSTEM`` come from the pipeline interpreter
(`analyze` phase). For those, this hook generates ONLY the deterministic
verdict layer (`synthesize_and_dispatch=False`): the interpreter's `output`
phase invokes `SynthesisRunner` and its `deliver` phase emits the webhooks —
running them here too would duplicate both. USER/RETRY/SCHEDULED runs keep
the historical inline behavior (verdict + synthesis + webhook dispatch).

Idempotent: invoking it on an already-COMPLETED run just refreshes the
summary (synthesis cache makes that cheap).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.event_publisher import EventPublisher
from src.workflows.application.analysis_run_summary.regenerate_on_run_complete import (
    WorkflowAnalysisRunSummarizer,
)
from src.workflows.application.analysis_run_summary.webhook_dispatcher import (
    SummaryWebhookDispatcher,
)
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

logger = get_logger(__name__)


@dataclass
class CompleteWorkflowAnalysisRun(UseCase):
    tenant: Tenant
    run_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    run_repository: WorkflowAnalysisRunRepository
    rule_repository: WorkflowRuleRepository
    result_repository: WorkflowRuleResultRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository
    agent: SynthesizerAgent
    event_publisher: EventPublisher
    webhook_dispatcher: SummaryWebhookDispatcher | None = None
    document_repository: WorkflowDocumentRepository | None = None  # A4
    document_type_repository: DocumentTypeRepository | None = None  # E2 x-source

    async def execute(self) -> WorkflowAnalysisRunSummary:
        run = await self.run_repository.find_by_id(self.run_id, self.tenant_id)
        if run is None:
            raise WorkflowAnalysisRunNotFoundError(str(self.run_id))

        # E2: SYSTEM runs belong to the pipeline interpreter — synthesis runs
        # in its `output` phase and webhooks in its `deliver` phase, so this
        # hook must do neither (only the deterministic verdict layer).
        synthesize_and_dispatch = run.trigger != WorkflowAnalysisRunTrigger.SYSTEM

        if run.status != WorkflowAnalysisRunStatus.COMPLETED:
            await self.run_repository.update_status(
                run_id=self.run_id,
                tenant_id=self.tenant_id,
                status=WorkflowAnalysisRunStatus.COMPLETED,
                completed=True,
            )

        summary = await WorkflowAnalysisRunSummarizer(
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            workflow_repository=self.workflow_repository,
            run_repository=self.run_repository,
            rule_repository=self.rule_repository,
            result_repository=self.result_repository,
            summary_repository=self.summary_repository,
            agent=self.agent,
            tenant=self.tenant,
            event_publisher=self.event_publisher,
            document_repository=self.document_repository,
            document_type_repository=self.document_type_repository,
            synthesize=synthesize_and_dispatch,
        ).execute()

        if self.webhook_dispatcher is not None and synthesize_and_dispatch:
            try:
                await self.webhook_dispatcher.dispatch(run_id=self.run_id, summary=summary)
            except Exception:
                logger.exception("run_summary.webhook_dispatch_failed", run_id=str(self.run_id))

        return summary
