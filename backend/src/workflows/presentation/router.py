"""Routers for the Workflows module."""

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.common.infrastructure.dependencies.workflow_access import (
    require_workflow_action,
    verify_workflow_access,
)
from src.workflows.presentation.endpoints.analysis_run_summary import (
    get_run_summary,
    get_workflow_output_schema,
    resynthesize_run_summary,
    stream_run_summary_events,
    update_workflow_output_schema,
)
from src.workflows.presentation.endpoints.document_processing import (
    get_case_document_extraction_status,
    get_workflow_document,
    start_case_document_extraction,
)
from src.workflows.presentation.endpoints.document_type import (
    delete_document_type,
    get_document_type,
    list_document_types,
    stream_document_type_events,
    suggest_document_type_fields,
    update_document_type,
)
from src.workflows.presentation.endpoints.webhook_destination import (
    create_webhook_destination,
    delete_webhook_destination,
    get_webhook_destination,
    list_webhook_destination_events,
    list_webhook_destinations,
    regenerate_webhook_destination_secret,
    reveal_webhook_destination_secret,
    update_webhook_destination,
)
from src.workflows.presentation.endpoints.workflow import (
    create_workflow,
    create_workflow_from_yaml,
    delete_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
)
from src.workflows.presentation.endpoints.workflow_analysis_run import (
    cancel_workflow_analysis_run,
    create_workflow_analysis_run,
    force_cancel_workflow_analysis_run,
    get_workflow_analysis_run,
    list_workflow_analysis_runs,
    stream_workflow_analysis_run_events,
)
from src.workflows.presentation.endpoints.pipeline_admin import (
    add_workflow_capability,
    create_workflow_pipeline_version,
    get_workflow_pipeline,
    get_workflow_pipeline_version,
    list_workflow_pipeline_versions,
)
from src.workflows.presentation.endpoints.workflow_duplicate import duplicate_workflow
from src.workflows.presentation.endpoints.workflow_import_export import (
    export_workflow_bundle,
    import_workflow_bundle,
    preview_workflow_bundle_import,
)
from src.workflows.presentation.endpoints.workflow_templates import (
    workflow_templates_router,
)
from src.workflows.presentation.endpoints.workflow_case import (
    create_case,
    delete_case,
    get_case,
    get_case_completeness,
    list_cases,
    ready_case,
    update_case,
)
from src.workflows.presentation.endpoints.workflow_case_fields import (
    add_case_comment,
    patch_case_document_fields,
)
from src.workflows.presentation.endpoints.workflow_document import (
    create_case_document,
    create_workflow_document,
    delete_case_document,
    delete_workflow_document,
    list_case_documents,
    update_case_document,
    update_workflow_document,
)
from src.workflows.presentation.endpoints.workflow_processing_job_events import (
    stream_processing_job_events,
)
from src.workflows.presentation.endpoints.workflow_processing_jobs import (
    create_processing_job,
    delete_processing_job,
    get_processing_job_phases,
    list_processing_jobs,
    re_extract_case_processing_jobs,
    retry_processing_job,
)
from src.workflows.presentation.endpoints.workflow_tools import (
    create_workflow_tool,
    delete_workflow_tool,
    list_workflow_tools,
)
from src.workflows.presentation.endpoints.workflow_document_type import (
    create_workflow_document_type,
    delete_workflow_document_type,
    list_workflow_document_types,
)
from src.workflows.presentation.endpoints.workflow_permission import (
    add_workflow_member,
    get_workflow_permissions,
    list_assignable_users,
    remove_workflow_member,
    update_workflow_access_type,
    update_workflow_member_role,
)
from src.workflows.presentation.endpoints.workflow_rule import (
    create_rule,
    delete_rule,
    get_compiling_state,
    get_rule,
    list_rules,
    reorder_rules,
    stream_workflow_rule_events,
    update_rule,
)
from src.workflows.presentation.endpoints.workflow_rule_compilation import (
    list_compilations,
    recompile_rule,
)
from src.workflows.presentation.endpoints.workflow_rule_import_export import (
    export_workflow_rules,
    import_workflow_rules,
    preview_workflow_rules_import,
)
from src.workflows.presentation.endpoints.workflow_rule_kinds import (
    list_workflow_rule_kinds,
)
from src.workflows.presentation.endpoints.workflow_rule_result import (
    list_run_results,
)
from src.workflows.presentation.endpoints.workflow_webhooks import (
    list_workflow_events,
    regenerate_workflow_webhook_secret,
    replay_workflow_event,
)

