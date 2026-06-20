"""F8 · source CRUD: update (enable/disable, rotate auth_mode) + delete.

Gotcha vigente: update() persiste la entidad COMPLETA (enabled, auth_mode,
secret). El route_token / ingest URL son inmutables.
"""

from uuid import uuid4

import pytest
from expects import be_false, be_none, equal, expect

from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.enums.sources import SourceAuthMode
from src.connections.domain.exceptions import SourceNotFoundError
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.infrastructure.repositories.sql_workflow_source import (
    SQLWorkflowSourceRepository,
)


@pytest.fixture
def source_repo(async_session):
    return SQLWorkflowSourceRepository(session=async_session)


def _webhook_source(
    tenant_orm,
    workflow_orm,
    *,
    auth_mode: SourceAuthMode = SourceAuthMode.API_KEY,
    enabled: bool = True,
) -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        provider=ConnectionProvider.WEBHOOK,
        route_token=f"src_{uuid4().hex[:12]}",
        auth_mode=auth_mode,
        secret="dxk_original",  # noqa: S106 — fake test secret
        enabled=enabled,
    )


async def test_update__toggles_enabled(source_repo, tenant_orm, workflow_orm):
    created = await source_repo.create(_webhook_source(tenant_orm, workflow_orm))

    created.enabled = False
    updated = await source_repo.update(created)

    expect(updated.enabled).to(be_false)
    found = await source_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found.enabled).to(be_false)


async def test_update__rotates_auth_mode_and_secret(source_repo, tenant_orm, workflow_orm):
    created = await source_repo.create(_webhook_source(tenant_orm, workflow_orm))

    created.auth_mode = SourceAuthMode.HMAC
    created.secret = "whsec_rotated"
    updated = await source_repo.update(created)

    expect(updated.auth_mode).to(equal(SourceAuthMode.HMAC))
    expect(updated.secret).to(equal("whsec_rotated"))
    found = await source_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found.auth_mode).to(equal(SourceAuthMode.HMAC))
    expect(found.secret).to(equal("whsec_rotated"))


async def test_update__missing_raises_not_found(source_repo, tenant_orm, workflow_orm):
    phantom = _webhook_source(tenant_orm, workflow_orm)

    with pytest.raises(SourceNotFoundError):
        await source_repo.update(phantom)


async def test_delete__removes_source(source_repo, tenant_orm, workflow_orm):
    created = await source_repo.create(_webhook_source(tenant_orm, workflow_orm))

    await source_repo.delete(created.uuid, tenant_orm.uuid)

    found = await source_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found).to(be_none)


async def test_delete__missing_is_noop(source_repo, tenant_orm):
    # Deleting a non-existent source must not raise.
    await source_repo.delete(uuid4(), tenant_orm.uuid)


async def test_delete__is_tenant_scoped(source_repo, tenant_orm, workflow_orm):
    created = await source_repo.create(_webhook_source(tenant_orm, workflow_orm))

    # A different tenant cannot delete this source.
    await source_repo.delete(created.uuid, uuid4())

    found = await source_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found).not_to(be_none)
