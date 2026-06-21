"""``accumulate`` — push parsed ``Finding[]`` into the shared session state.

This is the **only** way ``Finding`` objects leave a tool-function (spec §2.1,
plan §2). The tool parses raw stdout into ``Finding[]`` and calls ``accumulate``,
which appends to ``session_state["findings"]``; the function then returns a short
string the LLM uses to decide the next step. The findings NEVER travel through an
LLM message / ``response_model`` — that is what keeps the model out of the data
path.

``run_context`` is the Agno ``RunContext`` (it exposes ``.session_state``), but the
helper accepts any object with a ``session_state`` mapping attribute OR a plain
dict, so the same code path is trivially testable without Agno installed.
"""

from __future__ import annotations

from typing import Any

from src.scans.domain.contracts.finding import Finding

FINDINGS_KEY = "findings"
AGENTIC_KEY = "agentic"


def _state_of(run_context_or_state: Any) -> dict[str, Any]:
    """Return the mutable session-state dict from a RunContext or a raw dict."""
    state = getattr(run_context_or_state, "session_state", None)
    if state is None and isinstance(run_context_or_state, dict):
        state = run_context_or_state
    if state is None:
        raise ValueError("accumulate: no session_state on run_context")
    return state


def accumulate(run_context_or_state: Any, findings: list[Finding]) -> None:
    """Append ``findings`` to ``session_state['findings']`` (creating it if absent)."""
    state = _state_of(run_context_or_state)
    bucket = state.setdefault(FINDINGS_KEY, [])
    bucket.extend(findings)


def accumulate_agentic(run_context_or_state: Any, results: list[Any]) -> None:
    """Append ``AgenticResult`` rows to ``session_state['agentic']`` (03 seam)."""
    state = _state_of(run_context_or_state)
    bucket = state.setdefault(AGENTIC_KEY, [])
    bucket.extend(results)
