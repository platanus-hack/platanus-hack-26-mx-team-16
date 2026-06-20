from src.common.domain.exceptions._base import DomainError


class ConnectionAccountNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="connections.AccountNotFound",
            message=(f"Connection account not found: {identifier}" if identifier else "Connection account not found"),
            status_code=404,
        )


class InvalidConnectionCapabilityError(DomainError):
    def __init__(self, provider: str = "", capability: str = ""):
        super().__init__(
            code="connections.InvalidCapability",
            message=f"Provider {provider!r} does not support capability {capability!r}",
            status_code=400,
        )


# ── Ingest Source errors (F8) ────────────────────────────────────────────────
class SourceNotFoundError(DomainError):
    def __init__(self, route_token: str = ""):
        super().__init__(
            code="source.not_found",
            message="No ingest source matches this token.",
            status_code=404,
            context={"route_token": route_token},
        )


class SourceAuthFailedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="source.auth_failed",
            message="Ingest authentication failed.",
            status_code=401,
        )


class SourcePipelineNotConfiguredError(DomainError):
    def __init__(self, slug: str = ""):
        super().__init__(
            code="source.pipeline_not_configured",
            message="The source's workflow has no active pipeline version.",
            status_code=409,
            context={"pipeline_slug": slug},
        )


# ── Ingest case linkage (spec source_webhooks §7.2/§7.3 · E4) ────────────────
class IngestCaseNotFoundError(DomainError):
    def __init__(self, case_ref: str = ""):
        super().__init__(
            code="ingest.CaseNotFound",
            message="No case matches the given caseId in this workflow.",
            status_code=400,
            context={"case_id": case_ref},
        )


class IngestCaseNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ingest.CaseNotAllowed",
            message="caseId/caseName are only valid for ANALYSIS workflows.",
            status_code=400,
        )


# ── Native channels (email / WhatsApp · E6 · W5) ─────────────────────────────
class ChannelProviderMismatchError(DomainError):
    """The URL provider does not match the resolved Source's provider."""

    def __init__(self, url_provider: str = "", source_provider: str = ""):
        super().__init__(
            code="channel.ProviderMismatch",
            message="The channel provider does not match this source.",
            status_code=404,
            context={"url_provider": url_provider, "source_provider": source_provider},
        )


class ChannelSignatureInvalidError(DomainError):
    """The provider signature on the inbound webhook did not verify."""

    def __init__(self) -> None:
        super().__init__(
            code="channel.SignatureInvalid",
            message="Channel webhook signature verification failed.",
            status_code=401,
        )


class ChannelUnsupportedProviderError(DomainError):
    """No adapter is registered for the requested channel provider."""

    def __init__(self, provider: str = ""):
        super().__init__(
            code="channel.UnsupportedProvider",
            message="No channel adapter is registered for this provider.",
            status_code=404,
            context={"provider": provider},
        )
