from dataclasses import dataclass
from typing import Any

from src.common.domain.models.email_address import EmailAddress
from src.common.domain.interfaces.presenter import Presenter


@dataclass
class EmailAddressPresenter(Presenter[EmailAddress]):
    instance: EmailAddress

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "email": self.instance.email,
            "is_verified": self.instance.is_verified,
        }