# =============================================================================
# Workflows router  (prefix: /workflows)
# =============================================================================
workflows_router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
    dependencies=[Depends(verify_workflow_access)],
)

# --- Workflows ---------------------------------------------------------------
workflows_router.add_api_route("", list_workflows, methods=["GET"], summary="List workflows")
workflows_router.add_api_route("", create_workflow, methods=["POST"], summary="Create workflow")
workflows_router.add_api_route(
    "/import-yaml",
    create_workflow_from_yaml,
    methods=["POST"],
    summary="Create a workflow from a YAML bundle template",
)
workflows_router.add_api_route("/{workflow_id}", get_workflow, methods=["GET"], summary="Get workflow")
workflows_router.add_api_route(
    "/{workflow_id}",
    update_workflow,
    methods=["PUT"],
    summary="Update workflow",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}",
    delete_workflow,
    methods=["DELETE"],
    summary="Delete workflow",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/duplicate",
    duplicate_workflow,
    methods=["POST"],
    summary="Duplicate workflow (deep-copy: doctypes + rules + pipeline + KB refs)",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Pipeline (ADR 0002 · owned 1:1 by the workflow) ------------------------
workflows_router.add_api_route(
    "/{workflow_id}/pipeline",
    get_workflow_pipeline,
    methods=["GET"],
    summary="Get the workflow's own pipeline (container + active version pointer)",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/pipeline/versions",
    list_workflow_pipeline_versions,
    methods=["GET"],
    summary="List the workflow pipeline's sealed versions, newest first (E6 · editor)",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/pipeline/versions/{version}",
    get_workflow_pipeline_version,
    methods=["GET"],
    summary="Get a sealed pipeline version recipe",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/pipeline/versions",
    create_workflow_pipeline_version,
    methods=["POST"],
    summary="Publish a pipeline version (append + advance current_version; ?validate_only=)",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/pipeline/capabilities",
    add_workflow_capability,
    methods=["POST"],
    summary="Wizard: add a capability (insert phases + policy scaffolds, publish v+1) (E7·F3)",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Output schema / synthesis configuration --------------------------------
workflows_router.add_api_route(
    "/{workflow_id}/output-schema",
    get_workflow_output_schema,
    methods=["GET"],
    summary="Get workflow synthesis configuration",
)
workflows_router.add_api_route(
    "/{workflow_id}/output-schema",
    update_workflow_output_schema,
    methods=["PUT"],
    summary="Update workflow synthesis configuration (schema/template/toggle)",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Permissions (access type + explicit members) ---------------------------
workflows_router.add_api_route(
    "/{workflow_id}/permissions",
    get_workflow_permissions,
    methods=["GET"],
    summary="Get workflow permissions (access type + members)",
)
workflows_router.add_api_route(
    "/{workflow_id}/permissions/access-type",
    update_workflow_access_type,
    methods=["PUT"],
    summary="Set workflow access type (organization/private)",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/permissions/assignable-users",
    list_assignable_users,
    methods=["GET"],
    summary="List tenant members that can be added to the workflow",
)
workflows_router.add_api_route(
    "/{workflow_id}/permissions/members",
    add_workflow_member,
    methods=["POST"],
    summary="Add a member to the workflow",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/permissions/members/{user_id}",
    update_workflow_member_role,
    methods=["PATCH"],
    summary="Update a workflow member's role",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/permissions/members/{user_id}",
    remove_workflow_member,
    methods=["DELETE"],
    summary="Remove a member from the workflow",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Webhooks (config secret + delivery log + replay; spec §4.9/§10) --------
workflows_router.add_api_route(
    "/{workflow_id}/webhook-secret",
    regenerate_workflow_webhook_secret,
    methods=["POST"],
    summary="Regenerate workflow webhook secret",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/events",
    list_workflow_events,
    methods=["GET"],
    summary="List workflow webhook events (delivery log)",
)
workflows_router.add_api_route(
    "/{workflow_id}/events/{event_id}/replay",
    replay_workflow_event,
    methods=["POST"],
    summary="Replay a workflow webhook event delivery",
)

# --- Webhook destinations (multiple per workflow; spec connections §4.3) -----
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations",
    list_webhook_destinations,
    methods=["GET"],
    summary="List webhook destinations",
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations",
    create_webhook_destination,
    methods=["POST"],
    summary="Create webhook destination",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}",
    get_webhook_destination,
    methods=["GET"],
    summary="Get webhook destination",
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}",
    update_webhook_destination,
    methods=["PUT"],
    summary="Update webhook destination",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}",
    delete_webhook_destination,
    methods=["DELETE"],
    summary="Delete webhook destination",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}/secret",
    reveal_webhook_destination_secret,
    methods=["GET"],
    summary="Reveal webhook destination signing secret",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}/secret",
    regenerate_webhook_destination_secret,
    methods=["POST"],
    summary="Regenerate webhook destination signing secret",
    dependencies=[Depends(require_workflow_action("manage"))],
)
# Tools del workflow (F5, re-scoped 2026-06: 1:1 con el workflow, ADR 0002).
workflows_router.add_api_route(
    "/{workflow_id}/tools",
    list_workflow_tools,
    methods=["GET"],
    summary="List workflow tools",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/tools",
    create_workflow_tool,
    methods=["POST"],
    summary="Create a workflow tool",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/tools/{tool_id}",
    delete_workflow_tool,
    methods=["DELETE"],
    summary="Delete a workflow tool",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/webhook-destinations/{destination_id}/events",
    list_webhook_destination_events,
    methods=["GET"],
    summary="List webhook destination events (delivery log)",
)

