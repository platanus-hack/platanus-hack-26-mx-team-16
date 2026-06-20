from __future__ import annotations

from dataclasses import dataclass, field

from src.scans.domain.enums.tool_id import ToolId


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    """A concrete tool+flags invocation the worker can hand to the OWASP agent.

    Frozen/hashable so it is comparable by value/equality in tests (the byte-
    identity guard of the gov/basic legal floor against the canonical unified
    Nuclei tag set of 01 §3 / 02 §4). It carries NO timeout: per-tool timeouts and
    execution mechanics are owned by 04-scanning-engine (§4.2); here we only name
    the tool and its (logical) flags.

    The ``flags`` are *declarative policy*, not the literal argv executed at run
    time: 04 appends operational flags (e.g. ``-duc``) on each run, so these flags
    are intentionally NOT byte-equal to what 04 ultimately executes.
    """

    tool: ToolId
    flags: tuple[str, ...] = field(default=())
