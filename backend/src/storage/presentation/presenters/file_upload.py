from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.file_upload import Document


@dataclass
class FileUploadPresenter(Presenter[Document]):
    instance: Document
    presigned_url: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "file_name": self.instance.file_name,
            "mime": self.instance.mime,
            "size": self.instance.size,
            "s3_key": self.instance.s3_key,
            "presigned_url": self.presigned_url,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
