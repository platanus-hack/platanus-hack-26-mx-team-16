"""Router for the Connections module (org-level connection accounts)."""

from fastapi import APIRouter

from src.connections.presentation.endpoints.channels import (
    receive_channel_message,
    verify_whatsapp_challenge,
)
from src.connections.presentation.endpoints.connection_account import (
    create_connection_account,
    delete_connection_account,
    get_connection_account,
    list_connection_accounts,
    update_connection_account,
)
from src.connections.presentation.endpoints.ingest import ingest_via_source
from src.connections.presentation.endpoints.workflow_source import (
    create_source,
    delete_source,
    list_source_events,
    list_sources,
    update_source,
)

connections_router = APIRouter(prefix="/connections", tags=["Connections"])

# ── Sources (F8) ──────────────────────────────────────────────────────────
connections_router.add_api_route("/sources", create_source, methods=["POST"], summary="Create an ingest source (F8)")
connections_router.add_api_route(
    "/sources", list_sources, methods=["GET"], summary="List ingest sources for a workflow (F8)"
)
connections_router.add_api_route(
    "/sources/{source_id}", update_source, methods=["PATCH"], summary="Update an ingest source (F8)"
)
connections_router.add_api_route(
    "/sources/{source_id}", delete_source, methods=["DELETE"], summary="Delete an ingest source (F8)"
)
connections_router.add_api_route(
    "/sources/{source_id}/events",
    list_source_events,
    methods=["GET"],
    summary="List inbound ingest events for a source (F8)",
)

# ── Public ingest endpoint (F8 · W2) — token/source-authed, no JWT ─────────
ingest_router = APIRouter(prefix="/ingest", tags=["Ingest"])
ingest_router.add_api_route(
    "/{token}",
    ingest_via_source,
    methods=["POST"],
    summary="Ingest a file through a configured Source (F8 · W2)",
)

# ── Public native-channel webhooks (E6 · W5) — provider-signature authed ────
channels_router = APIRouter(prefix="/channels", tags=["Channels"])
channels_router.add_api_route(
    "/whatsapp/{route_token}",
    verify_whatsapp_challenge,
    methods=["GET"],
    summary="WhatsApp Cloud (Meta) verification handshake (E6 · W5)",
)
channels_router.add_api_route(
    "/{provider}/{route_token}",
    receive_channel_message,
    methods=["POST"],
    summary="Receive an inbound native-channel message (E6 · W5)",
)

connections_router.add_api_route("", list_connection_accounts, methods=["GET"], summary="List connection accounts")
connections_router.add_api_route("", create_connection_account, methods=["POST"], summary="Create connection account")
connections_router.add_api_route(
    "/{account_id}", get_connection_account, methods=["GET"], summary="Get connection account"
)
connections_router.add_api_route(
    "/{account_id}", update_connection_account, methods=["PUT"], summary="Update connection account"
)
connections_router.add_api_route(
    "/{account_id}",
    delete_connection_account,
    methods=["DELETE"],
    summary="Delete connection account",
)
