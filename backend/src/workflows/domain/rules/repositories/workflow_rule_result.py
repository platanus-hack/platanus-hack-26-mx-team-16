from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult


class WorkflowRuleResultRepository(ABC):
    @abstractmethod
    async def find_by_id(self, result_id: UUID, tenant_id: UUID) -> WorkflowRuleResult | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_run(self, run_id: UUID, tenant_id: UUID) -> list[WorkflowRuleResult]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowRuleResult]:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, result: WorkflowRuleResult) -> WorkflowRuleResult:
        """Upsert by (workflow_analysis_run_id, rule_id, document_refs_hash) — see spec §8.1."""
        raise NotImplementedError
