from src.common.domain.mixins.entities import CamelModel


class TenantUserStats(CamelModel):
    total: int
    active: int
    pending: int
    inactive: int
