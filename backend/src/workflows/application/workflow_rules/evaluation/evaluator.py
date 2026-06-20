"""Evaluate one rule against one combination and persist the result row."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import (
    WorkflowRuleOnEmpty,
    WorkflowRuleResultStatus,
)
from src.common.domain.exceptions.workflow_rules import (
    WorkflowRuleCompilationNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.workflow_rules.evaluation.scope_resolver import Combination
from src.workflows.application.workflow_rules.evaluation.when_evaluator import (
    RuleWhenOutcome,
    evaluate_rule_when,
)
from src.common.domain.exceptions.workflow_rules import (
    InvalidWorkflowRuleConfigError,
)
from src.workflows.domain.rules.kind_protocol import (
    EvalContext,
    EvalDocumentInput,
    EvalInputs,
)
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.infrastructure.services.rules import registry

from uuid import UUID

logger = get_logger(__name__)


@dataclass
class WorkflowRuleEvaluator(UseCase):
    """Evaluate a single rule × combination → upserts a WorkflowRuleResult."""

    rule: WorkflowRule
    combination: Combination
    workflow_analysis_run_id: UUID
    case_id: UUID
    document_inputs: list[EvalDocumentInput]
    knowledge_context: list[dict[str, Any]]
    tokens: dict[str, Any]
    compilation_repository: WorkflowRuleCompilationRepository
    result_repository: WorkflowRuleResultRepository
    # phases-config · analyze.{parser,reviewer}_provider: kind pre-construido con
    # runners override para ESTE run. None ⇒ el registry global (byte-idéntico).
    kind_override: Any = None

    async def execute(self) -> WorkflowRuleResult:
        if self.combination.is_synthetic_empty:
            return await self._handle_synthetic_empty()

        # E5 · conditional rules: the `when` predicate gates the evaluation
        # of THIS combination. Evaluated here (not in `load_analysis_run_plan`)
        # so a SKIPPED result row is persisted per combination — the UI needs
        # it to show "No aplica", and SKIPPED never contributes to the verdict
        # (contribute_to_verdict only looks at SUCCESS) nor to blocking gates.
        if self.rule.when:
            try:
                when_outcome = evaluate_rule_when(self.rule.when, self.document_inputs)
            except InvalidWorkflowRuleConfigError as exc:
                return await self._persist_errored(f"invalid `when` predicate: {exc.message}")
            if not when_outcome.matched:
                return await self._persist_when_skipped(when_outcome)

        if not self.rule.current_compilation_id:
            return await self._persist_errored("rule has no active compilation")

        compilation = await self.compilation_repository.find_by_id(self.rule.current_compilation_id)
        if not compilation:
            raise WorkflowRuleCompilationNotFoundError(str(self.rule.current_compilation_id))

        kind = self.kind_override or registry.get(self.rule.kind)
        ctx = EvalContext(
            workflow_id=self.rule.workflow_id,
            tenant_id=self.rule.tenant_id,
            case_id=self.case_id,
            workflow_analysis_run_id=self.workflow_analysis_run_id,
        )
        inputs = EvalInputs(
            documents=self.document_inputs,
            document_refs=self.combination.document_refs,
            knowledge_context=self.knowledge_context,
            tokens=self.tokens,
        )

        try:
            outcome = await kind.evaluate(self.rule, compilation, inputs, ctx)
        except Exception as exc:
            logger.exception("workflow_rule.evaluate.failed", rule_id=str(self.rule.uuid))
            return await self._persist_errored(str(exc))

        status = WorkflowRuleResultStatus.ERRORED if outcome.error is not None else WorkflowRuleResultStatus.SUCCESS
        result = WorkflowRuleResult(
            uuid=uuid4(),
            tenant_id=self.rule.tenant_id,
            workflow_analysis_run_id=self.workflow_analysis_run_id,
            rule_id=self.rule.uuid,
            case_id=self.case_id,
            kind=self.rule.kind,
            status=status,
            output=outcome.output,
            reasoning=outcome.reasoning,
            citations=outcome.citations,
            document_refs=self.combination.document_refs,
            document_refs_hash=self.combination.document_refs_hash,
            rendered_prompt=outcome.rendered_prompt,
            evaluation_metadata=outcome.evaluation_metadata,
            error=outcome.error,
        )
        return await self.result_repository.upsert(result)

    async def _handle_synthetic_empty(self) -> WorkflowRuleResult:
        outcome = self.combination.synthetic_outcome or WorkflowRuleOnEmpty.SKIPPED
        if outcome == WorkflowRuleOnEmpty.SKIPPED:
            status = WorkflowRuleResultStatus.SKIPPED
            output: dict[str, Any] | None = None
        else:
            status = WorkflowRuleResultStatus.SUCCESS
            output = {
                "passed": outcome == WorkflowRuleOnEmpty.PASSED,
                "reason": "scope vacío",
            }
        result = WorkflowRuleResult(
            uuid=uuid4(),
            tenant_id=self.rule.tenant_id,
            workflow_analysis_run_id=self.workflow_analysis_run_id,
            rule_id=self.rule.uuid,
            case_id=self.case_id,
            kind=self.rule.kind,
            status=status,
            output=output,
            reasoning=None,
            citations=[],
            document_refs={},
            document_refs_hash=self.combination.document_refs_hash,
            rendered_prompt=None,
            evaluation_metadata={"on_empty": outcome.value},
            error=None,
        )
        return await self.result_repository.upsert(result)

    async def _persist_when_skipped(self, outcome: RuleWhenOutcome) -> WorkflowRuleResult:
        metadata: dict[str, Any] = {"when": self.rule.when, "matched": False}
        if outcome.reason:
            metadata["reason"] = outcome.reason
        result = WorkflowRuleResult(
            uuid=uuid4(),
            tenant_id=self.rule.tenant_id,
            workflow_analysis_run_id=self.workflow_analysis_run_id,
            rule_id=self.rule.uuid,
            case_id=self.case_id,
            kind=self.rule.kind,
            status=WorkflowRuleResultStatus.SKIPPED,
            output=None,
            reasoning=None,
            citations=[],
            document_refs=self.combination.document_refs,
            document_refs_hash=self.combination.document_refs_hash,
            rendered_prompt=None,
            evaluation_metadata=metadata,
            error=None,
        )
        return await self.result_repository.upsert(result)

    async def _persist_errored(self, error: str) -> WorkflowRuleResult:
        result = WorkflowRuleResult(
            uuid=uuid4(),
            tenant_id=self.rule.tenant_id,
            workflow_analysis_run_id=self.workflow_analysis_run_id,
            rule_id=self.rule.uuid,
            case_id=self.case_id,
            kind=self.rule.kind,
            status=WorkflowRuleResultStatus.ERRORED,
            output=None,
            reasoning=None,
            citations=[],
            document_refs=self.combination.document_refs,
            document_refs_hash=self.combination.document_refs_hash,
            rendered_prompt=None,
            evaluation_metadata={},
            error=error,
        )
        return await self.result_repository.upsert(result)
