import calendar
from dataclasses import dataclass
from datetime import UTC, datetime

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant import Tenant
from src.usage.domain.models.plan import resolve_monthly_quota
from src.usage.domain.models.usage_summary import UsageSummary
from src.usage.domain.repositories.process_record import ProcessRecordRepository


@dataclass
class GetProcessRecordsSummary(UseCase):
    tenant: Tenant
    process_record_repository: ProcessRecordRepository

    async def execute(self) -> UsageSummary:
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        period_end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

        pages_used = await self.process_record_repository.count_pages_by_tenant(
            tenant_id=self.tenant.uuid,
            from_dt=period_start,
            to_dt=period_end,
        )
        monthly_quota = resolve_monthly_quota(
            self.tenant.plan_slug,
            self.tenant.monthly_page_quota_override,
        )
        days_remaining = (period_end.date() - now.date()).days

        return UsageSummary(
            pages_used=pages_used,
            monthly_quota=monthly_quota,
            period_start=period_start.date().isoformat(),
            period_end=period_end.date().isoformat(),
            days_remaining=days_remaining,
        )
