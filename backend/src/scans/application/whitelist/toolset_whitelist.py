"""The `(is_gov, level)` OWASP-web tool+flag whitelist POLICY (02-attack-levels).

This module is the declarative expression of 02's policy: *what* tools+flags each
`(is_gov, level)` pair is allowed to run. It is an **allow-list by construction** —
anything not present in a cell's tuple literally never reaches the agent.

Ownership split (02 ↔ 04): 02 owns the POLICY/CONTENT below (the contents of each
cell and the resolver's logical contract). 04-scanning-engine owns the concrete
runtime data structure + the worker enforcement drop point that materializes this
mapping and discards non-allowed tools before `owasp_agent` receives them. The
flags here are LOGICAL/declarative, not the literal argv (04 appends operational
flags at run time).

Cumulative ladder (spec §3): basic ⊂ intermediate ⊂ advanced. The `+` in the spec
table is literally tuple concatenation here.
"""

from __future__ import annotations

from types import MappingProxyType

from src.common.domain.enums.scans import ScanLevel  # owned by 06-data-model
from src.scans.domain.enums.tool_id import ToolId
from src.scans.domain.value_objects.tool_invocation import ToolInvocation

TI = ToolInvocation

# Canonical unified passive Nuclei tag set (01 §3 == 02 §4 == general basic §3.1).
# The invalid `http-misconfig` was eliminated; both specs agree on this exact set.
_PASSIVE_NUCLEI = TI(
    ToolId.NUCLEI,
    (
        "-tags",
        "exposures,misconfiguration,ssl,tech,dns",
        "-etags",
        "intrusive,dos,fuzzing,network",
        "-no-spider",
    ),
)

# --- BASIC layer, general (non-gov): passive over the root (spec §3.1) ---
_BASIC_NON_GOV: tuple[ToolInvocation, ...] = (
    TI(ToolId.WHATWEB, ("--root",)),
    TI(ToolId.TESTSSL, ("--root",)),
    TI(ToolId.SECURITY_HEADERS, ("--root",)),
    _PASSIVE_NUCLEI,
    TI(ToolId.SUBFINDER, ("-passive",)),
    TI(ToolId.DNSX, ("-passive",)),
)

# --- GOV/BASIC cell: LEGAL FLOOR (spec §4, byte-equivalent to 01 §3). ---
# testssl, security-headers, WhatWeb on the ROOT + the canonical passive Nuclei set
# (no spider). Differences vs non-gov: NO subfinder/dnsx recon; ZAP spider + katana
# are ABSENT by construction (they do not honor robots.txt -> illegal for passive
# gov). robots.txt is honored before any request via RobotsPolicy (spec §5).
_BASIC_GOV: tuple[ToolInvocation, ...] = (
    TI(ToolId.TESTSSL, ("--root",)),
    TI(ToolId.SECURITY_HEADERS, ("--root",)),
    TI(ToolId.WHATWEB, ("--root",)),
    _PASSIVE_NUCLEI,
)

# --- INTERMEDIATE delta (soft-active, rate-limited; spec §3.2) ---
# "Checks CORS / cookie / clickjacking" carry no own ToolId: subsumed by ZAP's
# passive rules + Nuclei misconfig tags (confirm against 04 when parsing).
# "ffuf / gobuster": FFUF chosen as the canonical light dir-enum tool.
_INTERMEDIATE_DELTA: tuple[ToolInvocation, ...] = (
    TI(ToolId.ZAP_BASELINE, ()),  # spider + ZAP passive scan (covers CORS/cookie/clickjacking)
    TI(ToolId.NUCLEI, ("-tags", "cve,default-logins")),  # full, low risk
    TI(ToolId.NIKTO, ()),
    TI(ToolId.KATANA, ()),  # crawl
    TI(ToolId.FFUF, ()),  # light dir enum (alternative to gobuster, spec §3.2)
)

# --- ADVANCED delta (bounded exploitation; spec §3.3 / §6). hexstrike NOT here. ---
# Reconciliation §3.3 vs §6: the spec lists "auth tests" too, but §6 bounds the
# GUARANTEED advanced battery to exactly three tools (ZAP full active + Nuclei
# fuzzing + sqlmap). We honor §6: "auth tests" are considered COVERED by the ZAP
# full active scan's auth/session rules and get no own ToolId. Deliberate cut.
_ADVANCED_DELTA: tuple[ToolInvocation, ...] = (
    TI(ToolId.ZAP_FULL_ACTIVE, ()),  # incl. auth/session checks (spec §3.3 "auth tests")
    TI(ToolId.NUCLEI, ("-fuzzing-templates",)),
    TI(ToolId.SQLMAP, ("--single-param",)),  # over 1 known param (spec §6)
)

# Cumulative accumulation: basic ⊂ intermediate ⊂ advanced.
_INTERMEDIATE_NON_GOV = _BASIC_NON_GOV + _INTERMEDIATE_DELTA
_ADVANCED_NON_GOV = _INTERMEDIATE_NON_GOV + _ADVANCED_DELTA
_INTERMEDIATE_GOV = _BASIC_GOV + _INTERMEDIATE_DELTA
_ADVANCED_GOV = _INTERMEDIATE_GOV + _ADVANCED_DELTA

# The frozen policy table. Immutable at runtime via MappingProxyType over frozen
# tuples of frozen ToolInvocation value objects. Keyed by (is_gov, level).
TOOLSET_WHITELIST: "MappingProxyType[tuple[bool, ScanLevel], tuple[ToolInvocation, ...]]" = MappingProxyType(
    {
        (False, ScanLevel.BASICO): _BASIC_NON_GOV,
        (False, ScanLevel.INTERMEDIO): _INTERMEDIATE_NON_GOV,
        (False, ScanLevel.AVANZADO): _ADVANCED_NON_GOV,
        (True, ScanLevel.BASICO): _BASIC_GOV,
        (True, ScanLevel.INTERMEDIO): _INTERMEDIATE_GOV,
        (True, ScanLevel.AVANZADO): _ADVANCED_GOV,
    }
)

# hexstrike: only ADDED by the resolver after flag + healthcheck pass (spec §6).
# Absent from every cell by default.
HEXSTRIKE_INVOCATION = TI(ToolId.HEXSTRIKE, ())

# Demo profile: NOT a level key in the mapping (not a 4th level). Orthogonal to
# level/is_gov. Curated fast subset; heavy tools (ZAP full active, garak) are
# pre-baked from fixtures, never run live (spec §7).
DEMO_PROFILE: tuple[ToolInvocation, ...] = (
    TI(ToolId.NUCLEI, ("-tags", "ssl,tech,exposures", "-no-spider")),  # fast subset
    TI(ToolId.TESTSSL, ("--fast",)),
    # The agentic "1 probe against the own bot" is owned by 03-agentic-surface.
)
