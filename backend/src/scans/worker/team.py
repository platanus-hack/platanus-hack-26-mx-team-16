"""Agno Team assembly — Opus coordinator + 2 Sonnet members (spec §1, plan §5).

``build_team`` wires the per-scan closed-over tool wrappers into the two Sonnet
members and a ``Team`` in ``coordinate`` mode led by Opus. The coordinator
delegates ``{url, level}``; the members pick their tools and accumulate
``Finding[]`` into the shared ``session_state`` (the LLM never carries the data).

``agno`` is **lazy-imported inside** :func:`build_team` so this module — and the
``WorkerFlow`` / ``RunScanHandler`` that import it — load cleanly on CI without
``agno``/``anthropic`` installed. The actual Team is only constructed when a scan
runs (where the deps are present), or with injected fakes in tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.scanning import CancelToken
from src.scans.domain.enums.tool_id import ToolId
from src.scans.domain.value_objects.tool_invocation import ToolInvocation
from src.scans.worker.events import ScanEventEmitter
from src.scans.worker.tools.agentic import AgenticProbe, make_agentic_tool
from src.scans.worker.tools.owasp import build_owasp_tools

TEAM_COORDINATE_MODE = "coordinate"

_TEAM_INSTRUCTIONS = (
    "Coordina ambos subagentes EN PARALELO sobre el objetivo al nivel indicado. "
    "El merge, la deduplicación y el scoring son Python determinista, NO tarea "
    "del LLM. Tú solo coordinas la ejecución de los subagentes."
)


@dataclass
class TeamDeps:
    """Everything the Team needs that must NOT come from the LLM (per-scan)."""

    target: str
    level: str
    is_gov: bool
    cancel: CancelToken
    emit: ScanEventEmitter
    host_shared_dir: str
    invocations: list[ToolInvocation] = field(default_factory=list)
    coverage: dict[str, str] = field(default_factory=dict)
    agentic_probe: AgenticProbe | None = None  # 03 injects the real probe here


def build_team(
    deps: TeamDeps,
    *,
    opus_model: Any | None = None,
    sonnet_model: Any | None = None,
) -> Any:
    """Build the Agno ``Team`` (Opus coordinator + OWASP/agentic Sonnet members).

    ``opus_model`` / ``sonnet_model`` are injectable for tests (fakes that don't
    call the API). When None, the ``ModelFactory`` builds the real models. Imports
    of ``agno`` happen lazily here and in ``members.py``.
    """
    from agno.team import Team  # noqa: PLC0415 - lazy import

    from src.scans.worker.members import build_agentic_agent, build_owasp_agent
    from src.scans.worker.models import ModelFactory

    owasp_tools: list[Callable[..., Any]] = build_owasp_tools(
        deps.invocations,
        target=deps.target,
        host_shared_dir=deps.host_shared_dir,
        cancel=deps.cancel,
        emit=deps.emit,
        coverage=deps.coverage,
    )
    agentic_tools: list[Callable[..., Any]] = [
        make_agentic_tool(
            target=deps.target,
            host_shared_dir=deps.host_shared_dir,
            cancel=deps.cancel,
            emit=deps.emit,
            level=deps.level,
            is_gov=deps.is_gov,
            probe=deps.agentic_probe,
        )
    ]

    owasp_agent = build_owasp_agent(tools=owasp_tools, model=sonnet_model)
    agentic_agent = build_agentic_agent(tools=agentic_tools, model=sonnet_model)

    opus = opus_model if opus_model is not None else ModelFactory().opus()
    return Team(
        mode=TEAM_COORDINATE_MODE,
        model=opus,
        members=[owasp_agent, agentic_agent],
        instructions=_TEAM_INSTRUCTIONS,
    )


def team_prompt(target: str, level: str) -> str:
    """The delegation prompt handed to the coordinator (spec §5)."""
    return (
        f"Realiza un pentest del objetivo {target} a nivel '{level}'. "
        "Delega en el subagente OWASP la batería web y en el subagente agéntico "
        "la superficie de IA. Cada subagente ejecuta sus herramientas."
    )


# Re-export ToolId for callers that build invocations without importing the enum
# module path directly (kept minimal; the value objects own the canonical types).
__all__ = ["TeamDeps", "ToolId", "build_team", "team_prompt"]
