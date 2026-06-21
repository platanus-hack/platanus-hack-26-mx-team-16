"""Agno Team members — OWASP + agentic Sonnet subagents (spec §1, plan §5).

Each member is a Sonnet ``Agent`` whose job is to **decide which tools to run**
for the level — NOT to parse or reconstruct findings (the tools already return
``Finding[]`` into ``session_state``). Neither member uses ``output_schema`` /
``response_model`` (tools + structured output is a known Agno/Claude bug zone,
spec §2.1).

``agno`` is **lazy-imported inside the builders** so this module imports cleanly
on CI without it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

OWASP_AGENT_NAME = "OWASP Scanner"
AGENTIC_AGENT_NAME = "Agentic Surface Auditor"

_OWASP_INSTRUCTIONS = (
    "Decide SOLO qué herramientas correr según el nivel del escaneo. "
    "NO redactes ni reconstruyas hallazgos: las herramientas ya devuelven "
    "Finding[] parseado y lo acumulan en el contexto. Ejecuta las herramientas "
    "apropiadas para el objetivo y reporta brevemente el avance."
)

_AGENTIC_INSTRUCTIONS = (
    "Detecta chatbots/entradas de IA (superficie agéntica) y pruébalos según el "
    "nivel, mapeando a OWASP-LLM Top 10. Las herramientas devuelven Finding[] + "
    "inventario ya parseados; no los reconstruyas."
)


def build_owasp_agent(
    *,
    tools: list[Callable[..., Any]],
    model: Any | None = None,
) -> Any:
    """Build the OWASP Sonnet member with its closed-over tool wrappers.

    ``tools`` are the closures from ``build_owasp_tools`` (already bound to the
    per-scan target/cancel/emit). ``model`` is injectable for tests; when None the
    ``ModelFactory`` builds the real Sonnet model (lazy anthropic/agno).
    """
    from agno.agent import Agent  # noqa: PLC0415 - lazy import

    from src.scans.worker.models import ModelFactory

    sonnet = model if model is not None else ModelFactory().sonnet()
    return Agent(
        name=OWASP_AGENT_NAME,
        model=sonnet,
        tools=tools,
        instructions=_OWASP_INSTRUCTIONS,
    )


def build_agentic_agent(
    *,
    tools: list[Callable[..., Any]],
    model: Any | None = None,
) -> Any:
    """Build the agentic Sonnet member (spec §1).

    ``tools`` is the agentic probe wrapper (``make_agentic_tool``), which defaults
    to the real 03 detection/probe (``DEFAULT_AGENTIC_PROBE``); a caller may inject
    a fake probe for tests. Same no-``output_schema`` rule.
    """
    from agno.agent import Agent  # noqa: PLC0415 - lazy import

    from src.scans.worker.models import ModelFactory

    sonnet = model if model is not None else ModelFactory().sonnet()
    return Agent(
        name=AGENTIC_AGENT_NAME,
        model=sonnet,
        tools=tools,
        instructions=_AGENTIC_INSTRUCTIONS,
    )
