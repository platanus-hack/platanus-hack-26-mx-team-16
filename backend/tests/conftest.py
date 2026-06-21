import tempfile
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.common.application.helpers.datetimes import utc_now
from src.common.domain.enums.common import Environment
from src.common.domain.enums.tenants import TenantStatus
from src.common.domain.models.tenants.tenant import Tenant
from src.common.settings import settings

TEST_DB_NAME = "doxiq_test"

# Override settings BEFORE any DatabaseConfig is built so no test ever touches
# the dev database. `get_database_config()` reads `settings.async_database_url`
# lazily, so mutating the singleton here is sufficient.
settings.POSTGRES_DB = TEST_DB_NAME
settings.ENVIRONMENT = Environment.testing

# Scan evidence must never touch the real `/data/scans` volume during tests: in
# CI pytest runs OUTSIDE the Docker container, where `/data` doesn't exist and
# isn't writable (the worker-flow tests fail with PermissionError on mkdir).
# `src.scanning.evidence` captures `settings.SCAN_DATA_DIR` into its module-level
# `DATA_DIR` at import time, so this override must happen here — before that
# module is first imported by any test — to redirect writes to a throwaway dir.
settings.SCAN_DATA_DIR = tempfile.mkdtemp(prefix="owliver-test-scans-")

from src.common.database.config import get_database_config  # noqa: E402
from src.common.database.mixins.common import Base  # noqa: E402
import src.common.database.models  # noqa: E402,F401  registers all ORM models on Base.metadata


def _admin_database_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )


async def _ensure_test_database_exists() -> None:
    engine = create_async_engine(_admin_database_url(), isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        await engine.dispose()


async def _drop_test_database() -> None:
    engine = create_async_engine(_admin_database_url(), isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    assert settings.POSTGRES_DB == TEST_DB_NAME, (
        f"Refusing to run: POSTGRES_DB is {settings.POSTGRES_DB!r}, expected {TEST_DB_NAME!r}."
    )

    await _ensure_test_database_exists()

    db_config = get_database_config()
    async with db_config.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        await db_config.dispose()
        await _drop_test_database()


@pytest.fixture(scope="function")
async def async_session() -> AsyncSession:
    async with get_database_config().session_maker() as session:
        yield session


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def tenant(tenant_id: UUID) -> Tenant:
    return Tenant(
        uuid=tenant_id,
        owner_id=uuid4(),
        name="Test Company",
        slug="test-company",
        status=TenantStatus.ACTIVE,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
