"""Activity: open (idempotently) a durable HumanTask for a pause phase (F6)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.domain.entities.workflows.human_task_io import (
    CreateHumanTaskInput,
    CreateHumanTaskOutput,
)
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository


class CreateHumanTaskActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="create_human_task")
    async def create_human_task(self, payload: CreateHumanTaskInput) -> CreateHumanTaskOutput:
        data = CreateHumanTaskInput.model_validate(payload)
        async with self._session_maker() as session:
            task = await SQLHumanTaskRepository(session).upsert(
                HumanTask(
                    uuid=uuid4(),
                    tenant_id=data.tenant_id,
                    task_key=data.task_key,
                    kind=data.kind,
                    assignee_mode=data.assignee_mode,
                    audience=data.audience,
                    workflow_id=data.workflow_id,
                    case_id=data.case_id,
                    pipeline_run_id=data.pipeline_run_id,
                    payload=data.payload,
                )
            )
        return CreateHumanTaskOutput(task_id=task.uuid, task_key=task.task_key)
