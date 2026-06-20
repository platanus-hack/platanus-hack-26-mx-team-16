from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import scoped_session

from src.common.database.mixins.common import Base
from src.common.settings import settings


@dataclass
class DatabaseConfig:
    database_url: str
    engine: AsyncEngine | None = None
    session_maker: async_sessionmaker | None = None

    def __post_init__(self):
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=20,  # Increased from 5 to 20
            max_overflow=30,  # Increased from 10 to 30 (total: 50 connections)
            pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
            pool_timeout=60,  # Increased timeout from default 30 to 60 seconds
            echo_pool=False,  # Set to True to debug connection pool issues
        )
        self.session_maker = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    async def create_tables_async(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        async with self.session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    async def dispose(self):
        if not self.engine:
            return
        await self.engine.dispose()


def get_database_config() -> DatabaseConfig:
    return DatabaseConfig(database_url=str(settings.async_database_url))


def get_scoped_session():
    return scoped_session(get_database_config().session_maker)
