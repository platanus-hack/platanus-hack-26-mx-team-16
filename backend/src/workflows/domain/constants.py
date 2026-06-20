from src.common.settings import settings

TEMPORAL_HOST: str = settings.TEMPORAL_HOST
TASK_QUEUE: str = settings.TEMPORAL_TASK_QUEUE

NON_RETRYABLE_CODES: frozenset[str] = frozenset(
    {
        "document_type.not_found",
        "extract_fields.no_documents",
    }
)

# Nombres de Lambdas: ver src/workflows/domain/lambda_catalog.py (E1) — la
# resolución es en call time con pin por fase dentro de la PipelineVersion.

STAGE: str = str(settings.STAGE.value) if hasattr(settings.STAGE, "value") else str(settings.STAGE)

ASSETS_BUCKET: str = f"vnext-assets-{STAGE}"

# pg_notify channel for the workflow_processing_jobs persistence layer.
# Distinct from the SSE channel (`workflow_document_updated` in pg_notifier).
WORKFLOW_PROCESSING_JOBS_CHANNEL: str = "workflow_processing_jobs"
