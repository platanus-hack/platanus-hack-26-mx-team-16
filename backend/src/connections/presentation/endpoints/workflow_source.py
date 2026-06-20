"""Configurable ingest Source endpoints (F8). JWT-admin management of Sources."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, status
from pydantic import BaseModel, Field

from src.common.application.helpers.secrets import (
    SECRET_PREFIX_API_KEY,
    SECRET_PREFIX_HMAC,
    SECRET_PREFIX_ROUTE_TOKEN,
    generate_base64_secret,
    generate_url_safe_token,
    hash_token,
)
from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.enums.sources import SourceAuthMode
from src.common.domain.exceptions._base import DomainError
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.connections.domain.exceptions import SourceNotFoundError
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.infrastructure.channels.registry import is_signed_vendor, resolve_vendor
from src.connections.infrastructure.repositories.sql_workflow_source import (
    SQLWorkflowSourceRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)

# URL provider segment for native channel sources (matches the channels router).
_CHANNEL_URL_BY_PROVIDER = {
    ConnectionProvider.EMAIL: "email",
    ConnectionProvider.WHATSAPP: "whatsapp",
}


def _validate_channel_config(provider: ConnectionProvider, config: dict) -> None:
    """Reject channel sources that would accept unsigned webhooks in production.

    The public ``/v1/channels/{provider}/{route_token}`` endpoint trusts the
    vendor adapter's ``verify``. Unsigned vendors (mailpit) accept any request,
    and the route_token is published in the inbound alias (not a secret), so an
    EMAIL source created in production without an explicit SIGNED vendor would be
    an open, forgeable webhook sink. Dev/test keep mailpit as the default.
    """
    if not settings.ENVIRONMENT.is_production:
        return
    url_provider = _CHANNEL_URL_BY_PROVIDER.get(provider)
    if url_provider is None:
        return
    vendor = resolve_vendor(url_provider, config)
    if not vendor or not is_signed_vendor(url_provider, vendor):
        raise DomainError(
            code="source.unsigned_channel_vendor",
            message=(
                "Channel sources require an explicit signed vendor in production "
                "(e.g. config.vendor='mailgun'); the unsigned dev vendor is rejected."
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            context={"provider": url_provider, "vendor": vendor or None},
        )


class CreateSourceRequest(BaseModel):
    workflow_id: UUID
    # E6 · W5: webhook (API ingest, default) | email | whatsapp (native channels).
    provider: ConnectionProvider = ConnectionProvider.WEBHOOK
    account_id: UUID | None = None
    auth_mode: SourceAuthMode = SourceAuthMode.API_KEY
    config: dict = Field(default_factory=dict)


def _present(source: WorkflowSource) -> dict:
    presented = {
        "uuid": str(source.uuid),
        "workflow_id": str(source.workflow_id),
        "provider": source.provider.value,
        "account_id": str(source.account_id) if source.account_id else None,
        "route_token": source.route_token,
        "auth_mode": source.auth_mode.value,
        "enabled": source.enabled,
        "has_secret": source.secret is not None,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }
    # The public URL depends on the kind of source: API ingest vs native channel.
    channel_segment = _CHANNEL_URL_BY_PROVIDER.get(source.provider)
    if channel_segment is not None:
        presented["channel_url"] = f"/v1/channels/{channel_segment}/{source.route_token}"
        presented["case_strategy"] = source.config.get("case_strategy", "per_message")
    else:
        presented["ingest_url"] = f"/v1/ingest/{source.route_token}"
    return presented


async def create_source(
    request: CreateSourceRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    route_token = generate_url_safe_token(SECRET_PREFIX_ROUTE_TOKEN)
    is_channel = request.provider in _CHANNEL_URL_BY_PROVIDER

    _validate_channel_config(request.provider, request.config)

    revealed: dict = {}
    if is_channel:
        # Native channels authenticate via the provider's own signature (verified
        # by the channel adapter), not the Svix-style auth_mode. The signing key
        # (Mailgun) / app_secret + access token (WhatsApp) live in config/secret
        # and are provisioned by the integrator, not minted here.
        secret = None
    elif request.auth_mode == SourceAuthMode.API_KEY:
        # api_key: mint a dxk_ key, store only its hash.
        api_key = generate_url_safe_token(SECRET_PREFIX_API_KEY)
        secret = hash_token(api_key)
        revealed["api_key"] = api_key
    else:
        secret = generate_base64_secret(SECRET_PREFIX_HMAC)
        revealed["signing_secret"] = secret

    source = await SQLWorkflowSourceRepository(session).create(
        WorkflowSource(
            uuid=uuid4(),
            tenant_id=tenant.uuid,
            workflow_id=request.workflow_id,
            provider=request.provider,
            account_id=request.account_id,
            route_token=route_token,
            auth_mode=request.auth_mode,
            secret=secret,
            config=request.config,
        )
    )
    # Credentials revealed exactly once.
    return ApiJSONResponse(content={**_present(source), **revealed}, status_code=status.HTTP_201_CREATED)


async def list_sources(
    workflow_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    sources = await SQLWorkflowSourceRepository(session).list_by_workflow(workflow_id, tenant.uuid)
    return ApiJSONResponse(content=[_present(s) for s in sources], status_code=status.HTTP_200_OK)


class UpdateSourceRequest(BaseModel):
    # Only the mutable surface: enable/disable and rotate the auth mode. The
    # route_token / ingest URL are immutable; changing auth_mode re-mints the
    # credential (revealed once), the same way create does.
    enabled: bool | None = None
    auth_mode: SourceAuthMode | None = None


async def update_source(
    source_id: UUID,
    request: UpdateSourceRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    repo = SQLWorkflowSourceRepository(session)
    source = await repo.find_by_id(source_id, tenant.uuid)
    if source is None:
        raise SourceNotFoundError(str(source_id))

    if request.enabled is not None:
        source.enabled = request.enabled

    # Changing the auth mode re-mints the credential (revealed once); the route
    # token / ingest URL stay fixed. Native channels authenticate via provider
    # signatures, so auth_mode does not apply to them.
    revealed: dict = {}
    is_channel = source.provider in _CHANNEL_URL_BY_PROVIDER
    if request.auth_mode is not None and not is_channel and request.auth_mode != source.auth_mode:
        source.auth_mode = request.auth_mode
        if request.auth_mode == SourceAuthMode.API_KEY:
            api_key = generate_url_safe_token(SECRET_PREFIX_API_KEY)
            source.secret = hash_token(api_key)
            revealed["api_key"] = api_key
        else:
            signing_secret = generate_base64_secret(SECRET_PREFIX_HMAC)
            source.secret = signing_secret
            revealed["signing_secret"] = signing_secret

    updated = await repo.update(source)
    return ApiJSONResponse(content={**_present(updated), **revealed}, status_code=status.HTTP_200_OK)


async def delete_source(
    source_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    repo = SQLWorkflowSourceRepository(session)
    source = await repo.find_by_id(source_id, tenant.uuid)
    if source is None:
        raise SourceNotFoundError(str(source_id))
    await repo.delete(source_id, tenant.uuid)
    return ApiJSONResponse(content={"deleted": True}, status_code=status.HTTP_200_OK)


async def list_source_events(
    source_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """Inbound ingest events for a Source — the files it received and their
    processing outcome (the "response"). Backed by the WorkflowProcessingJob
    rows the public ingest endpoint opens per upload, newest first.
    """
    source = await SQLWorkflowSourceRepository(session).find_by_id(source_id, tenant.uuid)
    if source is None:
        raise SourceNotFoundError(str(source_id))

    jobs = await SQLWorkflowProcessingJobRepository(session).list_by_source_token(
        source.route_token, tenant.uuid, limit=200
    )
    events = [
        {
            "uuid": str(job.uuid),
            "file_name": job.file_name,
            "status": job.status.value,
            "case_id": str(job.workflow_case_id) if job.workflow_case_id else None,
            "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]
    return ApiJSONResponse(content=events, status_code=status.HTTP_200_OK)
