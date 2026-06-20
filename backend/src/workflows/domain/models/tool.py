"""Domain models for the Tool registry (F5 · A3, workflow-scoped desde 2026-06).

A ``ToolDefinition`` belongs to ONE workflow (1:1 ownership, mismo patrón que
pipeline · ADR 0002): what to call and how to shape it. The secret lives once on
the referenced org-level ``ConnectionAccount`` (capability ``LOOKUP``), so
rotation / allowlist / auditing stay centralised exactly as for
``SEND``/``RECEIVE``. The deterministic connector (infra) executes the call; the
LLM never sees raw HTTP. Reuse across workflows = «Duplicar workflow».
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.tools import ToolCallStatus, ToolTransport


class ToolDefinition(BaseModel):
    uuid: UUID
    tenant_id: UUID
    # Owning workflow (1:1 scope): the tool only resolves inside this workflow.
    workflow_id: UUID
    # Slug used by the enrich phase / ``#tool.<name>`` token to resolve the tool.
    name: str
    display_name: str
    description: str | None = None
    transport: ToolTransport = ToolTransport.HTTP
    # The LOOKUP ConnectionAccount that holds the secret + host allowlist. None
    # para script tools (PYTHON/JS): corren en sandbox y no hacen HTTP (F5).
    connection_account_id: UUID | None = None
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    # Non-secret transport config: {base_url, path, method, headers, query, ...}.
    config: dict = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ToolResult(BaseModel):
    """The connector's verdict for one call. ``data`` is ``None`` when degraded."""

    status: ToolCallStatus
    data: dict | None = None
    error: str | None = None
    # Request/response/timing snapshot for the per-case audit trail (B1).
    snapshot: dict[str, Any] = Field(default_factory=dict)

    @property
    def degraded(self) -> bool:
        return self.status == ToolCallStatus.DEGRADED
