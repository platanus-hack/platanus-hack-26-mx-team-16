from src.common.domain.enums.base_enum import BaseEnum


class ConnectionProvider(BaseEnum):
    """External system a connection account talks to (spec connections §2.1)."""

    WEBHOOK = "WEBHOOK"  # outbound HTTP endpoint
    SLACK = "SLACK"  # outbound channel messages (OAuth, phase 3)
    EMAIL = "EMAIL"  # inbound + outbound mail
    WHATSAPP = "WHATSAPP"  # inbound + outbound (phase 2)
    DRIVE = "DRIVE"  # inbound documents (phase 2)
    HTTP = "HTTP"  # generic HTTP API for lookup Tools (F5 · A3)


class ConnectionCapability(BaseEnum):
    """What a connection account can do. An account may declare several."""

    RECEIVE = "RECEIVE"  # can act as an Origin (inbound files)
    SEND = "SEND"  # can act as a Destination (outbound results)
    LOOKUP = "LOOKUP"  # backs a Tool the pipeline calls mid-run (F5 · A3)


class ConnectionStatus(BaseEnum):
    """Health of a connected account (spec connections §7)."""

    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"  # OAuth token needs refresh / reauth
    REVOKED = "REVOKED"

    @property
    def is_connected(self) -> bool:
        return self == self.CONNECTED


# Capabilities a provider is allowed to declare (validated on create).
PROVIDER_CAPABILITIES: dict[ConnectionProvider, set[ConnectionCapability]] = {
    ConnectionProvider.WEBHOOK: {ConnectionCapability.SEND},
    ConnectionProvider.SLACK: {ConnectionCapability.SEND},
    ConnectionProvider.EMAIL: {ConnectionCapability.RECEIVE, ConnectionCapability.SEND},
    ConnectionProvider.WHATSAPP: {ConnectionCapability.RECEIVE, ConnectionCapability.SEND},
    ConnectionProvider.DRIVE: {ConnectionCapability.RECEIVE},
    ConnectionProvider.HTTP: {ConnectionCapability.LOOKUP},
}
