from src.common.database.models.processing.workflow_analysis_run import WorkflowAnalysisRunORM
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun


def build_workflow_analysis_run(orm_instance: WorkflowAnalysisRunORM) -> WorkflowAnalysisRun:
    return WorkflowAnalysisRun(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        workflow_case_id=orm_instance.workflow_case_id,
        status=WorkflowAnalysisRunStatus(orm_instance.status),
        trigger=WorkflowAnalysisRunTrigger(orm_instance.trigger),
        triggered_by=orm_instance.triggered_by,
        started_at=orm_instance.started_at,
        completed_at=orm_instance.completed_at,
        canceled_at=orm_instance.canceled_at,
        canceled_by=orm_instance.canceled_by,
        error=orm_instance.error,
        reviewer_model=orm_instance.reviewer_model,
        critic_model=orm_instance.critic_model,
        consensus_samples=orm_instance.consensus_samples,
        rules_total=orm_instance.rules_total,
        rules_passed=orm_instance.rules_passed,
        rules_failed=orm_instance.rules_failed,
        rules_inconclusive=orm_instance.rules_inconclusive,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
