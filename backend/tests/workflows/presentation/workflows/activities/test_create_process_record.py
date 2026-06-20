import hashlib
from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from expects import equal, expect, have_key
from sqlalchemy import select

from src.common.database.models.usage.process_record import ProcessRecordORM
from src.common.infrastructure.temporal.activities.create_process_record import (
    CreateProcessRecordActivity,
)

OBJECT_KEY = "uploads/tenants/abc123/files/pruebas.pdf"
EXPECTED_DIGEST = hashlib.sha256(OBJECT_KEY.encode("utf-8")).hexdigest()


@pytest.fixture
def activity(async_session):
    @asynccontextmanager
    async def _same_session():
        yield async_session

    return CreateProcessRecordActivity(session_maker=_same_session)


def _build_input(tenant_orm, workflow_orm=None, page_count: int = 5) -> dict:
    return {
        "tenant_id": str(tenant_orm.uuid),
        "workflow_id": str(workflow_orm.uuid) if workflow_orm else None,
        "object_key": OBJECT_KEY,
        "page_count": page_count,
        "analysis_run_id": None,
    }


async def test_create__records_process_record(activity, async_session, tenant_orm, workflow_orm):
    output = await activity.create_process_record(_build_input(tenant_orm, workflow_orm, page_count=5))

    expect(output).to(have_key("process_record_id"))

    row = await async_session.get(ProcessRecordORM, UUID(output["process_record_id"]))
    expect(row.page_count).to(equal(5))
    expect(row.tenant_id).to(equal(tenant_orm.uuid))
    expect(row.workflow_id).to(equal(workflow_orm.uuid))
    expect(row.object_key_digest).to(equal(EXPECTED_DIGEST))


async def test_create__digest_is_sha256_of_object_key(activity, async_session, tenant_orm):
    output = await activity.create_process_record(_build_input(tenant_orm, page_count=1))

    row = await async_session.get(ProcessRecordORM, UUID(output["process_record_id"]))
    expect(len(row.object_key_digest)).to(equal(64))
    expect(row.object_key_digest).to(equal(EXPECTED_DIGEST))


async def test_create__records_without_workflow_id(activity, async_session, tenant_orm):
    output = await activity.create_process_record(_build_input(tenant_orm, workflow_orm=None, page_count=3))

    expect(output).to(have_key("process_record_id"))
    row = await async_session.get(ProcessRecordORM, UUID(output["process_record_id"]))
    expect(row.workflow_id).to(equal(None))
    expect(row.page_count).to(equal(3))


async def test_create__multiple_calls_create_separate_records(activity, async_session, tenant_orm):
    out_a = await activity.create_process_record(_build_input(tenant_orm, page_count=2))
    out_b = await activity.create_process_record(_build_input(tenant_orm, page_count=4))

    rows = (
        (await async_session.execute(select(ProcessRecordORM).where(ProcessRecordORM.tenant_id == tenant_orm.uuid)))
        .scalars()
        .all()
    )

    expect(len(rows)).to(equal(2))
    expect(out_a["process_record_id"]).not_to(equal(out_b["process_record_id"]))
