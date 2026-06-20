"""E6 · W5: public channel webhooks — dedup, signature, hub.challenge, per_message.

Real ASGI app (httpx) with live DB sessions; Temporal is a recording stub and S3
is patched to a fake (the channel path uploads bytes-first). Asserts the
delivery-first dedup contract end-to-end: a redelivered message is a 200 no-op
with no new case.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from expects import equal, expect
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from src.common.database.config import get_database_config
from src.common.database.models.pipeline import PipelineORM, PipelineVersionORM
from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.source_delivery import SourceDeliveryORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM
from src.common.database.models.workflow_source import WorkflowSourceORM
from src.common.database.models.workspace import WorkflowORM
from src.common.domain.exceptions._base import DomainError
from src.common.infrastructure.error_handlers import domain_error_handler
from src.connections.presentation.router import channels_router
from src.storage.application.use_cases import upload_file as upload_module


# ── ASGI app + stubs ─────────────────────────────────────────────────────────
class _RecordingTemporal:
    def __init__(self):
        self.started = []

    async def start_workflow(self, *args, **kwargs):
        self.started.append((args, kwargs))


class _FakeS3:
    def put_object(self, **kwargs):
        return None


def _build_app(temporal) -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(channels_router, prefix="/v1")
    app.state.database_config = get_database_config()
    app.state.task_queue = object()
    app.state.temporal_client = temporal
    return app


@pytest.fixture
def temporal():
    return _RecordingTemporal()


@pytest.fixture
async def app(temporal):
    return _build_app(temporal)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture(autouse=True)
def _patch_s3(monkeypatch):
    monkeypatch.setattr(upload_module, "get_s3_client", lambda: _FakeS3())
    monkeypatch.setattr(upload_module.settings, "AWS_STORAGE_BUCKET_NAME", "bucket", raising=False)


# ── committed fixtures (ASGI app uses fresh sessions) ────────────────────────
async def _seed_source(async_session, provider: str, *, config=None, secret=None):
    user = UserORM(uuid=uuid4(), username=f"u-{uuid4().hex[:8]}", password="x")
    async_session.add(user)
    await async_session.flush()
    tenant = TenantORM(
        uuid=uuid4(), owner_id=user.uuid, name="T", slug=f"t-{uuid4().hex[:8]}", status="ACTIVE"
    )
    async_session.add(tenant)
    await async_session.flush()
    workflow = WorkflowORM(uuid=uuid4(), tenant_id=tenant.uuid, name="WF")
    async_session.add(workflow)
    await async_session.flush()
    # An ACTIVE pipeline OWNED by the workflow (ADR 0002 · find_by_workflow) with a
    # published version so ResolveIngestCase/IngestViaSource resolve.
    pipeline = PipelineORM(
        uuid=uuid4(),
        workflow_id=workflow.uuid,
        tenant_id=tenant.uuid,
        slug="standard-extraction",
        name="Std",
        kind="EXTRACTION",
        status="ACTIVE",
        current_version=1,
    )
    async_session.add(pipeline)
    await async_session.flush()
    async_session.add(
        PipelineVersionORM(
            uuid=uuid4(),
            pipeline_id=pipeline.uuid,
            version=1,
            phases=[{"id": "x", "kind": "extract_text", "scope": "document", "config": {}}],
        )
    )
    await async_session.flush()
    # Bind the workflow to its pipeline so the case run can resolve a recipe.
    workflow.pipeline_id = pipeline.uuid
    token = f"src_{uuid4().hex[:12]}"
    source = WorkflowSourceORM(
        uuid=uuid4(),
        tenant_id=tenant.uuid,
        workflow_id=workflow.uuid,
        provider=provider,
        route_token=token,
        secret=secret,
        config=config or {},
    )
    async_session.add(source)
    await async_session.commit()
    return source


def _wa_payload(wamid: str, phone_number_id: str = "PN1") -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": phone_number_id},
                            "messages": [
                                {"id": wamid, "type": "text", "from": "5215550001",
                                 "text": {"body": "Quiero 2 cajas"}}
                            ],
                        }
                    }
                ]
            }
        ]
    }


# ── hub.challenge (GET) ──────────────────────────────────────────────────────
async def test_hub_challenge__echoes_on_matching_verify_token(client, async_session):
    source = await _seed_source(
        async_session, "WHATSAPP", config={"verify_token": "vt", "app_secret": "s"}
    )

    response = await client.get(
        f"/v1/channels/whatsapp/{source.route_token}",
        params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "999"},
    )

    expect(response.status_code).to(equal(200))
    expect(response.text).to(equal("999"))


async def test_hub_challenge__wrong_verify_token_is_401(client, async_session):
    source = await _seed_source(
        async_session, "WHATSAPP", config={"verify_token": "vt", "app_secret": "s"}
    )

    response = await client.get(
        f"/v1/channels/whatsapp/{source.route_token}",
        params={"hub.mode": "subscribe", "hub.verify_token": "WRONG", "hub.challenge": "999"},
    )

    expect(response.status_code).to(equal(401))


# ── signature verification (POST) ────────────────────────────────────────────
async def test_whatsapp_post__invalid_signature_is_401_with_no_delivery(
    client, async_session
):
    source = await _seed_source(
        async_session, "WHATSAPP",
        config={"verify_token": "vt", "app_secret": "app-secret", "phone_number_id": "PN1"},
        secret="access-token",
    )
    body = json.dumps(_wa_payload("wamid.X")).encode()

    response = await client.post(
        f"/v1/channels/whatsapp/{source.route_token}",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": "sha256=bad"},
    )

    expect(response.status_code).to(equal(401))
    count = (
        await async_session.execute(
            select(func.count()).select_from(SourceDeliveryORM).where(
                SourceDeliveryORM.source_id == source.uuid
            )
        )
    ).scalar_one()
    expect(count).to(equal(0))


async def test_whatsapp_post__valid_signature_creates_case_and_delivery(
    client, async_session
):
    source = await _seed_source(
        async_session, "WHATSAPP",
        config={"verify_token": "vt", "app_secret": "app-secret", "phone_number_id": "PN1",
                "case_strategy": "per_message"},
        secret="access-token",
    )
    body = json.dumps(_wa_payload("wamid.OK")).encode()
    sig = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()

    response = await client.post(
        f"/v1/channels/whatsapp/{source.route_token}",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": sig},
    )

    expect(response.status_code).to(equal(200))
    expect(response.json()["data"]["processed"]).to(equal(1))
    deliveries = (
        await async_session.execute(
            select(func.count()).select_from(SourceDeliveryORM).where(
                SourceDeliveryORM.source_id == source.uuid
            )
        )
    ).scalar_one()
    expect(deliveries).to(equal(1))
    # per_message: external_ref == wamid → exactly one case.
    cases = (
        await async_session.execute(
            select(func.count()).select_from(WorkflowCaseORM).where(
                WorkflowCaseORM.workflow_id == source.workflow_id
            )
        )
    ).scalar_one()
    expect(cases).to(equal(1))


# ── dedup: redelivery is a 200 no-op (no new case) ──────────────────────────
async def test_post__redelivery_same_message_id_is_idempotent_no_new_case(
    client, async_session
):
    source = await _seed_source(
        async_session, "WHATSAPP",
        config={"app_secret": "app-secret", "phone_number_id": "PN1",
                "case_strategy": "per_message"},
        secret="access-token",
    )
    body = json.dumps(_wa_payload("wamid.DUP")).encode()
    sig = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    headers = {"content-type": "application/json", "X-Hub-Signature-256": sig}

    first = await client.post(f"/v1/channels/whatsapp/{source.route_token}", content=body, headers=headers)
    second = await client.post(f"/v1/channels/whatsapp/{source.route_token}", content=body, headers=headers)

    expect(first.status_code).to(equal(200))
    expect(first.json()["data"]["processed"]).to(equal(1))
    expect(second.status_code).to(equal(200))
    # Second is a pure duplicate — no new processing.
    expect(second.json()["data"]["duplicates"]).to(equal(1))
    expect(second.json()["data"]["processed"]).to(equal(0))

    deliveries = (
        await async_session.execute(
            select(func.count()).select_from(SourceDeliveryORM).where(
                SourceDeliveryORM.source_id == source.uuid
            )
        )
    ).scalar_one()
    expect(deliveries).to(equal(1))
    cases = (
        await async_session.execute(
            select(func.count()).select_from(WorkflowCaseORM).where(
                WorkflowCaseORM.workflow_id == source.workflow_id
            )
        )
    ).scalar_one()
    expect(cases).to(equal(1))


# ── provider mismatch ────────────────────────────────────────────────────────
async def test_post__provider_url_must_match_source_provider(client, async_session):
    source = await _seed_source(async_session, "WHATSAPP", config={"app_secret": "s"})

    response = await client.post(
        f"/v1/channels/email/{source.route_token}",
        content=b"{}",
        headers={"content-type": "application/json"},
    )

    expect(response.status_code).to(equal(404))
    expect(response.json()["errors"][0]["code"]).to(equal("channel.ProviderMismatch"))
