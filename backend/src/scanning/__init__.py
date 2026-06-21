"""Owliver scanning engine (04-scanning-engine).

The execution machinery that turns a URL into raw tool evidence: how the worker
launches each scanner (subprocess inside the fat ``scanners`` image vs DooD
siblings ZAP/hexstrike via the host docker socket) under hard per-tool timeouts,
a global ~8min budget, a watchdog, egress-isolated networks, and file-based
evidence storage.

This package owns the *execution mechanism* only. Parsing raw ``stdout`` into
``Finding[]`` and orchestrating the Agno Team belong to 05-agent-team; the shape
of ``Finding`` / ``coverage`` belongs to 06-data-model; the ``(is_gov, level)``
tool whitelist belongs to 02-attack-levels (materialized here, never re-authored).

Public API (consumed by 05-agent-team):
- ``run_tool(spec, *, target, host_shared_dir, cancel) -> ToolResult``
- ``ToolResult`` (raw-stdout contract)
- ``TOOL_SPECS`` registry + ``ToolSpec``
- ``resolve_tools(is_gov, level, ...) -> list[ToolInvocation]``
- ``CancelToken`` + ``run_with_watchdog`` (partial-failure + budget)
- ``assert_public_target`` (egress guard)
- ``LegalRobotsPolicy`` (RobotsPolicy Protocol impl)
"""

from __future__ import annotations

from src.scanning.egress import EgressViolation, assert_public_target
from src.scanning.registry import TOOL_SPECS, ToolMechanism as ToolMechanism
from src.scanning.registry import ToolSpec, spec_for
from src.scanning.resolver import resolve_tools
from src.scanning.runner import ToolResult, run_tool
from src.scanning.watchdog import CancelToken, ScanBudgetExceeded, run_with_watchdog

__all__ = [
    "TOOL_SPECS",
    "CancelToken",
    "EgressViolation",
    "ScanBudgetExceeded",
    "ToolMechanism",
    "ToolResult",
    "ToolSpec",
    "assert_public_target",
    "resolve_tools",
    "run_tool",
    "run_with_watchdog",
    "spec_for",
]
