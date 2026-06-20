from src.common.database.models.workflow_event import WorkflowEventORM
from src.common.domain.models.workflow_event import WorkflowEvent


def build_workflow_event(orm_instance: WorkflowEventORM) -> WorkflowEvent:
    """Map a ``WorkflowEventORM`` row to the domain model.

    ``event_type`` / ``delivery_status`` are stored as strings and coerced to
    their enums by Pydantic on construction.
    """
    return WorkflowEvent(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        event_id=orm_instance.event_id,
        event_type=orm_instance.event_type,
        workflow_id=orm_instance.workflow_id,
        processing_job_id=orm_instance.processing_job_id,
        document_id=orm_instance.document_id,
        destination_id=orm_instance.destination_id,
        idempotency_key=orm_instance.idempotency_key,
        document_status=orm_instance.document_status,
        payload=orm_instance.payload,
        delivery_status=orm_instance.delivery_status,
        attempts=orm_instance.attempts,
        last_attempt_at=orm_instance.last_attempt_at,
        delivered_at=orm_instance.delivered_at,
        response_status=orm_instance.response_status,
        last_error=orm_instance.last_error,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
