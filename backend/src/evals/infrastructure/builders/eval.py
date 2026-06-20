from src.common.database.models.eval import EvalCaseORM, EvalDatasetORM, EvalRunORM
from src.evals.domain.models.dataset import EvalCase, EvalDataset
from src.evals.domain.models.run import EvalRun


def build_eval_dataset(orm: EvalDatasetORM) -> EvalDataset:
    return EvalDataset(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        name=orm.name,
        pipeline_slug=orm.pipeline_slug,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def build_eval_case(orm: EvalCaseORM) -> EvalCase:
    return EvalCase(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        dataset_id=orm.dataset_id,
        input_ref=orm.input_ref,
        expected=orm.expected or {},
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def build_eval_run(orm: EvalRunORM) -> EvalRun:
    return EvalRun(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        dataset_id=orm.dataset_id,
        pipeline_version=orm.pipeline_version,
        status=orm.status,
        metrics=orm.metrics or {},
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
