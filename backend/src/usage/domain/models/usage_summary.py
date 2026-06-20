from dataclasses import dataclass


@dataclass(frozen=True)
class UsageSummary:
    pages_used: int
    monthly_quota: int | None  # None = unlimited
    period_start: str           # ISO date "YYYY-MM-01"
    period_end: str             # ISO date "YYYY-MM-DD" (last day of month)
    days_remaining: int

    @property
    def usage_pct(self) -> float | None:
        if self.monthly_quota is None:
            return None
        if self.monthly_quota == 0:
            return 100.0
        return round(self.pages_used / self.monthly_quota * 100, 2)

    @property
    def is_at_limit(self) -> bool:
        if self.monthly_quota is None:
            return False
        return self.pages_used >= self.monthly_quota

    @property
    def is_near_limit(self) -> bool:
        pct = self.usage_pct
        if pct is None:
            return False
        return pct >= 80.0
