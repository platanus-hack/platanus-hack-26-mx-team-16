"""Unit tests de ``DuplicateWorkflow`` — duplicar = deep-copy, no compartir (ADR 0002 · §3.7).

Reúso por duplicación: se crea un workflow NUEVO (copy-on-create le da su pipeline
propio v1) y se le importa **en memoria** el bundle del origen ⇒ cero referencias
compartidas (el BUG 3 — pipeline compartido — es imposible por construcción).

Se cablea el flujo real exporter→creator→importer a través de mocks autospec, con
doc-types/reglas vacíos y un pipeline+versión real en el origen para mantenerlo
determinista. Las aserciones clave: ``workflow_repository.create`` se invoca con un
workflow de ``name == new_name`` y ``workflow_type`` del origen; el duplicado tiene
``uuid`` distinto; y su ``pipeline_id`` NO es el del origen (sin pipeline compartido).
"""

from __future__ import annotations

from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from expects import equal, expect, not_

from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.common.domain.models.processing.workflow import Workflow
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.application.workflows.duplicate import DuplicateWorkflow
from src.workflows.domain.models.pipeline import PhaseSpec, Pipeline, PipelineVersion
from src.workflows.domain.recipes import standard_extraction_phases
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@pytest.fixture
def rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def kb_document_repository():
    return create_autospec(spec=KBDocumentRepository, spec_set=True, instance=True)


def _source_workflow(tenant_id) -> Workflow:
    """Origen con pipeline propio bindeado y config de análisis para heredar."""
    return Workflow(
        uuid=uuid4(),
        tenant_id=tenant_id,
        pipeline_id=uuid4(),
        name="Original",
        slug="original",
        output_schema={"type": "object"},
        synthesis_template="resumen",
        synthesis_enabled=True,
    )


def _source_pipeline(source: Workflow) -> Pipeline:
    return Pipeline(
        uuid=source.pipeline_id,
        workflow_id=source.uuid,
        tenant_id=source.tenant_id,
        slug="original-pipeline",
        name="Original pipeline",
        kind=PipelineKind.ANALYSIS,
        status=PipelineStatus.ACTIVE,
        current_version=1,
    )


def _source_version(pipeline: Pipeline) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=pipeline.uuid,
        version=1,
        phases=[PhaseSpec.model_validate(p) for p in standard_extraction_phases()],
    )


