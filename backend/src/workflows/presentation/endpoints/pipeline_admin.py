"""Pipeline endpoints — phase catalog (tenant-level) + workflow-scoped pipeline.

ADR 0002: el pipeline es propiedad 1:1 del workflow ⇒ las rutas de lectura/edición
viven bajo ``/v1/workflows/{id}/pipeline[/versions]`` (registradas en el workflows
router, gateadas por la matriz E5: leer = ``view``, publicar = ``manage``). Aquí
quedan sus handlers + el ``phase-catalog`` tenant-level (referencia del editor, sin
workflow). Toda escritura valida la receta con ``validate_phases`` contra el
``PHASE_LIBRARY`` real y el ``extractor`` contra ``DocumentExtractorType``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.enums.processing import DocumentExtractorType
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.domain.models.phase_configs import (
    InvalidPhaseConfigError,
    validate_phase_configs,
)
from src.workflows.domain.models.pipeline import Pipeline, PhaseSpec, PipelineVersion
from src.workflows.domain.services.capabilities import Capability, derive_capabilities
from src.workflows.domain.services.capability_macros import (
    ADDABLE_CAPABILITIES,
    addable_capabilities,
    apply_capability,
)
from src.workflows.domain.services.phase_catalog import build_phase_catalog
from src.workflows.domain.services.pipeline_validation import (
    InvalidPipelinePhasesError,
    validate_phases,
)
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository


def _validate_recipe(raw_phases: list[dict]) -> list[PhaseSpec] | ApiJSONResponse:
    """PhaseSpec + validate_phases contra los handlers REALES + extractor válido."""
    # Importar los módulos de fase puebla PHASE_LIBRARY (side-effect deliberado).
    from src.workflows.application.pipelines import (  # noqa: F401
        analysis_phases,
        assess_phases,
        enrich_phases,
        extraction_phases,
        pause_phases,
    )
    from src.workflows.application.pipelines.runtime import PHASE_LIBRARY, PHASE_SCOPES

    try:
        phases = [PhaseSpec.model_validate(p) for p in raw_phases]
        validate_phases(phases, known_kinds=set(PHASE_LIBRARY.keys()), phase_scopes=dict(PHASE_SCOPES))
    except (InvalidPipelinePhasesError, ValueError) as exc:
        return ApiJSONResponse(
            content={"error": "pipeline.invalid_phases", "detail": str(exc)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    valid_extractors = {e.value for e in DocumentExtractorType}
    for phase in phases:
        extractor = (phase.config or {}).get("extractor")
        if extractor is not None and extractor not in valid_extractors:
            return ApiJSONResponse(
                content={
                    "error": "pipeline.invalid_extractor",
                    "detail": f"phase '{phase.id}': unknown extractor '{extractor}' "
                    f"(valid: {sorted(valid_extractors)})",
                },
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
    # Validate-on-write: cada config contra su modelo tipado (extra=forbid ⇒
    # claves desconocidas o tipos inválidos ⇒ 422). Tras el check de extractor
    # para preservar el contrato `pipeline.invalid_extractor`.
    try:
        validate_phase_configs(phases)
    except InvalidPhaseConfigError as exc:
        return ApiJSONResponse(
            content={"error": "pipeline.invalid_phase_config", "detail": str(exc)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return phases


def _recipe_summary(phases: list[PhaseSpec]) -> dict:
    """Resumen ligero de una receta válida (para el 200 del dry-run E6)."""
    return {
        "phaseCount": len(phases),
        "kinds": [phase.kind.value for phase in phases],
    }


class CreatePipelineVersionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    phases: list[dict] = Field(default_factory=list)
    output_schema: dict | None = None


def _present(pipeline: Pipeline) -> dict:
    return {
        "uuid": str(pipeline.uuid),
        "workflowId": str(pipeline.workflow_id),
        "slug": pipeline.slug,
        "name": pipeline.name,
        "kind": pipeline.kind.value,
        "status": pipeline.status.value,
        "current_version": pipeline.current_version,
    }


def _present_version_summary(version_obj: PipelineVersion) -> dict:
    """Resumen de versión para el picker/historial del editor (E6)."""
    return {
        "version": version_obj.version,
        "createdAt": version_obj.created_at.isoformat() if version_obj.created_at else None,
        "phaseCount": len(version_obj.phases),
    }


def _present_version_recipe(version_obj: PipelineVersion) -> dict:
    return {
        "pipeline_id": str(version_obj.pipeline_id),
        "version": version_obj.version,
        "phases": [p.model_dump(mode="json") for p in version_obj.phases],
        "output_schema": version_obj.output_schema,
        # D-A: las policies van plegadas en config de fase (extraction_gate / await_documents).
    }


async def get_phase_catalog(
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """E6 · editor: catálogo de fases (kind + scope + configSchema + description).

    El FE NO hardcodea los kinds: este endpoint es la única fuente de verdad. Los
    kinds/scopes se derivan del ``PHASE_LIBRARY``/``PHASE_SCOPES`` reales (poblados
    al importar los módulos de fase, igual que ``_validate_recipe``) y el enum de
    ``extractor`` del propio ``DocumentExtractorType`` (incluye asr/auto de E6).
    """
    from src.workflows.application.pipelines import (  # noqa: F401
        analysis_phases,
        assess_phases,
        enrich_phases,
        extraction_phases,
        pause_phases,
    )
    from src.workflows.application.pipelines.runtime import PHASE_LIBRARY, PHASE_SCOPES

    catalog = build_phase_catalog(known_kinds=set(PHASE_LIBRARY.keys()), phase_scopes=dict(PHASE_SCOPES))
    # ``configSchema`` lleva claves de dominio (los nombres reales de
    # ``phase.config``: fan_out, on_failure, extractor…). Sin RawJson el
    # render camelCasea esas claves y rompe el contrato con el editor.
    for entry in catalog:
        entry["configSchema"] = RawJson(entry["configSchema"])
    return ApiJSONResponse(content=catalog, status_code=status.HTTP_200_OK)


# ── workflow-scoped pipeline (ADR 0002 · 1:1) ───────────────────────────────
# Registradas en el workflows router (verify_workflow_access + matriz E5):
#   GET  /v1/workflows/{id}/pipeline                  — view
#   GET  /v1/workflows/{id}/pipeline/versions         — view
#   GET  /v1/workflows/{id}/pipeline/versions/{v}     — view
#   POST /v1/workflows/{id}/pipeline/versions[?validate_only=]  — manage


async def get_workflow_pipeline(
    workflow_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """El pipeline propio del workflow (contenedor + puntero a la versión activa)."""
    pipeline = await SQLPipelineRepository(session).find_by_workflow(workflow_id, tenant.uuid)
    if pipeline is None:
        return ApiJSONResponse(
            content={"error": "pipeline.not_found", "detail": str(workflow_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return ApiJSONResponse(content=_present(pipeline), status_code=status.HTTP_200_OK)


async def list_workflow_pipeline_versions(
    workflow_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """E6 · editor: historial de versiones del pipeline del workflow. Newest first."""
    repo = SQLPipelineRepository(session)
    pipeline = await repo.find_by_workflow(workflow_id, tenant.uuid)
    if pipeline is None:
        return ApiJSONResponse(
            content={"error": "pipeline.not_found", "detail": str(workflow_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    versions = await repo.list_versions(pipeline.uuid)
    return ApiJSONResponse(
        content=[_present_version_summary(v) for v in versions],
        status_code=status.HTTP_200_OK,
    )


async def get_workflow_pipeline_version(
    workflow_id: UUID,
    version: int,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    repo = SQLPipelineRepository(session)
    # IDOR guard: la versión NO está tenant-scopeada por sí misma; resolver primero
    # el pipeline del workflow (tenant-scopeado) para que un tenant jamás lea la
    # receta/policies de otro.
    pipeline = await repo.find_by_workflow(workflow_id, tenant.uuid)
    if pipeline is None:
        return ApiJSONResponse(
            content={"detail": "Pipeline version not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    version_obj = await repo.get_version(pipeline.uuid, version)
    if version_obj is None:
        return ApiJSONResponse(
            content={"detail": "Pipeline version not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return ApiJSONResponse(content=_present_version_recipe(version_obj), status_code=status.HTTP_200_OK)


async def create_workflow_pipeline_version(
    workflow_id: UUID,
    request: CreatePipelineVersionRequest,
    session: AsyncSessionDep,
    validate_only: bool = False,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    phases = _validate_recipe(request.phases)
    if isinstance(phases, ApiJSONResponse):
        return phases

    # E6 · editor: dry-run. Misma validación que el publish real (mismo 422), pero
    # sin tocar el repo — no se crea versión ni se mueve current_version.
    if validate_only:
        return ApiJSONResponse(
            content={"valid": True, "summary": _recipe_summary(phases)},
            status_code=status.HTTP_200_OK,
        )

    repo = SQLPipelineRepository(session)
    pipeline = await repo.find_by_workflow(workflow_id, tenant.uuid)
    if pipeline is None:
        return ApiJSONResponse(
            content={"error": "pipeline.not_found", "detail": str(workflow_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    latest = await repo.latest_version(pipeline.uuid)
    next_version = (latest.version if latest else 0) + 1
    version = await repo.add_version(
        PipelineVersion(
            uuid=uuid4(),
            pipeline_id=pipeline.uuid,
            version=next_version,
            phases=[p.model_dump() for p in phases],
            output_schema=request.output_schema,
        )
    )
    # add_version NO avanza el puntero (gotcha del recon): activarla es explícito aquí.
    pipeline.current_version = version.version
    pipeline = await repo.upsert(pipeline)
    return ApiJSONResponse(
        content={
            **_present(pipeline),
            "version": version.version,
        },
        status_code=status.HTTP_201_CREATED,
    )


class AddCapabilityRequest(BaseModel):
    capability: str


async def add_workflow_capability(
    workflow_id: UUID,
    request: AddCapabilityRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """E7 · F3 — wizard «agregar capacidad».

    Inserta las fases + scaffolds de policy de la capacidad sobre la versión
    vigente del pipeline y publica v+1 (mismo camino que el editor: misma
    validación, mismo avance de ``current_version``). Idempotente a nivel de API:
    una capacidad ya presente devuelve 409.
    """
    try:
        capability = Capability(request.capability)
    except ValueError:
        return ApiJSONResponse(
            content={
                "error": "capability.unknown",
                "detail": f"unknown capability '{request.capability}' "
                f"(addable: {sorted(c.value for c in ADDABLE_CAPABILITIES)})",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if capability not in ADDABLE_CAPABILITIES:
        return ApiJSONResponse(
            content={
                "error": "capability.not_addable",
                "detail": f"'{capability.value}' is the base / not addable by the wizard",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    repo = SQLPipelineRepository(session)
    pipeline = await repo.find_by_workflow(workflow_id, tenant.uuid)
    if pipeline is None or pipeline.current_version is None:
        return ApiJSONResponse(
            content={"error": "pipeline.not_found", "detail": str(workflow_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    current = await repo.get_version(pipeline.uuid, pipeline.current_version)
    if current is None:
        return ApiJSONResponse(
            content={"error": "pipeline.not_found", "detail": str(workflow_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if capability not in addable_capabilities(current):
        return ApiJSONResponse(
            content={
                "error": "capability.already_present",
                "detail": f"'{capability.value}' is already enabled by this pipeline",
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    macro = apply_capability(
        [p.model_dump(mode="json") for p in current.phases],
        capability,
    )
    validated = _validate_recipe(macro.phases)
    if isinstance(validated, ApiJSONResponse):
        return validated  # 422 — no debería pasar (las macros son válidas), pero por defensa

    next_version = pipeline.current_version + 1
    version = await repo.add_version(
        PipelineVersion(
            uuid=uuid4(),
            pipeline_id=pipeline.uuid,
            version=next_version,
            phases=[p.model_dump() for p in validated],
            output_schema=current.output_schema,
        )
    )
    pipeline.current_version = version.version
    pipeline = await repo.upsert(pipeline)
    return ApiJSONResponse(
        content={
            **_present(pipeline),
            "version": version.version,
            "addedCapability": capability.value,
            "capabilities": sorted(c.value for c in derive_capabilities(version)),
        },
        status_code=status.HTTP_201_CREATED,
    )


# Tenant-level: solo el catálogo de fases (referencia del editor, sin workflow).
pipelines_router = APIRouter(prefix="/pipelines", tags=["Pipelines"])

pipelines_router.add_api_route(
    "/phase-catalog",
    get_phase_catalog,
    methods=["GET"],
    summary="Phase catalog for the visual editor (E6 · kind/scope/configSchema)",
)
