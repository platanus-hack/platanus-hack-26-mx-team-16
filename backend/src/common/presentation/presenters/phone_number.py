from dataclasses import dataclass
from typing import Any

from src.common.domain.models.phone_number import PhoneNumber
from src.common.domain.interfaces.presenter import Presenter


@dataclass
class PhoneNumberPresenter(Presenter[PhoneNumber]):
    instance: PhoneNumber

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "dial_code": self.instance.dial_code,
            "phone_number": self.instance.phone_number,
            "is_verified": self.instance.is_verified,
        }
