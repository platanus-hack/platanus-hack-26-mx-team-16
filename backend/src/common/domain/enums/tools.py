"""Enums for the Tool registry + deterministic connector (F5 · A2 · A3 · B1)."""

from src.common.domain.enums.base_enum import BaseEnum


class ToolTransport(BaseEnum):
    HTTP = "HTTP"  # generic HTTP/JSON API (judges API, policy form, drug KB…)
    # phases-config · F5 (D-D): script tools ejecutados en un runner sandbox
    # in-cluster (gVisor/Firecracker), sin red salvo allowlist, sin secretos.
    # El código vive en tool_definitions.config ({runtime, entrypoint, code|code_ref}).
    PYTHON = "PYTHON"
    JS = "JS"


class ToolCallStatus(BaseEnum):
    """Outcome of one Tool invocation. ``DEGRADED`` is the B1 fallback when the
    upstream service is unreachable — the run continues, the LLM never sees a raw
    401/429/5xx."""

    OK = "OK"
    DEGRADED = "DEGRADED"
