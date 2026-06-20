"""SQLClassifierRepository — registry de clasificadores tenant-scoped (F3 · D-C)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import be_none, equal, expect, have_length

from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM
from src.common.domain.enums.pipelines import ClassifierKind
from src.workflows.domain.models.classifier import Classifier
from src.workflows.infrastructure.repositories.sql_classifier import SQLClassifierRepository


@pytest.fixture
async def user_orm(async_session):
    user = UserORM(uuid=uuid4(), username=f"testuser-{uuid4().hex[:8]}", password="hashed")
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def tenant_orm(async_session, user_orm):
    tenant = TenantORM(
        uuid=uuid4(),
        owner_id=user_orm.uuid,
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        status="ACTIVE",
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest.fixture
def repo(async_session):
    return SQLClassifierRepository(session=async_session)


def _classifier(tenant_id, slug: str, kind: ClassifierKind, config: dict) -> Classifier:
    return Classifier(uuid=uuid4(), tenant_id=tenant_id, slug=slug, kind=kind, config=config)


async def test_upsert__creates_then_finds_by_slug(repo, tenant_orm):
    await repo.upsert(_classifier(tenant_orm.uuid, "custom-clf", ClassifierKind.LAMBDA, {"function": "fn"}))

    found = await repo.find_by_slug("custom-clf", tenant_orm.uuid)

    expect(found).not_to(be_none)
    expect(found.kind).to(equal(ClassifierKind.LAMBDA))
    expect(found.config["function"]).to(equal("fn"))


async def test_upsert__updates_existing_slug_in_place(repo, tenant_orm):
    await repo.upsert(_classifier(tenant_orm.uuid, "clf", ClassifierKind.LAMBDA, {"function": "a"}))
    await repo.upsert(_classifier(tenant_orm.uuid, "clf", ClassifierKind.PROMPT, {"provider": "p"}))

    found = await repo.find_by_slug("clf", tenant_orm.uuid)
    all_rows = await repo.list_by_tenant(tenant_orm.uuid)

    expect(found.kind).to(equal(ClassifierKind.PROMPT))
    expect(all_rows).to(have_length(1))


async def test_find_by_slug__missing_returns_none(repo, tenant_orm):
    expect(await repo.find_by_slug("ghost", tenant_orm.uuid)).to(be_none)


async def test_delete__removes_entry(repo, tenant_orm):
    await repo.upsert(_classifier(tenant_orm.uuid, "del", ClassifierKind.LAMBDA, {}))

    await repo.delete("del", tenant_orm.uuid)

    expect(await repo.find_by_slug("del", tenant_orm.uuid)).to(be_none)
