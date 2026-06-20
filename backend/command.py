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

        for file in sorted(pathlib.Path(fixtures_dir).glob("*.*")):
            for entry in _read_fixture(file):
                model_name = entry["model"]
                fields = entry.get("fields", {})
                pk_raw = entry.get("pk")

                if model_name == "User":
                    user_id = uuid.UUID(pk_raw) if pk_raw else uuid.uuid4()
                    user = models.UserORM(uuid=user_id, **fields)
                    objs.append(user)

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


if __name__ == "__main__":
    app()
