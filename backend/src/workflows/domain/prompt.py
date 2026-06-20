from dataclasses import dataclass

from src.common.domain.enums.base_enum import BaseEnum


class TokenKind(BaseEnum):
    DOCUMENT_FIELD = "document_field"
    SYSTEM_VAR = "system_var"

    @property
    def is_document_field(self) -> bool:
        return self == self.DOCUMENT_FIELD

    @property
    def is_system_var(self) -> bool:
        return self == self.SYSTEM_VAR


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    raw: str
    doc_slug: str | None = None
    field_key: str | None = None
    var_key: str | None = None
