"""Seed test workflows, each with its own pipeline, document types and rules.

Run after ``seed_common.py`` (industries) and ``seed_users.py`` (tenants/users).

Workflows are created through the real ``WorkflowCreator`` use case so each one
is born owning a valid pipeline cloned from a canonical template (ADR 0002) —
exactly like the product's "new workflow" flow. We then attach:
  * document types with a JSON-Schema ``fields`` contract + inline validations
  * workflow rules (kind ``VALIDATION``) — saved as drafts (uncompiled)

Idempotent: a workflow is skipped if one with the same name already exists for
the tenant.

Usage:
    docker compose run --rm api python scripts/seed_workflows.py
    docker compose run --rm api python scripts/seed_workflows.py --tenant-slug llamitai-dev
"""

import asyncio
from typing import Annotated
from uuid import uuid4

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.config import DatabaseConfig
from src.common.database.models.document_type import DocumentTypeORM
from src.common.database.models.processing.industry import IndustryORM
from src.common.database.models.processing.workflow_rule import WorkflowRuleORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.workspace import WorkflowORM
from src.common.settings import settings
from src.workflows.application.workflows.creator import WorkflowCreator
from src.workflows.domain.recipes import (
    ANALYSIS_PIPELINE_SLUG,
    EXTRACT_ASSESS_PIPELINE_SLUG,
    STANDARD_CASE_PIPELINE_SLUG,
    STANDARD_PIPELINE_SLUG,
)
from src.workflows.domain.services.rule_slug import slugify_rule_name
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository

app = typer.Typer(add_completion=False, help="Seed test workflows.")


def _string_field(description: str, fmt: str | None = None) -> dict:
    field: dict = {"type": "string", "description": description}
    if fmt:
        field["format"] = fmt
    return field


# Contratos de extracción (JSON Schema) reutilizados por los specs de abajo.
CEDULA_FIELDS = {
    "type": "object",
    "properties": {
        "nombres": _string_field("Nombres de la persona"),
        "apellidos": _string_field("Apellidos de la persona"),
        "numero_cedula": _string_field("Número de identificación"),
        "fecha_nacimiento": _string_field("Fecha de nacimiento", "date"),
        "sexo": _string_field("Sexo"),
    },
    "required": ["nombres", "apellidos", "numero_cedula"],
}

ESTADO_CUENTA_FIELDS = {
    "type": "object",
    "properties": {
        "titular": _string_field("Nombre del titular de la cuenta"),
        "numero_cuenta": _string_field("Número de cuenta"),
        "periodo": _string_field("Periodo del estado de cuenta"),
        "saldo_final": _string_field("Saldo final del periodo"),
    },
    "required": ["titular", "numero_cuenta", "saldo_final"],
}

POLIZA_FIELDS = {
    "type": "object",
    "properties": {
        "numero_poliza": _string_field("Número de póliza"),
        "asegurado": _string_field("Nombre del asegurado"),
        "vigencia_inicio": _string_field("Inicio de vigencia", "date"),
        "vigencia_fin": _string_field("Fin de vigencia", "date"),
        "prima": _string_field("Monto de la prima"),
    },
    "required": ["numero_poliza", "asegurado", "vigencia_inicio", "vigencia_fin"],
}

COMPROBANTE_FIELDS = {
    "type": "object",
    "properties": {
        "nombre": _string_field("Nombre del titular"),
        "direccion": _string_field("Dirección completa"),
        "fecha_emision": _string_field("Fecha de emisión", "date"),
    },
    "required": ["nombre", "direccion", "fecha_emision"],
}


# Cada spec produce: 1 workflow (+ pipeline de la plantilla) + N doc types + N reglas.
WORKFLOW_SPECS: list[dict] = [
    {
        "tenant_slug": "llamitai-dev", "industry_slug": "general",
        "name": "Extracción de Identidad", "slug": "extraccion-identidad",
        "template_slug": STANDARD_PIPELINE_SLUG,
        "doc_types": [{
            "name": "Cédula de Identidad", "slug": "cedula-identidad",
            "description": "Documento de identificación personal.",
            "fields": CEDULA_FIELDS,
            "validation_rules": [
                {"id": "v-nombre", "prompt": "Verifica que nombres y apellidos sean coherentes con un nombre real.", "enabled": True},
                {"id": "v-cedula", "prompt": "Verifica que numero_cedula tenga entre 7 y 12 dígitos.", "enabled": True},
            ],
        }],
        "rules": [
            {"name": "Identidad completa", "severity": "MAJOR",
             "prompt": "La cédula @cedula-identidad debe traer nombres, apellidos y numero_cedula legibles."},
            {"name": "Cédula con formato válido", "severity": "MINOR",
             "prompt": "Verifica que @cedula-identidad.numero_cedula contenga solo dígitos."},
        ],
    },
    {
        "tenant_slug": "llamitai-dev", "industry_slug": "banking",
        "name": "Análisis de Estados de Cuenta", "slug": "analisis-estados-cuenta",
        "template_slug": ANALYSIS_PIPELINE_SLUG,
        "doc_types": [{
            "name": "Estado de Cuenta", "slug": "estado-cuenta",
            "description": "Estado de cuenta bancario mensual.",
            "fields": ESTADO_CUENTA_FIELDS,
            "validation_rules": [
                {"id": "v-saldo", "prompt": "Verifica que saldo_final sea un monto numérico válido.", "enabled": True},
            ],
        }],
        "rules": [
            {"name": "Saldo final presente", "severity": "BLOCKER",
             "prompt": "El estado de cuenta @estado-cuenta debe incluir un saldo_final."},
        ],
    },
    {
        "tenant_slug": "aseguradora-norte", "industry_slug": "insurance",
        "name": "Validación de Pólizas", "slug": "validacion-polizas",
        "template_slug": STANDARD_CASE_PIPELINE_SLUG,
        "doc_types": [{
            "name": "Póliza de Seguro", "slug": "poliza-seguro",
            "description": "Contrato de póliza de seguro.",
            "fields": POLIZA_FIELDS,
            "validation_rules": [
                {"id": "v-vigencia", "prompt": "Verifica que vigencia_fin sea posterior a vigencia_inicio.", "enabled": True},
            ],
        }],
        "rules": [
            {"name": "Vigencia coherente", "severity": "BLOCKER",
             "prompt": "En @poliza-seguro, vigencia_fin debe ser posterior a vigencia_inicio."},
            {"name": "Prima registrada", "severity": "MAJOR",
             "prompt": "La póliza @poliza-seguro debe declarar una prima mayor a cero."},
        ],
    },
    {
        "tenant_slug": "banco-credito", "industry_slug": "banking",
        "name": "Onboarding de Clientes", "slug": "onboarding-clientes",
        "template_slug": EXTRACT_ASSESS_PIPELINE_SLUG,
        "doc_types": [{
            "name": "Comprobante de Domicilio", "slug": "comprobante-domicilio",
            "description": "Recibo que acredita el domicilio del cliente.",
            "fields": COMPROBANTE_FIELDS,
            "validation_rules": [
                {"id": "v-fecha", "prompt": "Verifica que fecha_emision tenga menos de 3 meses.", "enabled": True},
            ],
        }],
        "rules": [
            {"name": "Comprobante reciente", "severity": "MAJOR",
             "prompt": "El @comprobante-domicilio debe tener una fecha_emision de los últimos 3 meses."},
        ],
    },
]