# --- Cases -------------------------------------------------------------------
workflows_router.add_api_route("/{workflow_id}/cases", list_cases, methods=["GET"], summary="List cases")
workflows_router.add_api_route("/{workflow_id}/cases", create_case, methods=["POST"], summary="Create case")
workflows_router.add_api_route("/{workflow_id}/cases/{case_id}", get_case, methods=["GET"], summary="Get case")
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/completeness",
    get_case_completeness,
    methods=["GET"],
    summary="Fresh case completeness (E4)",
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/ready",
    ready_case,
    methods=["POST"],
    summary="Mark case ready (E4; 409 case.not_complete unless force)",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}",
    update_case,
    methods=["PUT"],
    summary="Update case",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}",
    delete_case,
    methods=["DELETE"],
    summary="Delete case",
    dependencies=[Depends(require_workflow_action("operate"))],
)

# --- Inspection Bench: verificación por campo + comentarios (E5 · §4) --------
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents/{document_id}/fields",
    patch_case_document_fields,
    methods=["PATCH"],
    summary="Correct/accept extracted fields (E5; 423 case.locked, 503 signal)",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/comments",
    add_case_comment,
    methods=["POST"],
    summary="Add a case comment (case_event comment.added)",
    dependencies=[Depends(require_workflow_action("operate"))],
)

# --- Workflow Documents (CRUD) -----------------------------------------------
workflows_router.add_api_route(
    "/{workflow_id}/documents",
    create_workflow_document,
    methods=["POST"],
    summary="Create workflow document",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/documents/{document_id}",
    update_workflow_document,
    methods=["PUT"],
    summary="Update workflow document",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/documents/{document_id}",
    delete_workflow_document,
    methods=["DELETE"],
    summary="Delete workflow document",
    dependencies=[Depends(require_workflow_action("operate"))],
)

# --- Case Documents ----------------------------------------------------------
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents",
    list_case_documents,
    methods=["GET"],
    summary="List case documents",
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents",
    create_case_document,
    methods=["POST"],
    summary="Create case document",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents/{document_id}",
    update_case_document,
    methods=["PUT"],
    summary="Update case document",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents/{document_id}",
    delete_case_document,
    methods=["DELETE"],
    summary="Delete case document",
    dependencies=[Depends(require_workflow_action("operate"))],
)

# --- Workflow Document Types -------------------------------------------------
workflows_router.add_api_route(
    "/{workflow_id}/document-types",
    list_workflow_document_types,
    methods=["GET"],
    summary="List workflow document types",
)
workflows_router.add_api_route(
    "/{workflow_id}/document-types",
    create_workflow_document_type,
    methods=["POST"],
    summary="Create and associate document type to workflow",
)
workflows_router.add_api_route(
    "/{workflow_id}/document-types/{document_type_id}",
    delete_workflow_document_type,
    methods=["DELETE"],
    summary="Delete document type from workflow",
)

