from src.common.database.models.pipeline import PipelineORM, PipelineVersionORM
from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.workflows.domain.models.pipeline import Pipeline, PhaseSpec, PipelineVersion


def build_pipeline(orm: PipelineORM) -> Pipeline:
    return Pipeline(
        uuid=orm.uuid,
        workflow_id=orm.workflow_id,
        tenant_id=orm.tenant_id,
        slug=orm.slug,
        name=orm.name,
        kind=PipelineKind(orm.kind),
        status=PipelineStatus(orm.status),
        current_version=orm.current_version,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def build_pipeline_version(orm: PipelineVersionORM) -> PipelineVersion:
    return PipelineVersion(
        uuid=orm.uuid,
        pipeline_id=orm.pipeline_id,
        version=orm.version,
        phases=[PhaseSpec.model_validate(p) for p in (orm.phases or [])],
        output_schema=orm.output_schema,
        created_at=orm.created_at,
    )
