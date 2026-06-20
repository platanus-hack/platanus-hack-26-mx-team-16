from src.common.domain.enums.base_enum import BaseEnum


class KBDocumentStatus(BaseEnum):
    VECTORIZING = "vectorizing"
    READY = "ready"
    FAILED = "failed"
