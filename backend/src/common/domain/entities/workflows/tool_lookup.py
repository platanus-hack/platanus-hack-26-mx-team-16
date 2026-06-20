"""Activity I/O for the deterministic Tool lookup (F5 · extendido en E3)."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.common.domain.enums.tools import ToolCallStatus

# Error type raised (non-retryable) when the enrich phase/tool is misconfigured
# (args fail input_schema, unknown token, broken path template). Shared between
# the activity (raises) and the phase handler (re-raises) — NEVER the on_failure
# path: a config error must fail loudly instead of opening review tasks.
ENRICH_CONFIG_ERROR_TYPE = "pipeline.enrich_config_error"


class ToolLookupInput(BaseModel):
    tenant_id: UUID
    tool_name: str
    args: dict = Field(default_factory=dict)
    case_id: UUID | None = None
    # E3: needed to resolve `@slug` refs (case docs) and to persist the result
    # as a virtual TOOL document in the workflow's doc-type catalogue.
    workflow_id: UUID | None = None
    # Doc type slug for the virtual document; falls back to the tool name.
    output_doc_type_slug: str | None = None
    # Persist the (partial) payload even when the call degraded (default off).
    persist_degraded: bool = False


class ToolLookupOutput(BaseModel):
    status: ToolCallStatus
    data: dict | None = None
    error: str | None = None
    # E3: uuid of the persisted virtual WorkflowDocument (source=TOOL), if any.
    document_id: UUID | None = None
