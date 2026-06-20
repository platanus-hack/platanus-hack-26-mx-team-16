from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.presentation.helpers.humanize_reasoning import humanize


@dataclass
class WorkflowRuleResultPresenter(Presenter[WorkflowRuleResult]):
    instance: WorkflowRuleResult
    rule_name: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_analysis_run_id": str(self.instance.workflow_analysis_run_id),
            "rule_id": str(self.instance.rule_id),
            "rule_name": self.rule_name,
            "case_id": str(self.instance.case_id),
            "kind": self.instance.kind,
            "status": self.instance.status.value,
            "is_passed": _derive_is_passed(self.instance),
            "output": RawJson(self.instance.output),
            "reasoning": humanize(self.instance.reasoning),
            # Citations: envelope keys go through camelization so the FE
            # reads `documentId`, `fieldPath`, etc. (the rest of the API
            # contract). Each scalar value is preserved verbatim.
            "citations": [_present_citation(c) for c in self.instance.citations],
            "document_refs": RawJson(self.instance.document_refs),
            "document_refs_hash": self.instance.document_refs_hash,
            "rendered_prompt": self.instance.rendered_prompt,
            "evaluation_metadata": RawJson(self.instance.evaluation_metadata),
            "error": self.instance.error,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }


def _derive_is_passed(result: WorkflowRuleResult) -> bool | None:
    """Top-level pass/fail signal exposed as `isPassed` on the wire.

    Returning `None` keeps the FE on the inconclusive (amber) badge,
    which is the right rendering for ERRORED / SKIPPED rows or any
    output shape that doesn't expose a boolean `passed`.
    """
    if result.status != WorkflowRuleResultStatus.SUCCESS:
        return None
    if not isinstance(result.output, dict):
        return None
    raw = result.output.get("passed")
    return raw if isinstance(raw, bool) else None


def _present_citation(citation) -> dict[str, Any]:
    payload = citation.model_dump(mode="json")
    return {
        "value": payload.get("value"),
        "field_path": payload.get("field_path"),
        "document_id": payload.get("document_id"),
        "document_type_slug": payload.get("document_type_slug"),
        "sub_check_id": payload.get("sub_check_id"),
    }
