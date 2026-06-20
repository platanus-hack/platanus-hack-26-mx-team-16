from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.workflows.presentation.helpers.humanize_reasoning import humanize


@dataclass
class WorkflowAnalysisRunSummaryPresenter(Presenter[WorkflowAnalysisRunSummary]):
    instance: WorkflowAnalysisRunSummary

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "workflow_analysis_run_id": str(self.instance.workflow_analysis_run_id),
            "tenant_id": str(self.instance.tenant_id),
            "verdict": self.instance.verdict.value,
            # Signals: envelope is camelized like every other API field; only
            # `detail` keeps RawJson because it carries arbitrary domain data
            # (slugs, user-defined field names, LLM output) where the keys
            # must not be mangled.
            "signals": [_present_signal(s) for s in self.instance.signals],
            "signals_by_polarity": RawJson(self.instance.signals_by_polarity),
            "signals_by_severity": RawJson(self.instance.signals_by_severity),
            "confidence_score": self.instance.confidence_score,
            "blocking_failures": [str(uid) for uid in self.instance.blocking_failures],
            "degraded_rules": [str(uid) for uid in self.instance.degraded_rules],
            "output": RawJson(self.instance.output),
            "output_schema_snapshot": RawJson(self.instance.output_schema_snapshot),
            "synthesis_template_snapshot": self.instance.synthesis_template_snapshot,
            "narrative_status": self.instance.narrative_status.value,
            "narrative_error": self.instance.narrative_error,
            "model": self.instance.model,
            "provider": self.instance.provider,
            "input_hash": self.instance.input_hash,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }


def _present_signal(signal) -> dict[str, Any]:
    return {
        "rule_id": str(signal.rule_id),
        "kind": signal.kind,
        "severity": signal.severity,
        "polarity": signal.polarity,
        "weight": signal.weight,
        # `detail.reason` is the engine's technical message — humanize it
        # for the FE while leaving the rest of the dict (which may carry
        # arbitrary domain data) untouched via RawJson.
        "detail": RawJson(_humanize_detail(signal.detail)),
    }


def _humanize_detail(detail: dict | None) -> dict | None:
    if not isinstance(detail, dict):
        return detail
    if "reason" not in detail:
        return detail
    return {**detail, "reason": humanize(detail.get("reason"))}
