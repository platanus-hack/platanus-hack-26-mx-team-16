from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.document_type import DocumentType


@dataclass
class DocumentTypePresenter(Presenter[DocumentType]):
    instance: DocumentType

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "name": self.instance.name,
            "is_shareable": self.instance.is_shareable,
            "slug": self.instance.slug,
            "description": self.instance.description,
            "fields": RawJson(self.instance.fields),
            "keywords": self.instance.keywords,
            "examples": self.instance.examples,
            "validation_rules": self.instance.validation_rules,
            "sample_file_id": str(self.instance.sample_file_id) if self.instance.sample_file_id else None,
            "sample_file_text": bool(self.instance.sample_file_text),
            "current_version": self.instance.current_version,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
