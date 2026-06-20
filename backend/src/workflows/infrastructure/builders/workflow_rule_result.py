from typing import Any

from pydantic import ValidationError

from src.common.database.models.processing.workflow_rule_result import WorkflowRuleResultORM
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult


def build_workflow_rule_result(orm_instance: WorkflowRuleResultORM) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_analysis_run_id=orm_instance.workflow_analysis_run_id,
        rule_id=orm_instance.rule_id,
        case_id=orm_instance.case_id,
        kind=orm_instance.kind,
        status=WorkflowRuleResultStatus(orm_instance.status),
        output=orm_instance.output,
        reasoning=orm_instance.reasoning,
        citations=_decode_citations(orm_instance.citations),
        document_refs=orm_instance.document_refs or {},
        document_refs_hash=orm_instance.document_refs_hash,
        rendered_prompt=orm_instance.rendered_prompt,
        evaluation_metadata=orm_instance.evaluation_metadata or {},
        error=orm_instance.error,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )


def _decode_citations(raw: Any) -> list[Citation]:
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    decoded: list[Citation] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            decoded.append(Citation.model_validate(entry))
        except ValidationError:
            # Legacy shape without the canonical fields — skip rather than fail.
            continue
    return decoded
