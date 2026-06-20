from src.common.domain.exceptions._base import DomainError


class KBDocumentNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="knowledge_base.DocumentNotFound",
            message=f"KB document not found: {identifier}" if identifier else "KB document not found",
            status_code=404,
        )


class KBUnsupportedFileTypeError(DomainError):
    def __init__(self, mime_type: str = ""):
        super().__init__(
            code="knowledge_base.UnsupportedFileType",
            message=f"Unsupported file type for KB: {mime_type}" if mime_type else "Unsupported file type",
            status_code=400,
        )


class KBTextExtractionError(DomainError):
    def __init__(self, detail: str = ""):
        super().__init__(
            code="knowledge_base.TextExtractionFailed",
            message=f"Text extraction failed: {detail}" if detail else "Text extraction failed",
            status_code=422,
        )


class KBEmbeddingError(DomainError):
    def __init__(self, detail: str = ""):
        super().__init__(
            code="knowledge_base.EmbeddingFailed",
            message=f"Embedding generation failed: {detail}" if detail else "Embedding generation failed",
            status_code=500,
        )


class KBDocumentSlugConflictError(DomainError):
    def __init__(self, slug: str, scope: str = ""):
        scope_label = f" in {scope}" if scope else ""
        super().__init__(
            code="knowledge_base.SlugConflict",
            message=f"KB document slug already in use{scope_label}: {slug}",
            status_code=409,
        )


class KBDocumentInvalidSlugError(DomainError):
    def __init__(self, slug: str):
        super().__init__(
            code="knowledge_base.InvalidSlug",
            message=(f"KB document slug must match ^[a-z0-9][a-z0-9_-]{{0,99}}$ (got: {slug!r})"),
            status_code=400,
        )
