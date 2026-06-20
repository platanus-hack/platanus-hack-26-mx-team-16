"""Public native-channel webhooks (E6 · W5 · diseño §5).

``POST /v1/channels/{provider}/{route_token}`` and the WhatsApp
``GET /v1/channels/whatsapp/{route_token}`` handshake. Flat + public like the
API ingest endpoint — the credential is the PROVIDER's own signature (verified
by the channel adapter), not a JWT or the Svix auth_mode.

Flow (POST): resolve Source by token → provider must match ``source.provider`` →
adapter.verify(signature) → adapter.parse → per message: delivery-first dedup +
case by ``case_strategy`` + bytes-first upload + ``IngestViaSource`` dispatch.

WhatsApp specifics: Meta requires a fast 200 and retries otherwise, and media
URLs expire ~5 min. So messages WITH deferred media are processed in a
background task after the 200 ACK; the delivery row is marked FAILED (retriable)
if the download blows up.
"""

from __future__ import annotations

from fastapi import BackgroundTasks, Request, status
from starlette.responses import PlainTextResponse

from src.common.application.logging import get_logger
from src.common.database.config import get_database_config
from src.common.infrastructure.dependencies.common import AsyncSessionDep, TemporalClientDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.connections.application.channels.ingest_channel import IngestChannelMessage
from src.connections.domain.channels.base import ChannelRequest
from src.connections.domain.exceptions import (
    ChannelProviderMismatchError,
    ChannelSignatureInvalidError,
    ChannelUnsupportedProviderError,
    SourceNotFoundError,
)
from src.connections.domain.models.channel_message import ChannelMessage
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.infrastructure.channels.registry import (
    PROVIDER_BY_URL,
    get_channel_adapter,
    resolve_vendor,
)
from src.connections.infrastructure.channels.whatsapp_cloud import WhatsappCloudChannelAdapter
from src.connections.infrastructure.repositories.sql_source_delivery import (
    SQLSourceDeliveryRepository,
)
from src.connections.infrastructure.repositories.sql_workflow_source import (
    SQLWorkflowSourceRepository,
)

logger = get_logger(__name__)


async def _build_request_ctx(request: Request) -> ChannelRequest:
    raw_body = await request.body()
    ctx = ChannelRequest(
        raw_body=raw_body,
        headers={k: v for k, v in request.headers.items()},
        query=dict(request.query_params),
    )
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        form = await request.form()
        for key, value in form.multi_items():
            if hasattr(value, "filename") and value.filename:
                ctx.files[key] = (
                    value.filename,
                    value.content_type or "application/octet-stream",
                    await value.read(),
                )
            else:
                ctx.form[key] = str(value)
    return ctx


async def _resolve_source(provider: str, route_token: str, session) -> WorkflowSource:
    if provider not in PROVIDER_BY_URL:
        raise ChannelUnsupportedProviderError(provider)
    source = await SQLWorkflowSourceRepository(session).find_by_route_token(route_token)
    if source is None or not source.enabled:
        raise SourceNotFoundError(route_token)
    if source.provider != PROVIDER_BY_URL[provider]:
        raise ChannelProviderMismatchError(provider, source.provider.value)
    return source


async def receive_channel_message(
    provider: str,
    route_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
) -> ApiJSONResponse:
    source = await _resolve_source(provider, route_token, session)
    vendor = resolve_vendor(provider, source.config)
    adapter = get_channel_adapter(provider, vendor)
    if adapter is None:
        raise ChannelUnsupportedProviderError(f"{provider}:{vendor}")

    ctx = await _build_request_ctx(request)
    if not adapter.verify(source, ctx):
        raise ChannelSignatureInvalidError()

    messages = adapter.parse(source, ctx)

    processed = 0
    duplicates = 0
    deferred = 0
    for message in messages:
        if _has_deferred_media(message):
            # Meta media expires fast → ACK now, download + ingest after 200.
            deferred += 1
            background_tasks.add_task(
                _process_message_background,
                source.route_token,
                provider,
                vendor,
                message,
                temporal_client,
            )
            continue
        result = await IngestChannelMessage(
            source=source,
            message=message,
            adapter=adapter,
            session=session,
            temporal_client=temporal_client,
            source_delivery_repository=SQLSourceDeliveryRepository(session),
        ).execute()
        if result.duplicate:
            duplicates += 1
        else:
            processed += 1

    return ApiJSONResponse(
        content={"received": len(messages), "processed": processed,
                 "duplicates": duplicates, "deferred": deferred},
        status_code=status.HTTP_200_OK,
    )


def _has_deferred_media(message: ChannelMessage) -> bool:
    return any(att.fetch_ref and att.content is None for att in message.attachments)


async def _process_message_background(
    route_token: str,
    provider: str,
    vendor: str,
    message: ChannelMessage,
    temporal_client: object,
) -> None:
    """Resolve deferred media + ingest, in a fresh session after the 200 ACK.

    Reuses the app's already-connected Temporal client (the request's session is
    closed by the time this runs, so we open a fresh one).
    """
    adapter = get_channel_adapter(provider, vendor)
    if adapter is None:
        return
    session_maker = get_database_config().session_maker
    async with session_maker() as session:
        source = await SQLWorkflowSourceRepository(session).find_by_route_token(route_token)
        if source is None:
            return
        try:
            await IngestChannelMessage(
                source=source,
                message=message,
                adapter=adapter,
                session=session,
                temporal_client=temporal_client,
                source_delivery_repository=SQLSourceDeliveryRepository(session),
            ).execute()
        except Exception:  # noqa: BLE001 — delivery row already marked FAILED
            logger.exception(
                "channel.background_ingest_failed",
                route_token=route_token,
                provider_message_id=message.provider_message_id,
            )


async def verify_whatsapp_challenge(
    route_token: str,
    request: Request,
    session: AsyncSessionDep,
) -> PlainTextResponse:
    """Meta GET handshake — echo ``hub.challenge`` when ``hub.verify_token`` matches."""
    source = await _resolve_source("whatsapp", route_token, session)
    adapter = WhatsappCloudChannelAdapter()
    challenge = adapter.hub_challenge(source, dict(request.query_params))
    if challenge is None:
        raise ChannelSignatureInvalidError()
    return PlainTextResponse(content=challenge, status_code=status.HTTP_200_OK)
