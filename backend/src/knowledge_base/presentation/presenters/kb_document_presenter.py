from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.knowledge_base.kb_document import KBDocument


@dataclass
class KBDocumentPresenter(Presenter[KBDocument]):
    instance: KBDocument

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "file_name": self.instance.file_name,
            "slug": self.instance.slug,
            "mime": self.instance.mime,
            "file_id": str(self.instance.file_id) if self.instance.file_id else None,
            "workflow_id": str(self.instance.workflow_id) if self.instance.workflow_id else None,
            "char_count": len(self.instance.extracted_text) if self.instance.extracted_text else 0,
            "preview": (
                self.instance.extracted_text[:300].replace("\n", " ").strip() if self.instance.extracted_text else None
            ),
            "status": self.instance.status.value,
            "chunk_count": self.instance.chunk_count,
            "error_message": self.instance.error_message,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
