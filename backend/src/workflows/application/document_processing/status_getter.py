from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client as TemporalClient, WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

from src.common.domain.interfaces.use_case import UseCase

_TERMINAL_STATUSES = {
    WorkflowExecutionStatus.COMPLETED,
    WorkflowExecutionStatus.FAILED,
    WorkflowExecutionStatus.CANCELED,
    WorkflowExecutionStatus.TERMINATED,
    WorkflowExecutionStatus.TIMED_OUT,
}


def _status_label(status: WorkflowExecutionStatus | None) -> str:
    if status is None:
        return "unknown"
    return status.name.lower()


def _as_dict(value) -> dict:
    return value.model_dump() if hasattr(value, "model_dump") else value


@dataclass
class ExtractionStatusGetter(UseCase):
    case_id: UUID
    document_id: UUID
    tenant_id: UUID
    temporal_client: TemporalClient

    async def execute(self) -> dict:
        job_id = f"case:{self.case_id.hex}_{self.document_id.hex}"
        handle = self.temporal_client.get_workflow_handle(job_id)

        try:
            description = await handle.describe()
        except RPCError as err:
            if err.status == RPCStatusCode.NOT_FOUND:
                return {"workflowId": job_id, "status": "not_started"}
            raise

        status = description.status
        payload: dict = {
            "workflowId": job_id,
            "status": _status_label(status),
            "done": status in _TERMINAL_STATUSES,
        }

        if status == WorkflowExecutionStatus.COMPLETED:
            try:
                payload["result"] = _as_dict(await handle.result())
            except Exception as err:  # noqa: BLE001 — surface the message, don't crash polling
                payload["error"] = str(err)
        elif status in _TERMINAL_STATUSES:
            try:
                await handle.result()
            except Exception as err:  # noqa: BLE001
                payload["error"] = str(err)

        return payload
