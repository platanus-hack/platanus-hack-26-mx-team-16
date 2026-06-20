from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.uuids import optional_string
from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.presentation.presenters.workflow_rule_result import (
    WorkflowRuleResultPresenter,
)


@dataclass
class WorkflowAnalysisRunPresenter(Presenter[WorkflowAnalysisRun]):
    instance: WorkflowAnalysisRun

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "workflow_case_id": str(self.instance.workflow_case_id),
            "status": self.instance.status.value,
            "trigger": self.instance.trigger.value,
            "triggered_by": optional_string(self.instance.triggered_by),
            "started_at": optional_datetime_string(self.instance.started_at),
            "completed_at": optional_datetime_string(self.instance.completed_at),
            "canceled_at": optional_datetime_string(self.instance.canceled_at),
            "canceled_by": optional_string(self.instance.canceled_by),
            "error": self.instance.error,
            "reviewer_model": self.instance.reviewer_model,
            "critic_model": self.instance.critic_model,
            "consensus_samples": self.instance.consensus_samples,
            "rules_total": self.instance.rules_total,
            "rules_passed": self.instance.rules_passed,
            "rules_failed": self.instance.rules_failed,
            "rules_inconclusive": self.instance.rules_inconclusive,
            "duration_ms": self.instance.duration_ms,
            "created_at": optional_datetime_string(self.instance.created_at),
        }


@dataclass
class WorkflowAnalysisRunDetailPresenter(Presenter[WorkflowAnalysisRun]):
    instance: WorkflowAnalysisRun
    results: list[WorkflowRuleResult]
    # Optional rule_id → name map; surfaces a human-readable title per
    # result card. Missing entries fall back to the FE's "Regla"
    # placeholder.
    rule_names: dict | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        names = self.rule_names or {}
        return {
            **WorkflowAnalysisRunPresenter(instance=self.instance).to_dict,
            "results": [
                WorkflowRuleResultPresenter(
                    instance=r, rule_name=names.get(r.rule_id)
                ).to_dict
                for r in self.results
            ],
        }
