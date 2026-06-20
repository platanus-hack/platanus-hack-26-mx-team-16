from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.usage.domain.models.process_record import ProcessRecord
from src.usage.domain.models.usage_summary import UsageSummary


@dataclass
class ProcessRecordPresenter(Presenter[ProcessRecord]):
    instance: ProcessRecord

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenantId": str(self.instance.tenant_id),
            "workflowId": str(self.instance.workflow_id) if self.instance.workflow_id else None,
            "workflowName": self.instance.workflow_name,
            "objectKeyDigest": self.instance.object_key_digest,
            "pageCount": self.instance.page_count,
            "analysisRunId": str(self.instance.analysis_run_id) if self.instance.analysis_run_id else None,
            "processedAt": self.instance.processed_at.isoformat(),
            "createdAt": self.instance.created_at.isoformat(),
        }


@dataclass
class UsageSummaryPresenter(Presenter[UsageSummary]):
    instance: UsageSummary

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "pagesUsed": self.instance.pages_used,
            "monthlyQuota": self.instance.monthly_quota,
            "usagePct": self.instance.usage_pct,
            "isAtLimit": self.instance.is_at_limit,
            "isNearLimit": self.instance.is_near_limit,
            "periodStart": self.instance.period_start,
            "periodEnd": self.instance.period_end,
            "daysRemaining": self.instance.days_remaining,
        }
