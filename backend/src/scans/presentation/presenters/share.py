"""Share-token presenter — ``PublicReport`` → camelCase (``POST /scans/{id}/share``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.domain.models.public_report import PublicReport


@dataclass
class ShareTokenPresenter(Presenter[PublicReport]):
    instance: PublicReport

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.instance.token,
            "url": f"/r/{self.instance.token}",
            "scanId": str(self.instance.scan_id),
            "expiresAt": self.instance.expires_at,
            "createdAt": self.instance.created_at,
        }
