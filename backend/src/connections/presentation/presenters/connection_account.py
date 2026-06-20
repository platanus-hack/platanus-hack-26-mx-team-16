from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.connections.domain.models.connection_account import ConnectionAccount


@dataclass
class ConnectionAccountPresenter(Presenter[ConnectionAccount]):
    """Org connection-account view. Never exposes the stored ``secret`` — only a
    ``has_secret`` flag (spec connections §2.1/§9)."""

    instance: ConnectionAccount

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "provider": self.instance.provider.value,
            "display_name": self.instance.display_name,
            "capabilities": [c.value for c in self.instance.capabilities],
            "status": self.instance.status.value,
            "config": RawJson(self.instance.config),
            "has_secret": self.instance.secret is not None,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