def _wire_repositories(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    """Cablea el flujo completo exporter→creator→importer de forma determinista.

    Devuelve ``(source, source_pipeline)`` para las aserciones. Doc-types y reglas
    vacíos; el origen tiene pipeline+versión real; el creator provisiona un pipeline
    propio nuevo y el importer appendea una v2 a ESE pipeline.
    """
    source = _source_workflow(tenant_id)
    src_pipeline = _source_pipeline(source)
    src_version = _source_version(src_pipeline)

    # Estado mutable de los workflows por uuid (creator.create siembra el nuevo;
    # find_by_id resuelve origen o duplicado según el id pedido).
    workflows: dict = {source.uuid: source}

    async def _find_workflow(workflow_id, _tenant_id):
        return workflows.get(workflow_id)

    async def _create_workflow(workflow):
        workflows[workflow.uuid] = workflow
        return workflow

    async def _update_workflow(workflow):
        workflows[workflow.uuid] = workflow
        return workflow

    workflow_repository.find_by_id.side_effect = _find_workflow
    workflow_repository.create.side_effect = _create_workflow
    workflow_repository.update.side_effect = _update_workflow
    workflow_repository.list_by_tenant.return_value = list(workflows.values())

    # Pipelines: el origen se resuelve por id (exporter); el del duplicado, por
    # workflow_id (creator lo provisiona, importer lo reusa para la v2).
    pipelines_by_id: dict = {src_pipeline.uuid: src_pipeline}
    pipelines_by_workflow: dict = {source.uuid: src_pipeline}
    versions: dict = {(src_pipeline.uuid, 1): src_version}

    async def _find_pipeline_by_id(pipeline_id, _tenant_id):
        return pipelines_by_id.get(pipeline_id)

    async def _find_pipeline_by_workflow(workflow_id, _tenant_id):
        return pipelines_by_workflow.get(workflow_id)

    async def _upsert_pipeline(pipeline):
        pipelines_by_id[pipeline.uuid] = pipeline
        pipelines_by_workflow[pipeline.workflow_id] = pipeline
        return pipeline

    async def _add_version(version):
        versions[(version.pipeline_id, version.version)] = version
        return version

    async def _get_version(pipeline_id, version):
        return versions.get((pipeline_id, version))

    async def _latest_version(pipeline_id):
        matching = [v for (pid, _), v in versions.items() if pid == pipeline_id]
        return max(matching, key=lambda v: v.version) if matching else None

    pipeline_repository.find_by_id.side_effect = _find_pipeline_by_id
    pipeline_repository.find_by_workflow.side_effect = _find_pipeline_by_workflow
    pipeline_repository.upsert.side_effect = _upsert_pipeline
    pipeline_repository.add_version.side_effect = _add_version
    pipeline_repository.get_version.side_effect = _get_version
    pipeline_repository.latest_version.side_effect = _latest_version

    # Sin doc-types ni reglas ⇒ exporter/importer fluyen sin tocar más repos.
    document_type_repository.list_by_workflow.return_value = []
    rule_repository.list_by_workflow.return_value = []

    return source, src_pipeline


async def test_execute__creates_new_workflow_with_new_name_and_same_type(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange
    source, _ = _wire_repositories(
        tenant_id,
        workflow_repository,
        pipeline_repository,
        rule_repository,
        document_type_repository,
        kb_document_repository,
    )

    # Act
    duplicate = await DuplicateWorkflow(
        source_workflow_id=source.uuid,
        tenant_id=tenant_id,
        new_name="Copia",
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — create se invocó con el nombre nuevo (E7·F2: ya no hay tipo).
    workflow_repository.create.assert_awaited_once()
    created = workflow_repository.create.call_args.args[0]
    expect(created.name).to(equal("Copia"))
    expect(created.tenant_id).to(equal(tenant_id))

    # Assert — el duplicado es un workflow distinto del origen.
    expect(duplicate.uuid).to_not(equal(source.uuid))
    expect(duplicate.name).to(equal("Copia"))


async def test_execute__duplicate_owns_a_private_pipeline_not_the_sources(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange
    source, src_pipeline = _wire_repositories(
        tenant_id,
        workflow_repository,
        pipeline_repository,
        rule_repository,
        document_type_repository,
        kb_document_repository,
    )

    # Act
    duplicate = await DuplicateWorkflow(
        source_workflow_id=source.uuid,
        tenant_id=tenant_id,
        new_name="Copia",
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — copy-on-create provisionó un pipeline propio (no el del origen).
    pipeline_repository.upsert.assert_awaited()
    provisioned = pipeline_repository.upsert.call_args_list[0].args[0]
    expect(provisioned.workflow_id).to(equal(duplicate.uuid))
    expect(provisioned.uuid).to_not(equal(src_pipeline.uuid))

    # Assert — el binding del duplicado NO apunta al pipeline del origen (BUG 3).
    expect(duplicate.pipeline_id).to_not(equal(source.pipeline_id))
    expect(duplicate.pipeline_id).to(equal(provisioned.uuid))


async def test_execute__exports_source_then_imports_into_new_workflow_pipeline(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange
    source, src_pipeline = _wire_repositories(
        tenant_id,
        workflow_repository,
        pipeline_repository,
        rule_repository,
        document_type_repository,
        kb_document_repository,
    )

    # Act
    duplicate = await DuplicateWorkflow(
        source_workflow_id=source.uuid,
        tenant_id=tenant_id,
        new_name="Copia",
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — el exporter leyó la versión sellada del pipeline del ORIGEN.
    pipeline_repository.get_version.assert_any_await(src_pipeline.uuid, 1)

    # Assert — el importer appendeó una versión al pipeline PROPIO del duplicado
    # (resuelto por workflow_id del nuevo workflow, no por el del origen).
    pipeline_repository.find_by_workflow.assert_any_await(duplicate.uuid, tenant_id)
    added_pipeline_ids = {
        call.args[0].pipeline_id for call in pipeline_repository.add_version.call_args_list
    }
    expect(duplicate.pipeline_id in added_pipeline_ids).to(equal(True))
    expect(src_pipeline.uuid in added_pipeline_ids).to(equal(False))


async def test_execute__inherits_analysis_config_from_source(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange
    source, _ = _wire_repositories(
        tenant_id,
        workflow_repository,
        pipeline_repository,
        rule_repository,
        document_type_repository,
        kb_document_repository,
    )

    # Act
    duplicate = await DuplicateWorkflow(
        source_workflow_id=source.uuid,
        tenant_id=tenant_id,
        new_name="Copia",
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — config heredada (output_schema/synthesis), nombre nuevo, sin compartir.
    expect(duplicate.output_schema).to(equal(source.output_schema))
    expect(duplicate.synthesis_template).to(equal(source.synthesis_template))
    expect(duplicate.synthesis_enabled).to(equal(source.synthesis_enabled))
    expect(duplicate.name).to(not_(equal(source.name)))


async def test_execute__copies_case_noun_from_source(
    tenant_id,
    workflow_repository,
    pipeline_repository,
    rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange — el origen tiene un sustantivo de caso propio (case-noun §3.5).
    source, _ = _wire_repositories(
        tenant_id,
        workflow_repository,
        pipeline_repository,
        rule_repository,
        document_type_repository,
        kb_document_repository,
    )
    source.case_noun = {
        "es": {"one": "Pedido", "other": "Pedidos"},
        "en": {"one": "Order", "other": "Orders"},
    }

    # Act
    duplicate = await DuplicateWorkflow(
        source_workflow_id=source.uuid,
        tenant_id=tenant_id,
        new_name="Copia",
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — el sustantivo del caso se hereda en el duplicado.
    expect(duplicate.case_noun).to(equal(source.case_noun))
