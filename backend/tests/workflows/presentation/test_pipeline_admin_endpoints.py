"""E6 · editor de pipelines — endpoints nuevos del pipeline_admin.

Cubre los tres entregables del frente W2 llamando a los handlers directamente
(son funciones async planas) con repos mockeados:

- ``get_phase_catalog``: catálogo derivado del registry REAL (incluye asr/auto en
  el enum de ``extractor``).
- ``list_pipeline_versions``: 404 si el pipeline no existe; resumen newest-first.
- ``create_pipeline_version(validate_only=True)``: 200 ``{valid, summary}`` con
  receta válida y 422 con el MISMO detail que el publish real — SIN persistir.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from expects import contain, equal, expect, have_keys

import src.workflows.presentation.endpoints.pipeline_admin as admin
from src.workflows.presentation.endpoints.pipeline_admin import (
    CreatePipelineVersionRequest,
    create_workflow_pipeline_version,
    get_phase_catalog,
    get_workflow_pipeline_version,
    list_workflow_pipeline_versions,
)


def _tenant():
    return SimpleNamespace(uuid=uuid4())


def _payload(response) -> dict:
    """Desenvuelve el cuerpo renderizado: error ⇒ raw; ok ⇒ {data, timestamp}."""
    body = json.loads(response.body)
    return body.get("data", body)


# ── phase-catalog ────────────────────────────────────────────────────────────


async def test_phase_catalog__returns_real_registry_kinds():
    response = await get_phase_catalog(tenant=_tenant())

    expect(response.status_code).to(equal(200))
    catalog = _payload(response)
    kinds = {entry["kind"] for entry in catalog}
    # Kinds reales registrados por @register_phase al importar los módulos de fase.
    expect(kinds).to(contain("extract_text"))
    expect(kinds).to(contain("classify_pages"))
    expect(kinds).to(contain("enrich"))


async def test_phase_catalog__extractor_enum_includes_asr_and_auto():
    response = await get_phase_catalog(tenant=_tenant())

    catalog = _payload(response)
    extract_text = next(e for e in catalog if e["kind"] == "extract_text")
    extractor_enum = extract_text["configSchema"]["extractor"]["enum"]
    expect(extractor_enum).to(contain("asr"))
    expect(extractor_enum).to(contain("auto"))


async def test_phase_catalog__case_phases_carry_case_scope():
    response = await get_phase_catalog(tenant=_tenant())

    catalog = _payload(response)
    enrich = next(e for e in catalog if e["kind"] == "enrich")
    expect(enrich["scope"]).to(equal("case"))


# ── list versions ────────────────────────────────────────────────────────────


def _patch_repo(monkeypatch, repo):
    monkeypatch.setattr(admin, "SQLPipelineRepository", lambda session: repo)


async def test_list_versions__404_when_pipeline_missing(monkeypatch):
    repo = MagicMock()
    repo.find_by_workflow = AsyncMock(return_value=None)
    repo.list_versions = AsyncMock()
    _patch_repo(monkeypatch, repo)

    response = await list_workflow_pipeline_versions(
        workflow_id=uuid4(), session=MagicMock(), tenant=_tenant()
    )

    expect(response.status_code).to(equal(404))
    expect(_payload(response)).to(have_keys("error"))
    repo.list_versions.assert_not_called()


async def test_list_versions__returns_summaries(monkeypatch):
    pipeline = SimpleNamespace(uuid=uuid4())
    versions = [
        SimpleNamespace(version=2, created_at=None, phases=[1, 2, 3]),
        SimpleNamespace(version=1, created_at=None, phases=[1]),
    ]
    repo = MagicMock()
    repo.find_by_workflow = AsyncMock(return_value=pipeline)
    repo.list_versions = AsyncMock(return_value=versions)
    _patch_repo(monkeypatch, repo)

    response = await list_workflow_pipeline_versions(
        workflow_id=uuid4(), session=MagicMock(), tenant=_tenant()
    )

    expect(response.status_code).to(equal(200))
    summaries = _payload(response)
    expect([s["version"] for s in summaries]).to(equal([2, 1]))
    expect(summaries[0]).to(have_keys("version", "createdAt", "phaseCount"))
    expect(summaries[0]["phaseCount"]).to(equal(3))


# ── get version (IDOR / tenant scoping) ──────────────────────────────────────


async def test_get_version__cross_tenant_is_404_without_reading_version(monkeypatch):
    """Bug 6 (IDOR): tenant B pide la versión del pipeline de un workflow de tenant A.

    ``find_by_workflow`` está tenant-scopeada ⇒ devuelve None para el tenant ajeno,
    así que el handler corta con 404 y NUNCA llega a ``get_version`` (que por sí sola
    no filtra por tenant). Antes del fix se leía la receta/policies del otro tenant.
    """
    repo = MagicMock()
    # pipeline de A no visible para B (find_by_workflow tenant-scopeado)
    repo.find_by_workflow = AsyncMock(return_value=None)
    repo.get_version = AsyncMock()
    _patch_repo(monkeypatch, repo)

    response = await get_workflow_pipeline_version(
        workflow_id=uuid4(), version=1, session=MagicMock(), tenant=_tenant()
    )

    expect(response.status_code).to(equal(404))
    # La versión jamás se consulta ⇒ no hay fuga de la receta del otro tenant.
    repo.get_version.assert_not_called()


async def test_get_version__owner_reads_own_version(monkeypatch):
    """Tenant A sigue leyendo su propia versión (recipe + policies camelCase)."""
    pipeline = SimpleNamespace(uuid=uuid4())
    version_obj = SimpleNamespace(
        pipeline_id=pipeline.uuid,
        version=2,
        phases=[],
        output_schema={"foo": "bar"},
    )
    repo = MagicMock()
    repo.find_by_workflow = AsyncMock(return_value=pipeline)
    repo.get_version = AsyncMock(return_value=version_obj)
    _patch_repo(monkeypatch, repo)

    response = await get_workflow_pipeline_version(
        workflow_id=uuid4(), version=2, session=MagicMock(), tenant=_tenant()
    )

    expect(response.status_code).to(equal(200))
    payload = _payload(response)
    expect(payload["version"]).to(equal(2))
    expect(payload).to(have_keys("outputSchema"))
    # La versión se resuelve contra el pipeline ya verificado por tenant.
    repo.get_version.assert_called_once_with(pipeline.uuid, 2)


# ── validate_only (dry-run) ──────────────────────────────────────────────────

_VALID_RECIPE = [
    {"id": "ingest", "kind": "ingest", "config": {}},
    {"id": "extract_text", "kind": "extract_text", "config": {"extractor": "auto"}},
    {"id": "extract_fields", "kind": "extract_fields", "config": {}},
    {"id": "finalize", "kind": "finalize", "config": {}},
]


async def test_validate_only__valid_recipe_returns_200_without_persisting(monkeypatch):
    repo = MagicMock()
    repo.find_by_workflow = AsyncMock()
    repo.add_version = AsyncMock()
    repo.upsert = AsyncMock()
    _patch_repo(monkeypatch, repo)

    request = CreatePipelineVersionRequest(phases=_VALID_RECIPE)
    response = await create_workflow_pipeline_version(
        workflow_id=uuid4(),
        request=request,
        session=MagicMock(),
        validate_only=True,
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(200))
    payload = _payload(response)
    expect(payload["valid"]).to(equal(True))
    expect(payload["summary"]["phaseCount"]).to(equal(4))
    # Dry-run: jamás toca el repo.
    repo.find_by_workflow.assert_not_called()
    repo.add_version.assert_not_called()
    repo.upsert.assert_not_called()


async def test_validate_only__invalid_recipe_returns_422_same_detail(monkeypatch):
    repo = MagicMock()
    repo.add_version = AsyncMock()
    _patch_repo(monkeypatch, repo)

    # ingest es document-scope DESPUÉS de un enrich case-scope ⇒ viola la regla E4.
    bad_recipe = [
        {"id": "enrich", "kind": "enrich", "config": {"tool": "lookup"}},
        {"id": "ingest", "kind": "ingest", "config": {}},
    ]
    request = CreatePipelineVersionRequest(phases=bad_recipe)
    response = await create_workflow_pipeline_version(
        workflow_id=uuid4(),
        request=request,
        session=MagicMock(),
        validate_only=True,
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(422))
    payload = _payload(response)
    expect(payload["error"]).to(equal("pipeline.invalid_phases"))
    repo.add_version.assert_not_called()


async def test_validate_only__invalid_gate_activation_returns_422(monkeypatch):
    # D-A: la activación va en extraction_gate.config.activation ⇒ una inválida
    # (umbral fuera de [0,1]) la caza validate_phase_configs como invalid_phase_config.
    repo = MagicMock()
    repo.add_version = AsyncMock()
    _patch_repo(monkeypatch, repo)

    request = CreatePipelineVersionRequest(
        phases=[
            {"id": "ingest", "kind": "ingest", "config": {}},
            {"id": "await_documents", "kind": "await_documents", "config": {}},
            {
                "id": "extraction_gate",
                "kind": "extraction_gate",
                "config": {"activation": {"field_thresholds": {"default": 5.0}}},
            },
        ],
    )
    response = await create_workflow_pipeline_version(
        workflow_id=uuid4(),
        request=request,
        session=MagicMock(),
        validate_only=True,
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(422))
    expect(_payload(response)["error"]).to(equal("pipeline.invalid_phase_config"))
    repo.add_version.assert_not_called()


async def test_validate_only__unknown_config_key_returns_422_phase_config(monkeypatch):
    repo = MagicMock()
    repo.add_version = AsyncMock()
    _patch_repo(monkeypatch, repo)

    # Clave desconocida en finalize.config ⇒ validate-on-write (extra=forbid).
    bad_recipe = [
        {"id": "ingest", "kind": "ingest", "config": {}},
        {"id": "finalize", "kind": "finalize", "config": {"bogus_key": True}},
    ]
    request = CreatePipelineVersionRequest(phases=bad_recipe)
    response = await create_workflow_pipeline_version(
        workflow_id=uuid4(),
        request=request,
        session=MagicMock(),
        validate_only=True,
        tenant=_tenant(),
    )

    expect(response.status_code).to(equal(422))
    payload = _payload(response)
    expect(payload["error"]).to(equal("pipeline.invalid_phase_config"))
    expect(payload["detail"]).to(contain("finalize"))
    repo.add_version.assert_not_called()
