import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from src.common.database.config import get_database_config
from src.common.infrastructure.event_publisher import RedisEventPublisher
from src.common.infrastructure.helpers.logger import get_logger
from src.common.infrastructure.temporal.activities.create_process_record import (
    CreateProcessRecordActivity,
)
from src.common.infrastructure.temporal.activities.publish_processing_job_event import (
    PublishProcessingJobEventActivity,
)
from src.common.settings import settings
from src.workflows.application.document_processing.orphan_sweeper import (
    OrphanedJobSweeper,
)
from src.workflows.domain.constants import TEMPORAL_HOST, TASK_QUEUE
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.infrastructure.services.rules.bootstrap import (
    build_synthesizer_agent,
    register_default_kinds,
)
from src.workflows.presentation.workflows import (
    PipelineInterpreterWorkflow,
    WorkflowAnalysisRunWorkflow,
)
from src.workflows.presentation.workflows.activities.case_phase_activities import (
    BuildCaseOutputActivity,
    CaseAnalysisRunActivities,
    DispatchCaseEventActivity,
)
from src.workflows.presentation.workflows.activities.case_runtime_activities import (
    CaseRuntimeActivities,
    SignalCaseWorkflowActivity,
)
from src.workflows.presentation.workflows.activities.fan_out_cases import (
    CreateChildCasesActivity,
    StartChildCaseRunsActivity,
)
from src.workflows.presentation.workflows.activities.load_pipeline_version import (
    LoadPipelineVersionActivity,
)
from src.workflows.presentation.workflows.activities.transition_case_status import (
    TransitionCaseStatusActivity,
)
from src.workflows.presentation.workflows.activities.create_human_task import (
    CreateHumanTaskActivity,
)
from src.workflows.presentation.workflows.activities.tool_lookup import (
    ToolLookupActivity,
)
from src.workflows.presentation.workflows.activities.analysis_run_activities import (
    CompleteAnalysisRunActivity,
    EvaluateRuleCombinationActivity,
    LoadAnalysisRunPlanActivity,
    PublishAnalysisRunEventActivity,
    UpdateAnalysisRunStatusActivity,
)
from src.workflows.presentation.workflows.activities.invoke_lambda import (
    InvokeLambdaActivity,
)
from src.workflows.presentation.workflows.activities.dispatch_processing_job_webhook import (
    DispatchProcessingJobWebhookActivity,
)
from src.workflows.presentation.workflows.activities.mark_document_status import (
    MarkDocumentStatusActivity,
)
from src.workflows.infrastructure.services.assess.agent import build_assess_agent
from src.workflows.presentation.workflows.activities.assess_document import (
    AssessDocumentActivity,
)
from src.workflows.infrastructure.services.webhooks.http_dispatcher import (
    HttpWorkflowWebhookDispatcher,
)
from src.workflows.infrastructure.services.webhooks.summary_dispatcher import (
    WorkflowSummaryWebhookDispatcher,
)
from src.workflows.presentation.workflows.activities.persist_classified_documents import (
    PersistClassifiedDocumentsActivity,
)
from src.workflows.presentation.workflows.activities.persist_document_texts import (
    PersistDocumentTextsActivity,
)
from src.workflows.presentation.workflows.activities.read_s3_json import (
    ReadS3JsonActivity,
)
from src.workflows.presentation.workflows.activities.record_phase_execution import (
    RecordPhaseExecutionActivity,
)
from src.workflows.presentation.workflows.activities.update_processing_job_status import (
    UpdateWorkflowProcessingJobStatusActivity,
)

logger = get_logger(__name__)


