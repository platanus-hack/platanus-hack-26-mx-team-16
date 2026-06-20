from src.common.database.models.processing.workflow_rule import WorkflowRuleORM
from src.common.domain.models.processing.workflow_rule import WorkflowRule


def build_workflow_rule(orm_instance: WorkflowRuleORM) -> WorkflowRule:
    return WorkflowRule(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        name=orm_instance.name,
        slug=orm_instance.slug,
        position=orm_instance.position,
        is_active=orm_instance.is_active,
        kind=orm_instance.kind,
        prompt=orm_instance.prompt,
        when=orm_instance.when_expr,
        config=orm_instance.config or {},
        scope=orm_instance.scope or {"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=list(orm_instance.knowledge_refs or []),
        current_compilation_id=orm_instance.current_compilation_id,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
