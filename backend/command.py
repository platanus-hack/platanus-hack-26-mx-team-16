import asyncio
import json
import pathlib
import uuid
from typing import Any

import typer
import yaml
from sqlalchemy import select

from src.common.database import models
from src.common.database.config import get_database_config

app = typer.Typer(add_completion=False)
database_config = get_database_config()


def _read_fixture(path: pathlib.Path) -> list[dict[str, Any]]:
    if path.suffix in {".yml", ".yaml"}:
        return yaml.safe_load(path.read_text())
    return json.loads(path.read_text())


async def _save(objects: list[object]):
    async with database_config.get_session() as session:  # type: AsyncSession
        session.add_all(objects)
        await session.commit()


@app.command()
def load(fixtures_dir: str = "fixtures"):
    """
    Carga todos los archivos JSON/YAML bajo *fixtures_dir* (similar a
    `python manage.py loaddata` de Django).
    """

    async def _inner():
        objs: list[object] = []
        email_to_user_id: dict[str, uuid.UUID] = {}

        fixture_files = [
            f
            for f in sorted(pathlib.Path(fixtures_dir).glob("*.*"))
            if f.suffix in {".json", ".yml", ".yaml"}
        ]
        for file in fixture_files:
            for entry in _read_fixture(file):
                model_name = entry["model"]
                fields = entry.get("fields", {})
                pk_raw = entry.get("pk")

                if model_name == "User":
                    user_id = uuid.UUID(pk_raw) if pk_raw else uuid.uuid4()
                    user = models.UserORM(uuid=user_id, **fields)
                    objs.append(user)

                # Pre-baked leaderboard fixtures (08-ranking-watchlists §2.4):
                # Site / Scan / Finding rows with grades already computed, so the
                # public board is never empty at demo time. Real gov scans only
                # overwrite these rows if they finish in time.
                elif model_name == "Site":
                    site_id = uuid.UUID(pk_raw) if pk_raw else uuid.uuid4()
                    objs.append(models.SiteORM(uuid=site_id, **fields))

                elif model_name == "Scan":
                    scan_id = uuid.UUID(pk_raw) if pk_raw else uuid.uuid4()
                    objs.append(models.ScanORM(uuid=scan_id, **fields))

                elif model_name == "Finding":
                    finding_id = uuid.UUID(pk_raw) if pk_raw else uuid.uuid4()
                    objs.append(models.FindingORM(uuid=finding_id, **fields))

                else:
                    typer.echo(f"⚠️  Modelo desconocido: {model_name}", err=True)

        await _save(objs)
        typer.echo(f"✅  Se cargaron {len(objs)} objetos")

    asyncio.run(_inner())


@app.command()
def flush_and_load(fixtures_dir: str = "fixtures"):
    async def _inner():
        from src.common.database.mixins.common import Base

        async with database_config.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # reutilizamos la función *load* sin repetir código
        await load.callback(fixtures_dir)

    asyncio.run(_inner())


def _dump_users(users):
    """Serializa usuarios a la estructura de fixture."""
    return [
        {
            "model": "User",
            "pk": str(u.id),
            "fields": {
                "email": u.email,
            },
        }
        for u in users
    ]


@app.command()
def dump(
    output: str = typer.Option(
        "fixtures/data.json",
        help="Ruta del archivo de salida (se creará si no existe).",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Formato de salida: json o yaml",
        case_sensitive=False,
    ),
):
    """
    Genera un archivo de fixtures tomando los datos reales de la base.
    Equivalente a `python manage.py dumpdata` en Django.
    """

    async def _inner():
        # ----- 1. Consultar la base de forma asíncrona -----
        async with database_config.get_session() as session:  # type: AsyncSession
            users = (
                await session.scalars(select(models.UserORM))  # todos los usuarios
            ).all()

        # ----- 2. Serializar a la estructura de fixture -----
        email_lookup = {u.id: u.email for u in users}

        objects = _dump_users(users)

        # ----- 3. Escribir a disco en JSON o YAML -----
        path = pathlib.Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)

        if fmt.lower() == "yaml":
            path.write_text(yaml.safe_dump(objects, allow_unicode=True, sort_keys=False))
        else:  # JSON por defecto
            path.write_text(json.dumps(objects, ensure_ascii=False, indent=2))

        typer.echo(f"✅  Exportados {len(objects)} registros a {path}")

    asyncio.run(_inner())


@app.command()
def seed_gov(seed_path: str = "fixtures/gob_mx.txt"):
    """Insert the .gob.mx seed domains as sites(is_gov=true) and enqueue a
    basic/passive scan for each (08-ranking-watchlists §2.3). Idempotent: re-runs
    reuse existing sites and live scans. Requires Redis (SAQ) to be reachable for
    the enqueued ``RunScanCommand`` dispatch."""

    async def _inner():
        from redis.asyncio import Redis

        from src.common.infrastructure.bus_builder import build_async_bus
        from src.common.infrastructure.domain_builder import build_async_domain
        from src.sites.application.commands.seed_gov import (
            SeedGovHandler,
            read_gov_seed,
        )
        from src.common.settings import settings

        try:
            from saq import Queue

            task_queue = Queue.from_url(settings.redis_url)
        except Exception:  # pragma: no cover - redis optional in some envs
            task_queue = None

        hosts = read_gov_seed(seed_path)
        typer.echo(f"Seeding {len(hosts)} .gob.mx domains from {seed_path}")
        async with database_config.get_session() as session:
            domain = build_async_domain(session=session)
            bus = build_async_bus(
                session=session, domain=domain, task_queue=task_queue
            )
            redis = Redis.from_url(settings.redis_url) if task_queue else None
            await SeedGovHandler(
                site_repository=domain.site_repository,
                scan_repository=domain.scan_repository,
                command_bus=bus.command_bus,
            ).execute(type("Cmd", (), {"seed_path": seed_path})())
            if redis is not None:
                await redis.aclose()
        typer.echo("✅  Gov seed completado")

    asyncio.run(_inner())


if __name__ == "__main__":
    app()
