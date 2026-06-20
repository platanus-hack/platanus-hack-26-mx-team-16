"""Read which workflow rules are currently compiling (Redis-backed set)."""

from dataclasses import dataclass
from uuid import UUID

from redis.asyncio import Redis

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.events import compiling_rules_key


@dataclass
class WorkflowCompilingRulesStateGetter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    redis_client: Redis

    async def execute(self) -> list[str]:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        members = await self.redis_client.smembers(compiling_rules_key(self.workflow_id))
        return sorted(m.decode("utf-8") if isinstance(m, bytes) else m for m in members)
