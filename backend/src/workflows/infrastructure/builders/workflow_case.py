from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.domain.models.processing.workflow_case import WorkflowCase


def build_workflow_case(orm_instance: WorkflowCaseORM) -> WorkflowCase:
    return WorkflowCase(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        name=orm_instance.name,
        status=orm_instance.status,
        last_ocr_provider=orm_instance.last_ocr_provider,
        external_ref=orm_instance.external_ref,
        pipeline_id=orm_instance.pipeline_id,
        pipeline_version_id=orm_instance.pipeline_version_id,
        parent_case_id=orm_instance.parent_case_id,
        ready_at=orm_instance.ready_at,
        completeness=orm_instance.completeness,
        created_by=orm_instance.created_by,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
