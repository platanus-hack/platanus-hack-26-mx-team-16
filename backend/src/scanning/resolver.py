"""``resolve_tools`` — materialize the 02 whitelist into runnable invocations.

This is NOT where the ``(is_gov, level)`` whitelist is authored — 02 owns that
(``resolve_toolset`` + ``TOOLSET_WHITELIST``). ``resolve_tools`` BUILDS ON
``resolve_toolset``: it calls it, materializes the result into a concrete list the
worker fans out with ``asyncio.gather``, and — for the gov/basic legal floor —
validates the resolved invocations against the 01-owned
``assert_within_passive_profile`` predicate. Allow-list by construction: anything
``resolve_toolset`` does not return literally never runs.

Ownership: 02 owns *which* tools per level; 01 owns the gov passive contract; 04
(here) owns the *materialization + enforcement drop-point* that hands only the
allow-listed tools to ``owasp_agent`` (05).
"""

from __future__ import annotations

from src.common.domain.enums.scans import ScanLevel
from src.common.domain.legal.passive_profile import (
    ToolInvocation as LegalToolInvocation,
)
from src.common.domain.legal.passive_profile import (
    assert_within_passive_profile,
)
from src.scans.application.whitelist.resolve_toolset import resolve_toolset
from src.scans.domain.enums.tool_id import ToolId
from src.scans.domain.value_objects.tool_invocation import ToolInvocation

# ToolIds that target beyond the root (crawl/spider). Used to set
# ``targets_root_only=False`` when projecting a ToolInvocation onto the legal
# contract's ToolInvocation, so the passive-profile validator can reject any
# crawler that slipped into the gov/basic cell (defense in depth).
_NON_ROOT_TOOLS: frozenset[ToolId] = frozenset(
    {ToolId.KATANA, ToolId.ZAP_BASELINE, ToolId.ZAP_FULL_ACTIVE, ToolId.FFUF, ToolId.NIKTO}
)

# Map a ToolId to the tool name the legal passive profile allow-list uses. The
# legal contract keys on bare tool names ("testssl", "security_headers",
# "whatweb", "nuclei"); our ToolId StrEnum values already match those.
def _legal_name(tool: ToolId) -> str:
    return str(tool)


def _to_legal_invocation(inv: ToolInvocation) -> LegalToolInvocation:
    """Project a 02 ``ToolInvocation`` onto the 01 legal-contract invocation.

    The legal validator checks the tool name + the flag/tag tokens. For nuclei we
    must surface the ``-tags`` values as individual flag tokens so the allow/deny
    check works; we expand the comma-joined tag string into the token set.
    """
    flags: set[str] = set()
    raw = list(inv.flags)
    i = 0
    while i < len(raw):
        token = raw[i]
        if token == "-tags" and i + 1 < len(raw):
            flags.update(raw[i + 1].split(","))
            i += 2
            continue
        if token in ("-etags", "-no-spider", "--root", "-passive"):
            # operational/declarative tokens, not tags to validate
            i += 1
            if token == "-etags" and i < len(raw):
                i += 1  # skip the etags value too
            continue
        i += 1
    return LegalToolInvocation(
        tool=_legal_name(inv.tool),
        flags=frozenset(flags),
        targets_root_only=inv.tool not in _NON_ROOT_TOOLS,
    )


def resolve_tools(
    *,
    is_gov: bool,
    level: ScanLevel,
    demo: bool = False,
    hexstrike_ok: bool = False,
) -> list[ToolInvocation]:
    """Resolve the runnable tool battery for a scan (spec §4, plan §3.5).

    Delegates the *policy* to ``resolve_toolset`` (02) and materializes it into a
    list. For ``(is_gov=True, basico)`` the resolved set MUST validate against
    ``assert_within_passive_profile`` (01) — if 02 ever changed the gov/basic cell
    in a way that violates the passive contract, this raises (and the test breaks).

    - ``demo=True`` short-circuits to the demo profile (orthogonal to level).
    - hexstrike is appended only on the advanced level and only when
      ``hexstrike_ok`` (``settings.ENABLE_HEXSTRIKE and <healthcheck OK>``); the
      advanced level NEVER depends on hexstrike to produce findings.
    """
    toolset = resolve_toolset(is_gov, level, demo=demo, hexstrike_ok=hexstrike_ok)

    if not demo and is_gov and level is ScanLevel.BASICO:
        assert_within_passive_profile(_to_legal_invocation(inv) for inv in toolset)

    return list(toolset)
