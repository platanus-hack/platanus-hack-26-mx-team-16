from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.entities.tenants.tenant_branch import TenantBranch
from src.common.domain.interfaces.presenter import Presenter
from src.common.presentation.presenters.payment_permalink import PaymentPermaLinkPresenter


@dataclass
class TenantBranchPresenter(Presenter[TenantBranch]):
    instance: TenantBranch

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "label": self.instance.label,
            "description": self.instance.description,
            "address": self.instance.address,
            "city": self.instance.city,
            "state_province": self.instance.state_province,
            "status": str(self.instance.status),
            "branch_type": str(self.instance.branch_type),
            "contact_email": self.instance.contact_email,
            "operating_hours": self.instance.operating_hours,
            "payment_permalink": (
                PaymentPermaLinkPresenter(self.instance.payment_permalink).to_dict
                if self.instance.payment_permalink
                else None
            ),
            "created_at": optional_datetime_string(self.instance.created_at),
        }


@dataclass
class TenantBranchPublicPresenter(Presenter[TenantBranch]):
    instance: TenantBranch

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "label": self.instance.label,
            "address": self.instance.address,
            "city": self.instance.city,
            "state_province": self.instance.state_province,
            "branch_type": str(self.instance.branch_type),
        }
