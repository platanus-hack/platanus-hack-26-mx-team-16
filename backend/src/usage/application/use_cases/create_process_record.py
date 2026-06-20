from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant import Tenant
from src.usage.domain.exceptions import QuotaExceededError
from src.usage.domain.models.plan import resolve_monthly_quota
from src.usage.domain.models.process_record import ProcessRecord
from src.usage.domain.repositories.process_record import ProcessRecordRepository


@dataclass
class CreateProcessRecord(UseCase):
    tenant: Tenant
    workflow_id: UUID | None
    object_key_digest: str
    page_count: int
    analysis_run_id: UUID | None
    process_record_repository: ProcessRecordRepository

    async def execute(self) -> ProcessRecord:
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_quota = resolve_monthly_quota(
            self.tenant.plan_slug,
            self.tenant.monthly_page_quota_override,
        )

        if monthly_quota is not None:
            pages_used = await self.process_record_repository.count_pages_by_tenant(
                tenant_id=self.tenant.uuid,
                from_dt=period_start,
                to_dt=now,
            )
            if pages_used >= monthly_quota:
                raise QuotaExceededError(
                    context={
                        "pages_used": pages_used,
                        "monthly_quota": monthly_quota,
                        "plan": self.tenant.plan_slug,
                    }
                )

        record = ProcessRecord(
            uuid=uuid4(),
            tenant_id=self.tenant.uuid,
            workflow_id=self.workflow_id,
            object_key_digest=self.object_key_digest,
            page_count=self.page_count,
            analysis_run_id=self.analysis_run_id,
            processed_at=now,
            created_at=now,
        )
        return await self.process_record_repository.create(record)
