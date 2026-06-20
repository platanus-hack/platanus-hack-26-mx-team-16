"""F8 · W2: ingest resolves a Source, authenticates, and dispatches the pipeline."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.application.helpers.secrets import hash_token
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.common.domain.enums.sources import SourceAuthMode
from src.connections.domain.exceptions import (
    SourceAuthFailedError,
    SourceNotFoundError,
    SourcePipelineNotConfiguredError,
)
from src.connections.domain.models.workflow_source import WorkflowSource
from src.workflows.application.sources.ingest import IngestViaSource
from src.workflows.domain.models.pipeline import Pipeline

_API_KEY = "dxk_secret-key"
_TENANT = uuid4()


def _source() -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=uuid4(),
        route_token="src_abc",
        auth_mode=SourceAuthMode.API_KEY,
        secret=hash_token(_API_KEY),
    )


def _pipeline(workflow_id=None) -> Pipeline:
    # ADR 0002: the pipeline is owned 1:1 by a workflow (workflow_id NOT NULL).
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id or uuid4(),
        tenant_id=_TENANT,
        slug="standard-extraction",
        name="Standard",
        kind=PipelineKind.EXTRACTION,
        status=PipelineStatus.ACTIVE,
        current_version=1,
    )


class _SourceRepo:
    def __init__(self, source):
        self._source = source

    async def find_by_route_token(self, token):
        return self._source if (self._source and self._source.route_token == token) else None


class _PipelineRepo:
    def __init__(self, pipeline):
        self._pipeline = pipeline
        self.queried_with = None

    async def find_by_workflow(self, workflow_id, tenant_id):
        # ADR 0002: ingest resolves the workflow's OWN pipeline; the deprecated
        # source.config ``pipeline_slug`` is ignored (contract §8).
        self.queried_with = (workflow_id, tenant_id)
        return self._pipeline


class _TemporalClient:
    def __init__(self):
        self.started = []

    async def start_workflow(self, run, arg, **kwargs):
        self.started.append((arg, kwargs))


def _ingest(source, pipeline, client, **overrides):
    return IngestViaSource(
        route_token="src_abc",
        object_key="s3://b/in.pdf",
        file_name="in.pdf",
        source_repository=_SourceRepo(source),
        pipeline_repository=_PipelineRepo(pipeline),
        temporal_client=client,
        task_queue="default",
        file_id=uuid4(),
        processing_job_uuid=uuid4(),
        case_id=overrides.get("case_id"),
        api_key=overrides.get("api_key", _API_KEY),
    )


async def test_ingest__dispatches_interpreter_with_sealed_pipeline():
    source, client = _source(), _TemporalClient()
    pipeline = _pipeline(workflow_id=source.workflow_id)
    repo = _PipelineRepo(pipeline)

    use_case = _ingest(source, pipeline, client)
    use_case.pipeline_repository = repo
    job_id = await use_case.execute()

    # ADR 0002: resolved via the workflow's own pipeline, not by slug.
    expect(repo.queried_with).to(equal((source.workflow_id, source.tenant_id)))
    expect(len(client.started)).to(equal(1))
    arg, kwargs = client.started[0]
    expect(isinstance(arg, PipelineRunInput)).to(equal(True))
    expect(arg.pipeline_id).to(equal(pipeline.uuid))
    expect(arg.version).to(equal(1))
    expect(kwargs["id"]).to(equal(job_id))


async def test_ingest__case_id_travels_in_the_processing_input():
    source, pipeline, client = _source(), _pipeline(), _TemporalClient()
    case_id = uuid4()

    await _ingest(source, pipeline, client, case_id=case_id).execute()

    arg, _ = client.started[0]
    expect(arg.document.case_id).to(equal(case_id))
    # E5: con caso, el run del archivo es document-scope (la cola del caso
    # vive en el CASE# durable) — sin esto, await_documents espera inline.
    expect(arg.scope).to(equal("document"))


async def test_ingest__without_case_keeps_anonymous_input():
    source, pipeline, client = _source(), _pipeline(), _TemporalClient()

    await _ingest(source, pipeline, client).execute()

    arg, _ = client.started[0]
    expect(arg.document.case_id).to(equal(None))
    expect(arg.scope).to(equal(None))


class _DoctypeRepo:
    """E5: classify necesita el catálogo — el use case lo carga si nadie lo pasó."""

    def __init__(self, doctypes):
        self._doctypes = doctypes
        self.queried_with = None

    async def list_by_workflow(self, workflow_id, tenant_id):
        self.queried_with = (workflow_id, tenant_id)
        return self._doctypes


def _doctype(name: str, slug: str):
    from src.common.domain.models.processing.document_type import DocumentType

    return DocumentType(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=uuid4(),
        name=name,
        slug=slug,
        fields={"fields": {"nombre": {"type": "string"}}},
    )


async def test_ingest__loads_doctype_catalog_when_not_provided():
    source, pipeline, client = _source(), _pipeline(), _TemporalClient()
    repo = _DoctypeRepo([_doctype("Persona Embargo", "persona_embargo")])

    use_case = _ingest(source, pipeline, client)
    use_case.document_type_repository = repo

    await use_case.execute()

    arg, _ = client.started[0]
    expect(repo.queried_with).to(equal((source.workflow_id, source.tenant_id)))
    expect(len(arg.document.document_types)).to(equal(1))
    expect(arg.document.document_types[0]["name"]).to(equal("Persona Embargo"))
    expect(arg.document.document_types[0]["slug"]).to(equal("persona_embargo"))


async def test_ingest__explicit_document_types_skip_the_lookup():
    source, pipeline, client = _source(), _pipeline(), _TemporalClient()
    repo = _DoctypeRepo([_doctype("Persona Embargo", "persona_embargo")])

    use_case = _ingest(source, pipeline, client)
    use_case.document_types = [{"uuid": "x", "name": "Circular", "slug": "circular"}]
    use_case.document_type_repository = repo

    await use_case.execute()

    arg, _ = client.started[0]
    expect(repo.queried_with).to(equal(None))
    expect(arg.document.document_types[0]["name"]).to(equal("Circular"))


async def test_ingest__unknown_token_raises_not_found():
    client = _TemporalClient()
    with pytest.raises(SourceNotFoundError):
        await _ingest(None, _pipeline(), client).execute()
    expect(client.started).to(equal([]))


async def test_ingest__bad_api_key_raises_auth_failed():
    client = _TemporalClient()
    with pytest.raises(SourceAuthFailedError):
        await _ingest(_source(), _pipeline(), client, api_key="dxk_wrong").execute()
    expect(client.started).to(equal([]))


async def test_ingest__missing_pipeline_raises_not_configured():
    # ADR 0002: find_by_workflow returns None ⇒ the workflow has no pipeline;
    # the use case raises SourcePipelineNotConfiguredError (no-arg) and dispatches
    # nothing (the deprecated config pipeline_slug is no longer a fallback).
    client = _TemporalClient()
    with pytest.raises(SourcePipelineNotConfiguredError):
        await _ingest(_source(), None, client).execute()
    expect(client.started).to(equal([]))
