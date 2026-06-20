"""FROZEN contract — ``finding.py`` (06-data-model §5).

One of the 5 non-negotiable hour-0 artifacts. ``Finding`` + ``AgenticResult`` are
the contract shared by P2 (parsers, 04-scanning-engine), P3 (agentic,
03-agentic-surface) and P4 (reporting, 09-reporting). **Do not change after
hour 2** — changing it breaks three carriles at once.

The ``Literal[...]`` values mirror the enums in
``src/common/domain/enums/scans.py`` verbatim. They are intentionally inlined
(not imported) so the contract stays self-contained and trivially serializable,
the same way the boilerplate ``domain/models/user.py`` keeps Pydantic decoupled
from the ORM.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Normative enum aliases derived from the Finding/AgenticResult shapes (spec §5).
# Re-exported for downstream typing without re-deriving the Literal.
Severity = Literal["critical", "high", "medium", "low", "info"]
Confidence = Literal["alta", "media", "baja"]
Source = Literal["owasp", "agentic"]
AgenticStatusLiteral = Literal["no_surface", "detected_not_tested", "tested"]


class Finding(BaseModel):
    """Standard structured output (spec §5.1 / §8).

    Tool-functions PARSE raw scanner output in Python and return ``list[Finding]``
    already built; the Sonnet agents do **not** use ``response_model=list[Finding]``
    (see 04-scanning-engine, 05-agent-team).
    """

    model_config = ConfigDict(extra="forbid")

    source: Source
    tool: str
    category: str  # A01..A10 (OWASP) or LLM01..LLM10 (OWASP-LLM); assigned by a
    # curated static dict/YAML, never by the LLM.
    title: str
    severity: Severity
    cvss: float | None = None
    confidence: Confidence
    description: str
    evidence: dict = Field(default_factory=dict)  # payload, req/resp snippet,
    # screenshot ref (relative URL, never base64).
    affected_url: str | None = None
    endpoint: str | None = None
    param: str | None = None
    impact: str  # business language
    remediation: str
    references: list[str] = Field(default_factory=list)


class AgenticResult(BaseModel):
    """Output of the agentic subagent (spec §5.2) — frozen in finding.py.

    Source of ``scans.agentic_status``. Each probe verdict materializes as a
    ``Finding`` with ``source="agentic"`` and ``evidence = {payload,
    respuesta_cruda, veredicto, reason}``; confidence is ``alta`` when a
    canary/regex fired, ``media`` when it was an LLM judgement.
    """

    model_config = ConfigDict(extra="forbid")

    type: str  # chatbot | prompt_input | search_ai
    vendor: str | None = None  # Intercom, Drift... or None (generic surface)
    location_url: str
    inferred_model: str | None = None  # best-effort; None if "model not exposed"
    agentic_status: AgenticStatusLiteral  # spec §9.1
    findings: list[Finding] = Field(default_factory=list)
