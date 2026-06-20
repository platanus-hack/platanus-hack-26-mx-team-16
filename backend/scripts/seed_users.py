"""Seed tenants, email addresses, users and tenant-user memberships.

Run after ``seed_common.py``. Creates a handful of tenants, each with one
owner and a couple of members, all sharing a known dev password so you can
log in immediately. Idempotent: existing emails / tenant slugs are reused.

The canonical dev login ``team@llamitai.com`` / ``llamitai-dev`` is preserved
so existing E2E flows keep working.

Usage:
    docker compose run --rm api python scripts/seed_users.py
    docker compose run --rm api python scripts/seed_users.py --password secret123
"""

import asyncio
from typing import Annotated
from uuid import uuid4

import bcrypt
import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.config import DatabaseConfig
from src.common.database.models.email_address import EmailAddressORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.tenants.tenant_user import TenantUserORM
from src.common.database.models.user import UserORM
from src.common.settings import settings

app = typer.Typer(add_completion=False, help="Seed tenants and users.")

DEFAULT_PASSWORD = "12345678x"

# Cada tenant trae un owner y N miembros. ``industry`` es informativo (los
# workflows se cuelgan de la industria en seed_workflows.py). País/moneda
# controlan los checksums multi-país de las reglas.
TENANTS: list[dict] = [
    {
        "name": "LlamitAI Dev", "slug": "llamitai-dev",
        "country_code": "MX", "currency_code": "MXN", "time_zone": "America/Mexico_City",
        "owner": {"email": "team@llamitai.com", "username": "team",
                  "first_name": "Team", "last_name": "Llamitai"},
        "members": [
            {"email": "ana@llamitai.com", "username": "ana", "first_name": "Ana", "last_name": "Reviewer"},
            {"email": "luis@llamitai.com", "username": "luis", "first_name": "Luis", "last_name": "Analyst"},
        ],
    },
    {
        "name": "Aseguradora del Norte", "slug": "aseguradora-norte",
        "country_code": "MX", "currency_code": "MXN", "time_zone": "America/Mexico_City",
        "owner": {"email": "ana@aseguradoranorte.mx", "username": "ana.norte",
                  "first_name": "Ana", "last_name": "Gómez"},
        "members": [
            {"email": "juan@aseguradoranorte.mx", "username": "juan.norte",
             "first_name": "Juan", "last_name": "Pérez"},
        ],
    },
    {
        "name": "Banco Crédito", "slug": "banco-credito",
        "country_code": "CO", "currency_code": "COP", "time_zone": "America/Bogota",
        "owner": {"email": "carlos@bancocredito.co", "username": "carlos.bc",
                  "first_name": "Carlos", "last_name": "Rojas"},
        "members": [
            {"email": "maria@bancocredito.co", "username": "maria.bc",
             "first_name": "María", "last_name": "Díaz"},
        ],
    },
]


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def _get_or_create_tenant(session: AsyncSession, spec: dict) -> TenantORM:
    result = await session.execute(select(TenantORM).where(TenantORM.slug == spec["slug"]))
    tenant = result.scalar_one_or_none()
    if tenant:
        typer.echo(f"  = Tenant exists: {spec['slug']}")
        return tenant

    tenant = TenantORM(
        uuid=uuid4(), name=spec["name"], slug=spec["slug"], status="ACTIVE",
        time_zone=spec["time_zone"], country_code=spec["country_code"],
        currency_code=spec["currency_code"],
    )
    session.add(tenant)
    await session.flush()
    typer.secho(f"  + Tenant: {spec['name']} ({spec['slug']})", fg=typer.colors.GREEN)
    return tenant


async def _get_or_create_user(session: AsyncSession, person: dict, password: str) -> UserORM:
    result = await session.execute(
        select(UserORM).join(EmailAddressORM, UserORM.email_address_id == EmailAddressORM.uuid)
        .where(EmailAddressORM.email == person["email"])
    )
    user = result.scalar_one_or_none()
    if user:
        typer.echo(f"    = User exists: {person['email']}")
        return user

    email_orm = EmailAddressORM(uuid=uuid4(), email=person["email"], is_verified=True)
    session.add(email_orm)
    await session.flush()

    user = UserORM(
        uuid=uuid4(), username=person["username"], email_address_id=email_orm.uuid,
        first_name=person["first_name"], last_name=person["last_name"],
        password=_hash(password), is_active=True,
    )
    session.add(user)
    await session.flush()
    typer.secho(f"    + User: {person['email']}", fg=typer.colors.GREEN)
    return user


async def _link(session: AsyncSession, tenant: TenantORM, user: UserORM, person: dict, *, is_owner: bool) -> None:
    result = await session.execute(
        select(TenantUserORM).where(
            TenantUserORM.tenant_id == tenant.uuid, TenantUserORM.user_id == user.uuid
        )
    )
    if result.scalar_one_or_none():
        return

    session.add(TenantUserORM(
        uuid=uuid4(), tenant_id=tenant.uuid, user_id=user.uuid, is_owner=is_owner,
        status="ACTIVE", first_name=person["first_name"], last_name=person["last_name"],
    ))
    if user.current_tenant_id is None:
        user.current_tenant_id = tenant.uuid
    role = "owner" if is_owner else "member"
    typer.echo(f"    · linked as {role}")


async def _seed(session: AsyncSession, password: str) -> None:
    for spec in TENANTS:
        typer.secho(f"\n{spec['name']}", bold=True)
        tenant = await _get_or_create_tenant(session, spec)

        owner = await _get_or_create_user(session, spec["owner"], password)
        if tenant.owner_id is None:
            tenant.owner_id = owner.uuid
        await _link(session, tenant, owner, spec["owner"], is_owner=True)

        for person in spec.get("members", []):
            member = await _get_or_create_user(session, person, password)
            await _link(session, tenant, member, person, is_owner=False)

        await session.flush()

    await session.commit()


@app.command()
def seed(
    password: Annotated[str, typer.Option("--password", "-p", help="Password for every seeded user.")] = DEFAULT_PASSWORD,
) -> None:
    """Create tenants, users and memberships (idempotent)."""

    async def _run() -> None:
        db_config = DatabaseConfig(str(settings.async_database_url))
        try:
            async with db_config.session_maker() as session:
                await _seed(session, password)
            typer.secho(f"\nDone! All users share password: {password}", fg=typer.colors.GREEN, bold=True)
        finally:
            await db_config.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
