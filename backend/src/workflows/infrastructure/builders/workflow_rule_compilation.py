from src.common.database.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilationORM,
)
from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)


def build_workflow_rule_compilation(
    orm_instance: WorkflowRuleCompilationORM,
) -> WorkflowRuleCompilation:
    return WorkflowRuleCompilation(
        uuid=orm_instance.uuid,
        rule_id=orm_instance.rule_id,
        version=orm_instance.version,
        kind=orm_instance.kind,
        status=WorkflowRuleCompilationStatus(orm_instance.status),
        artifact=orm_instance.artifact,
        compiled_with=orm_instance.compiled_with,
        error=orm_instance.error,
        created_at=orm_instance.created_at,
        completed_at=orm_instance.completed_at,
    )
