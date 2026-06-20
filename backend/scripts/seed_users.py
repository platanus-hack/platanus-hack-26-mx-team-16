"""Seed dev tenants, users and tenant-user memberships.

Scope is limited to three concerns: ``tenants``, ``users`` and the
``tenant_users`` memberships that join them. Each user is created with a login
email (its identity — ``UserORM.email_address_id`` is required to authenticate)
and a shared dev password so you can log in immediately; each tenant gets one
owner plus a couple of members. Idempotent: existing tenant slugs / user emails
are reused on re-run.

The canonical dev login is ``team@owliver.com`` / ``owliver-dev``.

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

# Cada tenant trae un owner y N miembros (filas en ``tenant_users``).
# country_code / currency_code / time_zone son campos de ``TenantORM``; aquí
# solo fijan datos de dev coherentes.
TENANTS: list[dict] = [
    {
        "name": "Owliver Dev", "slug": "owliver-dev",
        "country_code": "MX", "currency_code": "MXN", "time_zone": "America/Mexico_City",
        "owner": {"email": "team@owliver.com", "username": "team",
                  "first_name": "Team", "last_name": "Owliver"},
        "members": [
            {"email": "ana@owliver.com", "username": "ana", "first_name": "Ana", "last_name": "Pentester"},
            {"email": "luis@owliver.com", "username": "luis", "first_name": "Luis", "last_name": "Analyst"},
        ],
    }
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
