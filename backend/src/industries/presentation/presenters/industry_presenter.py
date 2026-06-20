from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.industry import Industry


@dataclass
class IndustryPresenter(Presenter[Industry]):
    instance: Industry

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "slug": self.instance.slug,
            "name": self.instance.name,
            "icon": self.instance.icon,
            "description": self.instance.description,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