async def main() -> None:
    client = await Client.connect(TEMPORAL_HOST, data_converter=pydantic_data_converter)

    db_config = get_database_config()
    session_maker = db_config.session_maker
    assert session_maker is not None

    redis_client = Redis.from_url(settings.redis_url, decode_responses=True, encoding="utf-8")
    event_publisher = RedisEventPublisher(redis=redis_client)

    invoke_lambda_activity = InvokeLambdaActivity()
    read_s3_json_activity = ReadS3JsonActivity()
    publish_event_activity = PublishProcessingJobEventActivity(event_publisher=event_publisher)
    persist_docs_activity = PersistClassifiedDocumentsActivity(
        session_maker=session_maker,
        event_publisher=event_publisher,
    )
    persist_texts_activity = PersistDocumentTextsActivity(session_maker=session_maker)
    update_job_activity = UpdateWorkflowProcessingJobStatusActivity(session_maker=session_maker)
    record_phase_activity = RecordPhaseExecutionActivity(session_maker=session_maker)
    create_process_record_activity = CreateProcessRecordActivity(session_maker=session_maker)
    load_pipeline_version_activity = LoadPipelineVersionActivity(session_maker=session_maker)
    tool_lookup_activity = ToolLookupActivity(session_maker=session_maker)
    create_human_task_activity = CreateHumanTaskActivity(session_maker=session_maker)
    mark_doc_activity = MarkDocumentStatusActivity(
        session_maker=session_maker,
        event_publisher=event_publisher,
    )
    dispatch_webhook_activity = DispatchProcessingJobWebhookActivity(
        session_maker=session_maker,
        dispatcher=HttpWorkflowWebhookDispatcher(),
    )
    # E3: fase assess — capa-2 de confianza por documento.
    assess_document_activity = AssessDocumentActivity(
        session_maker=session_maker,
        assess_agent=build_assess_agent(),
    )

    # Analysis run activities
    register_default_kinds()
    synthesizer_agent = build_synthesizer_agent()
    load_plan_activity = LoadAnalysisRunPlanActivity(session_maker=session_maker)
    evaluate_combination_activity = EvaluateRuleCombinationActivity(session_maker=session_maker)
    update_run_status_activity = UpdateAnalysisRunStatusActivity(session_maker=session_maker)
    publish_run_event_activity = PublishAnalysisRunEventActivity(event_publisher=event_publisher)
    complete_run_activity = CompleteAnalysisRunActivity(
        session_maker=session_maker,
        synthesizer_agent=synthesizer_agent,
        event_publisher=event_publisher,
        # W1: emit analysis_run.completed to subscribed workflow_destinations.
        webhook_dispatcher=WorkflowSummaryWebhookDispatcher(session_maker=session_maker),
    )

    # E2: fases case-scope del intérprete (analyze/output/deliver)
    case_run_activities = CaseAnalysisRunActivities(session_maker=session_maker)
    build_case_output_activity = BuildCaseOutputActivity(
        session_maker=session_maker,
        synthesizer_agent=synthesizer_agent,
    )
    dispatch_case_event_activity = DispatchCaseEventActivity(session_maker=session_maker)
    # E4: choke point de la máquina de estados del caso (status + case_event).
    transition_case_status_activity = TransitionCaseStatusActivity(session_maker=session_maker)
    # E4: motor de caso — completitud, gate de activación, pausas ricas, señal.
    case_runtime_activities = CaseRuntimeActivities(session_maker=session_maker)
    signal_case_workflow_activity = SignalCaseWorkflowActivity(temporal_client=client)
    # E5: fan-out a child cases (classify_pages fan_out + finalize batches).
    create_child_cases_activity = CreateChildCasesActivity(session_maker=session_maker)
    start_child_case_runs_activity = StartChildCaseRunsActivity(
        session_maker=session_maker,
        temporal_client=client,
        task_queue=TASK_QUEUE,
    )

    # On-startup reconciliation: any workflow_processing_jobs row left
    # non-terminal by a previous crash gets matched against Temporal and
    # finalized. Wrapped in try/except so a sweeper failure (DB blip,
    # Temporal blip) never blocks the worker from coming up to serve real
    # tasks.
    @asynccontextmanager
    async def make_sweeper_repo():
        # Each reconciliation gets its own session so a flush failure on
        # one document set doesn't poison subsequent iterations.
        async with session_maker() as session:
            try:
                yield SQLWorkflowProcessingJobRepository(session=session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    try:
        await OrphanedJobSweeper(
            repository_factory=make_sweeper_repo,
            temporal_client=client,
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("orphan_sweeper.startup_failed")

    try:
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[
                PipelineInterpreterWorkflow,
                WorkflowAnalysisRunWorkflow,
            ],
            activities=[
                invoke_lambda_activity.invoke_lambda,
                read_s3_json_activity.read_s3_json,
                read_s3_json_activity.read_classified_refs,
                read_s3_json_activity.split_classified_documents,
                publish_event_activity.publish_processing_job_event,
                persist_docs_activity.persist_classified_documents,
                persist_texts_activity.persist_document_texts,
                update_job_activity.update_workflow_processing_job_status,
                record_phase_activity.record_phase_execution,
                mark_doc_activity.mark_document_status,
                assess_document_activity.assess_document,
                dispatch_webhook_activity.dispatch_processing_job_webhook,
                create_process_record_activity.create_process_record,
                load_pipeline_version_activity.load_pipeline_version,
                tool_lookup_activity.tool_lookup,
                create_human_task_activity.create_human_task,
                load_plan_activity.load_analysis_run_plan,
                evaluate_combination_activity.evaluate_rule_combination,
                update_run_status_activity.update_analysis_run_status,
                publish_run_event_activity.publish_analysis_run_event,
                complete_run_activity.complete_analysis_run,
                case_run_activities.create_analysis_run,
                case_run_activities.mark_analysis_run_failed,
                build_case_output_activity.build_case_output,
                dispatch_case_event_activity.dispatch_case_event,
                transition_case_status_activity.transition_case_status,
                case_runtime_activities.resolve_classifier,
                case_runtime_activities.evaluate_case_completeness,
                case_runtime_activities.mark_case_ready,
                case_runtime_activities.append_case_event,
                case_runtime_activities.evaluate_activation_gate,
                case_runtime_activities.open_clarification_task,
                case_runtime_activities.open_approval_task,
                case_runtime_activities.check_blocking_results,
                case_runtime_activities.build_stage_gate_items,
                case_runtime_activities.open_qa_audit_task,
                signal_case_workflow_activity.signal_case_workflow,
                create_child_cases_activity.create_child_cases,
                start_child_case_runs_activity.start_child_case_runs,
            ],
            activity_executor=ThreadPoolExecutor(5),
        ):
            logger.info("worker.started", task_queue=TASK_QUEUE)
            await asyncio.Future()
    finally:
        await redis_client.aclose()
        await db_config.dispose()


if __name__ == "__main__":
    asyncio.run(main())
