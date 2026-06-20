from src.common.domain.enums.base_enum import BaseEnum


class PlanSlug(str, BaseEnum):
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


# None means unlimited
PLAN_PAGE_QUOTAS: dict[PlanSlug, int | None] = {
    PlanSlug.STARTER: 500,
    PlanSlug.PRO: 5_000,
    PlanSlug.BUSINESS: 25_000,
    PlanSlug.ENTERPRISE: None,
}

DEFAULT_PLAN = PlanSlug.STARTER


def resolve_monthly_quota(plan_slug: str, quota_override: int | None) -> int | None:
    """Return effective monthly page quota for a tenant.

    quota_override takes precedence over the plan default (used for custom
    Enterprise contracts). Returns None for unlimited.
    """
    if quota_override is not None:
        return quota_override
    slug = PlanSlug(plan_slug)
    return PLAN_PAGE_QUOTAS.get(slug)
