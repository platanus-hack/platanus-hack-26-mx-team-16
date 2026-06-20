"""Entidades de lectura del plano staff (ADR 0001).

Shapes compactos para la cola L1 unificada y el caso read-only. El tenant
viaja junto a cada recurso (la cola es cross-tenant: el FE necesita
``tenantName`` sin pagar un lookup extra).
"""

from dataclasses import dataclass, field

from src.workflows.domain.models.human_task import HumanTask


@dataclass
class StaffQueueItem:
    """Una tarea L1 de la cola unificada + contexto de tenant (barato: join)."""

    task: HumanTask
    tenant_name: str | None = None
    tenant_slug: str | None = None


@dataclass
class StaffCaseAggregate:
    """Caso read-only cross-tenant: caso + docs + runs + análisis + timeline.

    Espejo de ``CaseAggregate`` (M2M) + contexto de tenant. Solo lectura:
    la superficie staff jamás escribe sobre el caso (ADR 0001, alcance mínimo).
    """

    case: object
    documents: list = field(default_factory=list)
    runs: list = field(default_factory=list)
    latest_summary: object | None = None
    timeline: list = field(default_factory=list)
    tenant_name: str | None = None
    tenant_slug: str | None = None
