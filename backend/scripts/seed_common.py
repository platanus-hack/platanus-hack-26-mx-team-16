"""Initial setup & shared config: the global industry catalog.

This is the first seed to run on a fresh database. It loads platform-level
reference data that is NOT tenant-specific (today: industries). Tenants and
users live in ``seed_users.py``; workflows in ``seed_workflows.py``.

Usage:
    docker compose run --rm api python scripts/seed_common.py
    python scripts/seed_common.py            # against a locally-reachable DB
"""

import asyncio

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.config import DatabaseConfig
from src.common.database.models.processing.industry import IndustryORM
from src.common.settings import settings

app = typer.Typer(add_completion=False, help="Seed global config (industries).")

# Catálogo de industrias del producto. Idempotente por ``slug``: re-correr
# actualiza nombre/icono/descripción sin duplicar filas.
INDUSTRIES: list[dict] = [
    {"slug": "banking", "name": "Banca", "icon": "landmark",
     "description": "Automatiza procesos bancarios y de riesgo."},
    {"slug": "insurance", "name": "Seguros", "icon": "shield",
     "description": "Valida pólizas y recetas, automatiza autorizaciones."},
    {"slug": "real-estate", "name": "Inmobiliario", "icon": "building-2",
     "description": "Analiza expedientes inmobiliarios y riesgos."},
    {"slug": "transport-logistics", "name": "Transporte y Logística", "icon": "package",
     "description": "Bills of lading, cartas porte y documentación de embarque."},
    {"slug": "healthcare", "name": "Salud", "icon": "stethoscope",
     "description": "Procesa recetas, estudios y autorizaciones médicas."},
    {"slug": "general", "name": "General", "icon": "layers",
     "description": "Extracción y análisis documental de propósito general."},
]


async def _seed(session: AsyncSession) -> int:
    created = 0
    for ind in INDUSTRIES:
        result = await session.execute(select(IndustryORM).where(IndustryORM.slug == ind["slug"]))
        found = result.scalar_one_or_none()
        if found:
            found.name = ind["name"]
            found.icon = ind.get("icon")
            found.description = ind.get("description")
            typer.echo(f"  = Industry exists, updated: {ind['slug']}")
            continue

        session.add(IndustryORM(slug=ind["slug"], name=ind["name"], icon=ind.get("icon"),
                                description=ind.get("description")))
        created += 1
        typer.secho(f"  + Industry: {ind['name']} ({ind['slug']})", fg=typer.colors.GREEN)

    await session.commit()
    return created


@app.command()
def seed() -> None:
    """Load the industry catalog (idempotent)."""

    async def _run() -> None:
        db_config = DatabaseConfig(str(settings.async_database_url))
        try:
            async with db_config.session_maker() as session:
                created = await _seed(session)
            typer.secho(f"\nDone! {created} industries created, {len(INDUSTRIES) - created} already present.",
                        fg=typer.colors.GREEN, bold=True)
        finally:
            await db_config.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
