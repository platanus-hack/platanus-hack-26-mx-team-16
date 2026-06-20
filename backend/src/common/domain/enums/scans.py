"""Single source of truth for the pentest-engine enums (06-data-model §2.1).

These enums back the scan-engine ORM columns and the ``Literal[...]`` values of
the frozen Pydantic contracts in ``src/scans/domain/contracts/finding.py`` and
``events.py``. The string values match the spec DDL (spec §2) verbatim and are
persisted as ``String`` columns (repo convention, see ``TenantStatus``); the
``Literal[...]`` in the contracts intentionally mirror these values rather than
import the enum, to keep the contracts self-contained and serializable.

Downstream features (01-legal-ethics, 02-attack-levels, 03-agentic-surface,
04-scanning-engine, 05-agent-team, 07-scoring, 08-ranking-watchlists,
10-realtime-live-view, 12-api) **re-export** these enums; they do not duplicate
them.
"""

from src.common.domain.enums.base_enum import BaseEnum


class ScanLevel(BaseEnum):
    """Requested attack level (02-attack-levels)."""

    BASICO = "basico"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"


class ScanStatus(BaseEnum):
    """Scan state machine (spec §3.2).

    ``running`` doubles as the idempotency lock (spec §4). ``partial`` is a
    first-class state: the scan finished but >=1 base scanner was missing, so the
    scoring caps the grade at C (see 07-scoring).
    """

    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanVisibility(BaseEnum):
    """Access-control primitive (spec §3.2). Gov basic/passive = public;
    intermediate/advanced or any owned site = private."""

    PUBLIC = "public"
    PRIVATE = "private"


class AgenticStatus(BaseEnum):
    """Three-state agentic outcome — not a binary N/A (spec §5.2, 07-scoring §9.1)."""

    NO_SURFACE = "no_surface"
    DETECTED_NOT_TESTED = "detected_not_tested"
    TESTED = "tested"


class FindingSource(BaseEnum):
    """Splits Web (OWASP) vs Agentic sub-scores (spec §3.3)."""

    OWASP = "owasp"
    AGENTIC = "agentic"


class FindingSeverity(BaseEnum):
    """Severity scale (spec §5.1). ``info`` has weight 0 and never affects score."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingConfidence(BaseEnum):
    """Confidence — critical for false-positive triage (spec §3.3). Weights penalty."""

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class FindingStatus(BaseEnum):
    """Site-level finding lifecycle for temporal monitoring (spec §3.3)."""

    OPEN = "open"
    FIXED = "fixed"
    ACCEPTED = "accepted"


class FindingCategory(BaseEnum):
    """OWASP ``A01..A10`` / OWASP-LLM ``LLM01..LLM10`` taxonomy (spec §3.3).

    The concrete value is assigned from a curated static dict/YAML
    (template-id/probe -> category), **never** by the LLM. Enumerated here so
    other features share a single canonical taxonomy; the ``Finding`` contract
    keeps ``category: str`` open to avoid coupling the parsers to this enum.
    """

    A01 = "A01"  # Broken Access Control
    A02 = "A02"  # Cryptographic Failures
    A03 = "A03"  # Injection
    A04 = "A04"  # Insecure Design
    A05 = "A05"  # Security Misconfiguration
    A06 = "A06"  # Vulnerable and Outdated Components
    A07 = "A07"  # Identification and Authentication Failures
    A08 = "A08"  # Software and Data Integrity Failures
    A09 = "A09"  # Security Logging and Monitoring Failures
    A10 = "A10"  # Server-Side Request Forgery
    LLM01 = "LLM01"  # Prompt Injection
    LLM02 = "LLM02"  # Sensitive Information Disclosure
    LLM03 = "LLM03"  # Supply Chain
    LLM04 = "LLM04"  # Data and Model Poisoning
    LLM05 = "LLM05"  # Improper Output Handling
    LLM06 = "LLM06"  # Excessive Agency
    LLM07 = "LLM07"  # System Prompt Leakage
    LLM08 = "LLM08"  # Vector and Embedding Weaknesses
    LLM09 = "LLM09"  # Misinformation
    LLM10 = "LLM10"  # Unbounded Consumption


class AgenticType(BaseEnum):
    """Detected agentic surface kind (spec §3.4)."""

    CHATBOT = "chatbot"
    PROMPT_INPUT = "prompt_input"
    SEARCH_AI = "search_ai"


class ScanEventType(BaseEnum):
    """Discriminant for ``scan_events`` / the ``ScanEvent`` contract (spec §3.5)."""

    AGENT_STATUS = "agent_status"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    FINDING = "finding"
    PHASE = "phase"
    SCORE = "score"
    DONE = "done"
    ERROR = "error"


class AlertChannel(BaseEnum):
    """Notification channel for the monitoring alert log (spec §3.6)."""

    EMAIL = "email"
    SLACK = "slack"
