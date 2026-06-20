"""Use cases for org-level connection accounts (spec connections §2.1)."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.common.domain.enums.connections import (
    PROVIDER_CAPABILITIES,
    ConnectionCapability,
    ConnectionProvider,
    ConnectionStatus,
)
from src.common.domain.interfaces.use_case import UseCase
from src.connections.domain.exceptions import (
    ConnectionAccountNotFoundError,
    InvalidConnectionCapabilityError,
)
from src.connections.domain.models.connection_account import ConnectionAccount
from src.connections.domain.repositories.connection_account import ConnectionAccountRepository


def _validate_capabilities(provider: ConnectionProvider, capabilities: list[ConnectionCapability]) -> None:
    allowed = PROVIDER_CAPABILITIES.get(provider, set())
    for capability in capabilities:
        if capability not in allowed:
            raise InvalidConnectionCapabilityError(provider=provider.value, capability=capability.value)


@dataclass
class CreateConnectionAccount(UseCase):
    tenant_id: UUID
    provider: ConnectionProvider
    display_name: str
    repo: ConnectionAccountRepository
    capabilities: list[ConnectionCapability] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    secret: str | None = None

    async def execute(self) -> ConnectionAccount:
        capabilities = self.capabilities or sorted(
            PROVIDER_CAPABILITIES.get(self.provider, set()), key=lambda c: c.value
        )
        _validate_capabilities(self.provider, capabilities)
        account = ConnectionAccount(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            provider=self.provider,
            display_name=self.display_name,
            capabilities=capabilities,
            status=ConnectionStatus.CONNECTED,
            config=self.config,
            secret=self.secret,
        )
        return await self.repo.create(account)


@dataclass
class ListConnectionAccounts(UseCase):
    tenant_id: UUID
    repo: ConnectionAccountRepository

    async def execute(self) -> list[ConnectionAccount]:
        return await self.repo.list_by_tenant(tenant_id=self.tenant_id)


@dataclass
class GetConnectionAccount(UseCase):
    account_id: UUID
    tenant_id: UUID
    repo: ConnectionAccountRepository

    async def execute(self) -> ConnectionAccount:
        account = await self.repo.find_by_id(self.account_id, self.tenant_id)
        if account is None:
            raise ConnectionAccountNotFoundError(str(self.account_id))
        return account


@dataclass
class UpdateConnectionAccount(UseCase):
    account_id: UUID
    tenant_id: UUID
    repo: ConnectionAccountRepository
    display_name: str | None = None
    capabilities: list[ConnectionCapability] | None = None
    status: ConnectionStatus | None = None
    config: dict | None = None
    secret: str | None = None

    async def execute(self) -> ConnectionAccount:
        account = await self.repo.find_by_id(self.account_id, self.tenant_id)
        if account is None:
            raise ConnectionAccountNotFoundError(str(self.account_id))

        if self.display_name is not None:
            account.display_name = self.display_name
        if self.capabilities is not None:
            _validate_capabilities(account.provider, self.capabilities)
            account.capabilities = self.capabilities
        if self.status is not None:
            account.status = self.status
        if self.config is not None:
            account.config = self.config
        if self.secret is not None:
            account.secret = self.secret
        return await self.repo.update(account)


@dataclass
class DeleteConnectionAccount(UseCase):
    account_id: UUID
    tenant_id: UUID
    repo: ConnectionAccountRepository

    async def execute(self) -> None:
        account = await self.repo.find_by_id(self.account_id, self.tenant_id)
        if account is None:
            raise ConnectionAccountNotFoundError(str(self.account_id))
        await self.repo.delete(self.account_id, self.tenant_id)
