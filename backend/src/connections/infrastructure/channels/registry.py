"""Channel adapter registry (E6 · W5 · diseño §5).

The public endpoint is ``POST /v1/channels/{provider}/{route_token}`` where
``provider`` is the wire family (``email`` | ``whatsapp``) — it must match
``source.provider``. The concrete vendor adapter (mailpit/mailgun/whatsapp_cloud)
is chosen from ``source.config["vendor"]``, with a sensible per-provider default.

Resolution is by ``(provider, vendor)``: this replaces the F12 polling registry
keyed on :class:`ConnectionProvider`.
"""

from __future__ import annotations

from src.common.domain.enums.connections import ConnectionProvider
from src.common.settings import settings
from src.connections.domain.channels.base import ChannelAdapter
from src.connections.infrastructure.channels.email_mailgun import (
    VENDOR as MAILGUN_VENDOR,
    MailgunChannelAdapter,
)
from src.connections.infrastructure.channels.email_mailpit import (
    VENDOR as MAILPIT_VENDOR,
    MailpitChannelAdapter,
)
from src.connections.infrastructure.channels.whatsapp_cloud import (
    VENDOR as WHATSAPP_CLOUD_VENDOR,
    WhatsappCloudChannelAdapter,
)

# URL provider segment → ConnectionProvider it must resolve against.
PROVIDER_BY_URL: dict[str, ConnectionProvider] = {
    "email": ConnectionProvider.EMAIL,
    "whatsapp": ConnectionProvider.WHATSAPP,
}

# (url provider, vendor) → adapter instance.
_CHANNEL_ADAPTERS: dict[tuple[str, str], ChannelAdapter] = {
    ("email", MAILPIT_VENDOR): MailpitChannelAdapter(),
    ("email", MAILGUN_VENDOR): MailgunChannelAdapter(),
    ("whatsapp", WHATSAPP_CLOUD_VENDOR): WhatsappCloudChannelAdapter(),
}

# Default vendor per URL provider when source.config omits "vendor".
_DEFAULT_VENDOR: dict[str, str] = {
    "email": MAILPIT_VENDOR,
    "whatsapp": WHATSAPP_CLOUD_VENDOR,
}

# Vendors whose adapter has NO signature scheme (``verify`` accepts unsigned
# requests). They are dev/local only — the route_token is published in the
# inbound alias and is NOT a secret, so an unsigned adapter on a public endpoint
# accepts forged webhooks. NEVER let one resolve in production.
_UNSIGNED_VENDORS: frozenset[tuple[str, str]] = frozenset({("email", MAILPIT_VENDOR)})


def is_signed_vendor(provider: str, vendor: str) -> bool:
    """``True`` when ``(provider, vendor)`` authenticates inbound webhooks."""
    return (provider, vendor) not in _UNSIGNED_VENDORS


def resolve_vendor(provider: str, config: dict) -> str:
    explicit = config.get("vendor")
    if explicit:
        return str(explicit)
    # Defensive: never silently fall back to an unsigned dev vendor (mailpit) in
    # production — a pre-existing source created without an explicit vendor must
    # not become an unauthenticated webhook sink. Returning "" yields no adapter,
    # so the endpoint 404s instead of accepting forged traffic.
    default = _DEFAULT_VENDOR.get(provider, "")
    if settings.ENVIRONMENT.is_production and not is_signed_vendor(provider, default):
        return ""
    return default


def get_channel_adapter(provider: str, vendor: str) -> ChannelAdapter | None:
    return _CHANNEL_ADAPTERS.get((provider, vendor))
