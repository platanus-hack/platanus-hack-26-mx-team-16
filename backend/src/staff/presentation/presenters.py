"""Presenters del plano staff — snake_case aquí; ``ApiJSONResponse``
convierte a camelCase en el wire. Blobs con claves de dominio (payload,
extracción, verificación) van en ``RawJson`` para no corromper field paths.
"""

from src.common.application.helpers.json_encoder import RawJson
from src.staff.application.metrics import StaffMetrics
from src.staff.domain.entities import StaffCaseAggregate, StaffQueueItem
from src.staff.domain.models.staff_access_event import StaffAccessEvent
from src.workflows.domain.models.human_task import HumanTask


def present_task(task: HumanTask, tenant_name: str | None = None, tenant_slug: str | None = None) -> dict:
    return {
        "uuid": str(task.uuid),
        "task_key": task.task_key,
        "kind": task.kind.value,
        "status": task.status.value,
        "stage": task.stage,
        "assignee_mode": task.assignee_mode.value,
        "audience": task.audience,
        "case_id": str(task.case_id) if task.case_id else None,
        "workflow_id": str(task.workflow_id) if task.workflow_id else None,
        # Cola unificada cross-tenant: el tenant viaja con cada tarea.
        "tenant_id": str(task.tenant_id),
        "tenant_name": tenant_name,
        "tenant_slug": tenant_slug,
        "claimed_by": task.claimed_by,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "payload": RawJson(task.payload),
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def present_queue_item(item: StaffQueueItem) -> dict:
    return present_task(item.task, tenant_name=item.tenant_name, tenant_slug=item.tenant_slug)


def _present_document(document) -> dict:
    return {
        "document_id": str(document.uuid),
        "document_type_id": str(document.document_type_id) if document.document_type_id else None,
        "source": document.source.value if hasattr(document.source, "value") else document.source,
        "status": document.processing_status
        or (document.status.value if getattr(document, "status", None) else None),
        "file_name": document.file_name,
        # Lo que el bench staff necesita para resolver la tarea (read-only).
        "mapped_extraction": RawJson(document.mapped_extraction),
        "field_confidence": RawJson(document.field_confidence),
        "needs_clarification": RawJson(document.needs_clarification),
        "verification": RawJson(getattr(document, "verification", None)),
    }


def present_case_aggregate(aggregate: StaffCaseAggregate) -> dict:
    case = aggregate.case
    summary = aggregate.latest_summary
    return {
        "case_id": str(case.uuid),
        "workflow_id": str(case.workflow_id),
        "tenant_id": str(case.tenant_id),
        "tenant_name": aggregate.tenant_name,
        "tenant_slug": aggregate.tenant_slug,
        "name": case.name,
        "status": case.status.value if hasattr(case.status, "value") else case.status,
        "external_ref": case.external_ref,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "ready_at": case.ready_at.isoformat() if getattr(case, "ready_at", None) else None,
        "read_only": True,  # la superficie staff jamás escribe sobre el caso
        "documents": [_present_document(d) for d in aggregate.documents],
        "runs": [
            {
                "run_id": str(r.uuid),
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "trigger": r.trigger.value if hasattr(r.trigger, "value") else r.trigger,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if getattr(r, "completed_at", None) else None,
            }
            for r in aggregate.runs
        ],
        "latest_output": (
            {
                "verdict": summary.verdict.value if summary.verdict else None,
                "confidence_score": summary.confidence_score,
                "narrative_status": summary.narrative_status.value if summary.narrative_status else None,
                "has_output": summary.output is not None,
            }
            if summary is not None
            else None
        ),
        "timeline": [
            {
                "uuid": str(e.uuid),
                "type": e.type,
                "payload": RawJson(e.payload),
                "actor": e.actor,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in aggregate.timeline or []
        ],
    }


def present_metrics(metrics: StaffMetrics) -> dict:
    # RawJson en los cortes: las claves son tenant_id / actor (no field paths,
    # pero tampoco queremos camelizarlas).
    return {
        "since": metrics.since.isoformat(),
        "totals": RawJson(metrics.totals),
        "by_tenant": RawJson(metrics.by_tenant),
        "by_actor": RawJson(metrics.by_actor),
    }


def present_access_event(event: StaffAccessEvent) -> dict:
    return {
        "uuid": str(event.uuid),
        "staff_user_id": str(event.staff_user_id),
        "action": event.action,
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "case_id": str(event.case_id) if event.case_id else None,
        "task_id": str(event.task_id) if event.task_id else None,
        "request_id": event.request_id,
        "ip": event.ip,
        "metadata": RawJson(event.metadata),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
