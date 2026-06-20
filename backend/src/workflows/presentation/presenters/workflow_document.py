from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_document import WorkflowDocument


@dataclass
class WorkflowDocumentPresenter(Presenter[WorkflowDocument]):
    instance: WorkflowDocument

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "case_id": str(self.instance.case_id) if self.instance.case_id else None,
            "document_type_id": str(self.instance.document_type_id) if self.instance.document_type_id else None,
            "file_name": self.instance.file_name,
            "file_id": str(self.instance.file_id) if self.instance.file_id else None,
            "mime_type": self.instance.mime_type,
            "status": str(self.instance.status),
            "source": str(self.instance.source),
            "extraction": RawJson(self.instance.extraction),
            "mapped_extraction": RawJson(self.instance.mapped_extraction),
            # E3 · capa-2 (fase assess): el FE los consumirá tal cual.
            "extract_confidence": self.instance.extract_confidence,
            "signals": self.instance.signals,
            # E5 · Inspection Bench: capa-1 + flags + verificación por campo.
            # RawJson: las claves son fieldPaths (datos), no se camelizan.
            "field_confidence": RawJson(self.instance.field_confidence),
            "needs_clarification": self.instance.needs_clarification,
            "verification": RawJson(self.instance.verification),
            "extraction_pages": self.instance.extraction_pages,
            "validation": self.instance.validation,
            "extracted_text": self.instance.extracted_text,
            "extraction_metadata": self.instance.extraction_metadata,
            "page_range": self.instance.page_range,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
