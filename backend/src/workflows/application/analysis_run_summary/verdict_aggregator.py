from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.verdict_signal import VerdictSignal
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash
from src.workflows.domain.repositories.workflow import WorkflowRepository
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
from src.workflows.infrastructure.services.rules import registry as kind_registry
from src.workflows.infrastructure.services.run_summary import verdict_logic


@dataclass
class VerdictAggregator(UseCase):
    tenant_id: UUID
    analysis_run_id: UUID
    workflow_repository: WorkflowRepository
    analysis_run_repository: WorkflowAnalysisRunRepository
    workflow_rule_repository: WorkflowRuleRepository
    workflow_rule_result_repository: WorkflowRuleResultRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository

    async def execute(self) -> WorkflowAnalysisRunSummary:
        analysis_run = await self._get_analysis_run()

        workflow = await self.workflow_repository.find_by_id(analysis_run.workflow_id, self.tenant_id)
        results = await self.workflow_rule_result_repository.list_by_run(self.analysis_run_id, self.tenant_id)

        signals = await self._collect_signals(results)
        bundle = verdict_logic.aggregate(signals=signals, results=results)

        summary = await self._build_summary(workflow=workflow, results=results, bundle=bundle)
        return await self.summary_repository.upsert(summary)

    async def _get_analysis_run(self) -> WorkflowAnalysisRun:
        run = await self.analysis_run_repository.find_by_id(self.analysis_run_id, self.tenant_id)
        if run is None:
            raise WorkflowAnalysisRunNotFoundError
        return run

    async def _collect_signals(self, results: list[WorkflowRuleResult]) -> list[VerdictSignal]:
        signals: list[VerdictSignal] = []
        for result in results:
            if result.status != WorkflowRuleResultStatus.SUCCESS:
                continue

            rule = await self.workflow_rule_repository.find_by_id(result.rule_id, self.tenant_id)
            if rule is None:
                continue

            signal = kind_registry.get(rule.kind).contribute_to_verdict(rule, result)
            if signal is not None:
                signals.append(signal)
        return signals

    async def _build_summary(
        self,
        *,
        workflow: Workflow | None,
        results: list[WorkflowRuleResult],
        bundle: verdict_logic.VerdictBundle,
    ) -> WorkflowAnalysisRunSummary:
        existing = await self.summary_repository.find_by_run(self.analysis_run_id, self.tenant_id)
        narrative_status = self._resolve_narrative_status(workflow)
        input_hash = compute_input_hash(
            verdict=bundle.verdict,
            rule_results=results,
            output_schema=workflow.output_schema if workflow else None,
            synthesis_template=workflow.synthesis_template if workflow else None,
            model=None,
        )
        return WorkflowAnalysisRunSummary(
            uuid=existing.uuid if existing else uuid4(),
            workflow_analysis_run_id=self.analysis_run_id,
            tenant_id=self.tenant_id,
            verdict=bundle.verdict,
            signals=bundle.signals,
            signals_by_polarity=bundle.signals_by_polarity,
            signals_by_severity=bundle.signals_by_severity,
            confidence_score=bundle.confidence_score,
            blocking_failures=bundle.blocking_failures,
            degraded_rules=bundle.degraded_rules,
            narrative_status=narrative_status,
            input_hash=input_hash,
        )

    @staticmethod
    def _resolve_narrative_status(workflow: Workflow | None) -> NarrativeStatus:
        if workflow is not None and workflow.synthesis_enabled:
            return NarrativeStatus.PENDING
        return NarrativeStatus.SKIPPED