# --- Workflow Rules (nested under workflow, spec §11) -----------------------
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules",
    list_rules,
    methods=["GET"],
    summary="List workflow rules",
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules",
    create_rule,
    methods=["POST"],
    summary="Create workflow rule",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/reorder",
    reorder_rules,
    methods=["POST"],
    summary="Reorder workflow rules",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/events",
    stream_workflow_rule_events,
    methods=["GET"],
    summary="SSE stream of workflow rule events",
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/compiling-state",
    get_compiling_state,
    methods=["GET"],
    summary="Rule ids whose compilation is currently running",
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/export",
    export_workflow_rules,
    methods=["GET"],
    summary="Export workflow rules as a portable JSON envelope",
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/import/preview",
    preview_workflow_rules_import,
    methods=["POST"],
    summary="Preview the result of importing rules (dry run)",
)
workflows_router.add_api_route(
    "/{workflow_id}/workflow-rules/import",
    import_workflow_rules,
    methods=["POST"],
    summary="Import rules using the chosen conflict strategy",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Workflow bundle export/import (doc-types + pipeline + rules; E6 · W4) ----
workflows_router.add_api_route(
    "/{workflow_id}/export",
    export_workflow_bundle,
    methods=["GET"],
    summary="Export the workflow as a git-able bundle envelope",
)
workflows_router.add_api_route(
    "/{workflow_id}/import/preview",
    preview_workflow_bundle_import,
    methods=["POST"],
    summary="Preview a workflow bundle import (dry run)",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/import",
    import_workflow_bundle,
    methods=["POST"],
    summary="Import a workflow bundle (doc-types → pipeline → rules)",
    dependencies=[Depends(require_workflow_action("manage"))],
)

# --- Workflow Analysis Runs (per-case) ---------------------------------------
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/workflow-analysis-runs",
    create_workflow_analysis_run,
    methods=["POST"],
    summary="Trigger an analysis run on a case",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/workflow-analysis-runs",
    list_workflow_analysis_runs,
    methods=["GET"],
    summary="List analysis runs for a case",
)


# =============================================================================
# Standalone Workflow Rules router  (prefix: /workflow-rules)
# =============================================================================
workflow_rules_router = APIRouter(prefix="/workflow-rules", tags=["Workflow Rules"])