async def _create_workflow(session: AsyncSession, tenant: TenantORM, spec: dict) -> WorkflowORM | None:
    existing = await session.execute(
        select(WorkflowORM).where(WorkflowORM.tenant_id == tenant.uuid, WorkflowORM.name == spec["name"])
    )
    if existing.scalar_one_or_none():
        typer.echo(f"  = Workflow exists: {spec['name']}")
        return None

    industry = None
    if spec.get("industry_slug"):
        result = await session.execute(select(IndustryORM).where(IndustryORM.slug == spec["industry_slug"]))
        industry = result.scalar_one_or_none()

    creator = WorkflowCreator(
        tenant_id=tenant.uuid,
        name=spec["name"],
        workflow_repository=SQLWorkflowRepository(session),
        pipeline_repository=SQLPipelineRepository(session),
        template_slug=spec["template_slug"],
        industry_id=industry.uuid if industry else None,
        created_by_id=tenant.owner_id,
    )
    workflow = await creator.execute()

    orm = await session.get(WorkflowORM, workflow.uuid)
    orm.slug = spec["slug"]
    await session.flush()
    typer.secho(f"  + Workflow: {spec['name']}  [{spec['template_slug']}]", fg=typer.colors.GREEN)
    return orm


async def _attach(session: AsyncSession, tenant: TenantORM, workflow: WorkflowORM, spec: dict) -> None:
    for dt in spec.get("doc_types", []):
        session.add(DocumentTypeORM(
            uuid=uuid4(), tenant_id=tenant.uuid, workflow_id=workflow.uuid,
            name=dt["name"], slug=dt["slug"], description=dt.get("description"),
            fields=dt["fields"], validation_rules=dt.get("validation_rules", []),
        ))
        typer.echo(f"    · doc type: {dt['name']}")

    for position, rule in enumerate(spec.get("rules", [])):
        session.add(WorkflowRuleORM(
            uuid=uuid4(), tenant_id=tenant.uuid, workflow_id=workflow.uuid,
            name=rule["name"], slug=slugify_rule_name(rule["name"]), kind="VALIDATION",
            prompt=rule["prompt"], position=position, is_active=True,
            config={"severity": rule.get("severity", "MAJOR")},
            scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"}, knowledge_refs=[],
        ))
        typer.echo(f"    · rule: {rule['name']} ({rule.get('severity', 'MAJOR')})")


async def _seed(session: AsyncSession, only_tenant: str | None) -> int:
    specs = [s for s in WORKFLOW_SPECS if not only_tenant or s["tenant_slug"] == only_tenant]
    tenants: dict[str, TenantORM] = {}
    created = 0

    for spec in specs:
        slug = spec["tenant_slug"]
        if slug not in tenants:
            result = await session.execute(select(TenantORM).where(TenantORM.slug == slug))
            tenants[slug] = result.scalar_one_or_none()
        tenant = tenants[slug]
        if not tenant:
            typer.secho(f"  ! Tenant '{slug}' not found — run seed_users.py first. Skipping '{spec['name']}'.",
                        fg=typer.colors.YELLOW)
            continue

        workflow = await _create_workflow(session, tenant, spec)
        if workflow is None:
            continue
        await _attach(session, tenant, workflow, spec)
        await session.commit()
        created += 1

    return created


@app.command()
def seed(
    tenant_slug: Annotated[str | None, typer.Option("--tenant-slug", "-t", help="Only seed this tenant's workflows.")] = None,
) -> None:
    """Create test workflows with pipelines, document types and rules."""

    async def _run() -> None:
        db_config = DatabaseConfig(str(settings.async_database_url))
        try:
            async with db_config.session_maker() as session:
                created = await _seed(session, tenant_slug)
            typer.secho(f"\nDone! {created} workflows created.", fg=typer.colors.GREEN, bold=True)
        finally:
            await db_config.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
