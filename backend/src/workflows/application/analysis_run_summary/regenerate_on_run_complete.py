"""Hook called when a `WorkflowAnalysisRun` reaches COMPLETED status.

Two phases:
- (deterministic) `VerdictAggregator` writes the verdict layer of the summary.
- (LLM) `SynthesisRunner` enqueues narrative generation if the workflow has
  `synthesis_enabled=True`.

Both steps log + soft-fail: if synthesis falls over, the verdict is still
available. Verdict failure does propagate (no run with results should fail
to compute a verdict; if it does, that's a bug worth surfacing).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.event_publisher import EventPublisher
from src.workflows.application.analysis_run_summary.synthesis_runner import SynthesisRunner
from src.workflows.application.analysis_run_summary.verdict_aggregator import VerdictAggregator
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
from src.workflows.domain.run_summary.events import RunSummaryEvent
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
)

logger = get_logger(__name__)


@dataclass
class WorkflowAnalysisRunSummarizer(UseCase):
    run_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    run_repository: WorkflowAnalysisRunRepository
    rule_repository: WorkflowRuleRepository
    result_repository: WorkflowRuleResultRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository
    agent: SynthesizerAgent
    event_publisher: EventPublisher
    tenant: Tenant | None = None
    document_repository: WorkflowDocumentRepository | None = None  # A4
    document_type_repository: DocumentTypeRepository | None = None  # E2 x-source
    # E2 split: SYSTEM-triggered runs (pipeline interpreter) only need the
    # deterministic verdict layer here — the interpreter's `output` phase runs
    # the synthesis itself. When False, the narrative stays PENDING/SKIPPED.
    synthesize: bool = True

    async def execute(self) -> WorkflowAnalysisRunSummary:
        summary = await VerdictAggregator(
            analysis_run_id=self.run_id,
            tenant_id=self.tenant_id,
            workflow_repository=self.workflow_repository,
            analysis_run_repository=self.run_repository,
            workflow_rule_repository=self.rule_repository,
            workflow_rule_result_repository=self.result_repository,
            summary_repository=self.summary_repository,
        ).execute()

        await self._publish(
            "summary.verdict_ready",
            seq=1,
            payload={
                "verdict": summary.verdict.value,
                "signalsByPolarity": summary.signals_by_polarity,
                "blockingFailures": [str(uid) for uid in summary.blocking_failures],
            },
        )

        if summary.narrative_status != NarrativeStatus.PENDING:
            return summary

        if not self.synthesize:
            # The pipeline `output` phase will invoke SynthesisRunner; leave
            # the narrative PENDING for it.
            return summary

        await self._publish("summary.narrative_started", seq=2, payload={})

        try:
            summary = await SynthesisRunner(
                run_id=self.run_id,
                tenant_id=self.tenant_id,
                workflow_repository=self.workflow_repository,
                run_repository=self.run_repository,
                result_repository=self.result_repository,
                summary_repository=self.summary_repository,
                agent=self.agent,
                tenant=self.tenant,
                document_repository=self.document_repository,
                document_type_repository=self.document_type_repository,
                rule_repository=self.rule_repository,
            ).execute()
        except Exception as exc:
            logger.exception("run_summary.synthesis_failed", run_id=str(self.run_id))
            await self._publish(
                "summary.failed",
                seq=3,
                payload={"error": str(exc)},
            )
            return summary

        if summary.narrative_status == NarrativeStatus.COMPLETED:
            await self._publish(
                "summary.narrative_completed",
                seq=3,
                payload={"outputPreview": _preview(summary.output)},
            )
        elif summary.narrative_status == NarrativeStatus.FAILED:
            await self._publish(
                "summary.failed",
                seq=3,
                payload={"error": summary.narrative_error or "narrative generation failed"},
            )
        return summary

    async def _publish(self, event_type: str, *, seq: int, payload: dict) -> None:
        await self.event_publisher.publish(
            event=RunSummaryEvent(
                seq=seq,
                ts=datetime.now(UTC),
                payload=payload,
                type=event_type,  # type: ignore[arg-type]
                run_id=self.run_id,
            ),
        )


def _preview(output: dict | None) -> dict:
    if not output:
        return {}
    keys = list(output.keys())[:3]
    return {k: output[k] for k in keys}
