"""Pure resolver: the single source of truth for which web tools owasp_agent gets.

This function is the ONLY seam consumed by both the passive-scheduler guarantee
(01-legal-ethics) and the `owasp_agent` construction (05-agent-team). It is pure
(no I/O): the hexstrike healthcheck state is passed in as an argument so the
function stays testable. 04-scanning-engine materializes + enforces the result.
"""

from __future__ import annotations

from src.common.domain.enums.scans import ScanLevel  # owned by 06-data-model
from src.scans.application.whitelist.toolset_whitelist import (
    DEMO_PROFILE,
    HEXSTRIKE_INVOCATION,
    TOOLSET_WHITELIST,
)
from src.scans.domain.value_objects.tool_invocation import ToolInvocation


def resolve_toolset(
    is_gov: bool,
    level: ScanLevel,
    *,
    demo: bool = False,
    hexstrike_ok: bool = False,
) -> tuple[ToolInvocation, ...]:
    """Resolve the allow-listed web tool battery for a scan.

    - ``demo=True`` short-circuits and returns ``DEMO_PROFILE``, IGNORING both
      ``level`` and ``is_gov`` (demo is orthogonal to level; demo == localhost).
    - hexstrike is appended ONLY on the advanced level and ONLY when
      ``hexstrike_ok`` (i.e. ``settings.ENABLE_HEXSTRIKE and <healthcheck OK>``).
      Otherwise the advanced level falls back to ZAP full active + Nuclei fuzzing
      + sqlmap. The advanced level NEVER depends on hexstrike to produce findings.
    - Allow-list by construction: anything not in the resolved tuple does not run.

    Returns an ORDERED tuple; 04 may fan it out with ``asyncio.gather``.
    """
    if demo:
        return DEMO_PROFILE

    toolset = TOOLSET_WHITELIST[(is_gov, level)]

    if level is ScanLevel.AVANZADO and hexstrike_ok:
        toolset = toolset + (HEXSTRIKE_INVOCATION,)

    return toolset
