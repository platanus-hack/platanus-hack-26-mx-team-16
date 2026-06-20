"""E7 · F0: WorkflowCapabilitiesResolver — I/O hacia la versión vigente.

El dominio (`derive_capabilities`) es puro; esta capa resuelve workflow → pipeline
1:1 → ``current_version`` y delega. Aquí mockeamos el repo para fijar el contrato:
sin pipeline o sin ``current_version`` ⇒ sin capacidades.
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_empty, contain, equal, expect

from src.common.domain.enums.pipelines import PhaseKind, PipelineKind
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.application.workflows.capabilities_resolver import (
    WorkflowCapabilitiesResolver,
    capabilities_to_payload,
)
from src.workflows.domain.models.pipeline import Pipeline, PhaseSpec, PipelineVersion
from src.workflows.domain.services.capabilities import Capability


def _workflow() -> Workflow:
    return Workflow(uuid=uuid4(), tenant_id=uuid4(), name="WF")


def _pipeline(workflow: Workflow, *, current_version: int | None) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow.uuid,
        tenant_id=workflow.tenant_id,
        slug="wf-pipeline",
        name="WF pipeline",
        kind=PipelineKind.EXTRACTION,
        current_version=current_version,
    )


def _version(pipeline: Pipeline, kinds: list[PhaseKind]) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=pipeline.uuid,
        version=1,
        phases=[PhaseSpec(id=f"{k.value}_{i}", kind=k, config={}) for i, k in enumerate(kinds)],
    )


async def test_for_workflow__derives_from_current_version(pipeline_repository):
    workflow = _workflow()
    pipeline = _pipeline(workflow, current_version=1)
    pipeline_repository.find_by_workflow.return_value = pipeline
    pipeline_repository.get_version.return_value = _version(
        pipeline, [PhaseKind.EXTRACT_FIELDS, PhaseKind.ANALYZE]
    )

    caps = await WorkflowCapabilitiesResolver(pipeline_repository=pipeline_repository).for_workflow(
        workflow
    )

    expect(caps).to(contain(Capability.EXTRACTION))
    expect(caps).to(contain(Capability.ANALYSIS))
    pipeline_repository.get_version.assert_awaited_once_with(pipeline.uuid, 1)


async def test_for_workflow__no_pipeline_yields_empty(pipeline_repository):
    pipeline_repository.find_by_workflow.return_value = None

    caps = await WorkflowCapabilitiesResolver(pipeline_repository=pipeline_repository).for_workflow(
        _workflow()
    )

    expect(caps).to(be_empty)
    pipeline_repository.get_version.assert_not_awaited()


async def test_for_workflow__pipeline_without_current_version_yields_empty(pipeline_repository):
    workflow = _workflow()
    pipeline_repository.find_by_workflow.return_value = _pipeline(workflow, current_version=None)

    caps = await WorkflowCapabilitiesResolver(pipeline_repository=pipeline_repository).for_workflow(
        workflow
    )

    expect(caps).to(be_empty)
    pipeline_repository.get_version.assert_not_awaited()


async def test_for_workflows__maps_each_workflow(pipeline_repository):
    workflow = _workflow()
    pipeline = _pipeline(workflow, current_version=1)
    pipeline_repository.find_by_workflow.return_value = pipeline
    pipeline_repository.get_version.return_value = _version(pipeline, [PhaseKind.EXTRACT_FIELDS])

    result = await WorkflowCapabilitiesResolver(
        pipeline_repository=pipeline_repository
    ).for_workflows([workflow])

    expect(result[workflow.uuid]).to(equal({Capability.EXTRACTION}))


def test_capabilities_to_payload__is_sorted_string_list():
    payload = capabilities_to_payload({Capability.QA, Capability.ANALYSIS, Capability.EXTRACTION})

    expect(payload).to(equal(["analysis", "extraction", "qa"]))
