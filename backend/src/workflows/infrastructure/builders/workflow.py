from src.common.database.models.workspace import WorkflowORM
from src.common.domain.models.processing.workflow import Workflow


def build_workflow(orm_instance: WorkflowORM) -> Workflow:
    return Workflow(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        industry_id=orm_instance.industry_id,
        pipeline_id=orm_instance.pipeline_id,
        name=orm_instance.name,
        slug=orm_instance.slug,
        access_type=orm_instance.access_type,
        created_by_id=orm_instance.created_by_id,
        selected_doc_types=orm_instance.selected_doc_types,
        kb_document_ids=orm_instance.kb_document_ids,
        per_doc_kb_ids=orm_instance.per_doc_kb_ids,
        structuring_model=orm_instance.structuring_model,
        llm_model=orm_instance.llm_model,
        analysis_reviewer_model=orm_instance.analysis_reviewer_model,
        analysis_critic_model=orm_instance.analysis_critic_model,
        analysis_consensus_samples=orm_instance.analysis_consensus_samples,
        output_schema=orm_instance.output_schema,
        synthesis_template=orm_instance.synthesis_template,
        synthesis_enabled=orm_instance.synthesis_enabled,
        synthesis_uses_documents=orm_instance.synthesis_uses_documents,
        webhook_url=orm_instance.webhook_url,
        webhook_enabled=orm_instance.webhook_enabled,
        webhook_secret=orm_instance.webhook_secret,
        webhook_events=orm_instance.webhook_events,
        case_noun=orm_instance.case_noun,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