workflow_rules_router.add_api_route(
    "/kinds",
    list_workflow_rule_kinds,
    methods=["GET"],
    summary="List registered workflow rule kinds + their JSON Schemas",
)
workflow_rules_router.add_api_route(
    "/{rule_id}",
    get_rule,
    methods=["GET"],
    summary="Get workflow rule",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflow_rules_router.add_api_route(
    "/{rule_id}",
    update_rule,
    methods=["PUT"],
    summary="Update workflow rule",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflow_rules_router.add_api_route(
    "/{rule_id}",
    delete_rule,
    methods=["DELETE"],
    summary="Delete workflow rule",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflow_rules_router.add_api_route(
    "/{rule_id}/recompile",
    recompile_rule,
    methods=["POST"],
    summary="Force a fresh compilation for a rule",
    dependencies=[Depends(require_workflow_action("manage"))],
)
workflow_rules_router.add_api_route(
    "/{rule_id}/compilations",
    list_compilations,
    methods=["GET"],
    summary="List compilation history for a rule",
    dependencies=[Depends(require_workflow_action("view"))],
)


# =============================================================================
# Workflow Analysis Runs router  (prefix: /workflow-analysis-runs)
# =============================================================================
# NOTE: este router NO está bajo ``/workflows/{workflow_id}`` ⇒ sin
# ``verify_workflow_access`` a nivel router. ``require_workflow_action`` resuelve
# el workflow desde ``run_id`` (lookup tenant-scoped) y valida el binding
# workflow↔run + el rol efectivo, cerrando la fuga cross-workflow.
workflow_analysis_runs_router = APIRouter(prefix="/workflow-analysis-runs", tags=["Workflow Analysis Runs"])

workflow_analysis_runs_router.add_api_route(
    "/{run_id}",
    get_workflow_analysis_run,
    methods=["GET"],
    summary="Get workflow analysis run",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/cancel",
    cancel_workflow_analysis_run,
    methods=["POST"],
    summary="Cancel an in-flight analysis run",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/force-cancel",
    force_cancel_workflow_analysis_run,
    methods=["POST"],
    summary="Force-cancel a run stuck in CANCELING (bypasses Temporal)",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/events",
    stream_workflow_analysis_run_events,
    methods=["GET"],
    summary="SSE stream of analysis run events",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/workflow-rule-results",
    list_run_results,
    methods=["GET"],
    summary="List workflow rule results for the run",
    dependencies=[Depends(require_workflow_action("view"))],
)

# --- Run Summary (synthesis spec) -------------------------------------------
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/summary",
    get_run_summary,
    methods=["GET"],
    summary="Get the consolidated summary for a run",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/summary/resynthesize",
    resynthesize_run_summary,
    methods=["POST"],
    summary="Re-run the LLM synthesizer for an existing summary",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflow_analysis_runs_router.add_api_route(
    "/{run_id}/summary/events",
    stream_run_summary_events,
    methods=["GET"],
    summary="SSE stream of summary verdict + narrative events",
    dependencies=[Depends(require_workflow_action("view"))],
)


# =============================================================================
# Document Types router  (prefix: /document-types)
# =============================================================================
document_types_router = APIRouter(prefix="/document-types", tags=["Document Types"])

document_types_router.add_api_route("", list_document_types, methods=["GET"], summary="List document types")
document_types_router.add_api_route(
    "/{document_type_id}", get_document_type, methods=["GET"], summary="Get document type"
)
document_types_router.add_api_route(
    "/{document_type_id}", update_document_type, methods=["PUT"], summary="Update document type"
)
document_types_router.add_api_route(
    "/{document_type_id}", delete_document_type, methods=["DELETE"], summary="Delete document type"
)
document_types_router.add_api_route(
    "/{document_type_id}/suggest-fields",
    suggest_document_type_fields,
    methods=["POST"],
    summary="Suggest fields from sample document",
)
document_types_router.add_api_route(
    "/{document_type_id}/events",
    stream_document_type_events,
    methods=["GET"],
    summary="SSE stream of document type events",
    response_class=EventSourceResponse,
)


# =============================================================================
# Workflow Documents router  (prefix: /workflow-documents)
# =============================================================================
workflow_document_router = APIRouter(
    prefix="/workflow-documents",
    tags=["Workflow Documents"],
)

workflow_document_router.add_api_route(
    "/{document_id}",
    get_workflow_document,
    methods=["GET"],
    summary="Get a single workflow document by id",
)


# =============================================================================
# Case Document Extraction router  (prefix: /workflows, Temporal-driven + SSE)
# =============================================================================
case_extraction_router = APIRouter(
    prefix="/workflows",
    tags=["Case Document Extraction"],
    dependencies=[Depends(verify_workflow_access)],
)

case_extraction_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents/{document_id}/extract",
    start_case_document_extraction,
    methods=["POST"],
    summary="Start extraction workflow for a case document",
    dependencies=[Depends(require_workflow_action("operate"))],
)
case_extraction_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/documents/{document_id}/extract/status",
    get_case_document_extraction_status,
    methods=["GET"],
    summary="Get extraction workflow status for a case document",
)

# --- Bulk file extraction (unified for STANDARD + ANALYSIS) -----------------
workflows_router.add_api_route(
    "/{workflow_id}/jobs",
    list_processing_jobs,
    methods=["GET"],
    summary="List workflow document sets (with extracted documents)",
)
workflows_router.add_api_route(
    "/{workflow_id}/jobs",
    create_processing_job,
    methods=["POST"],
    summary="Dispatch bulk extraction of a file",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/jobs/events",
    stream_processing_job_events,
    methods=["GET"],
    summary="SSE stream of ProcessingJobEvents",
)
workflows_router.add_api_route(
    "/{workflow_id}/jobs/{processing_job_id}",
    delete_processing_job,
    methods=["DELETE"],
    summary="Delete a workflow document set",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/jobs/{processing_job_id}/retry",
    retry_processing_job,
    methods=["POST"],
    summary="Re-dispatch a FAILED processing job (trigger=RETRY)",
    dependencies=[Depends(require_workflow_action("operate"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/jobs/{processing_job_id}/phases",
    get_processing_job_phases,
    methods=["GET"],
    summary="Per-phase execution timeline of a processing job (Ejecuciones)",
    dependencies=[Depends(require_workflow_action("view"))],
)
workflows_router.add_api_route(
    "/{workflow_id}/cases/{case_id}/jobs/re-extract",
    re_extract_case_processing_jobs,
    methods=["POST"],
    summary="Re-run extract_fields + validate_extraction for every set in the case",
    dependencies=[Depends(require_workflow_action("operate"))],
)
