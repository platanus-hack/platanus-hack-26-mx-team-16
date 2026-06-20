from __future__ import annotations

from enum import StrEnum


class ToolId(StrEnum):
    """Stable identifiers for every OWASP-web tool in the attack-level battery.

    These ids are the contract that 05-agent-team maps to its ``run_*`` tool
    functions and 04-scanning-engine maps to its per-tool timeout table (§4.2).
    They are *logical* names, not literal argv — the executor (04) appends
    operational flags (e.g. ``-duc``) at run time.

    Notes on coverage vs spec §3:
    - ``robots/sitemap`` recon: robots.txt is honored via ``RobotsPolicy`` (not a
      ToolId); sitemap has no ToolId (subsumed by recon, dropped here).
    - ``ffuf / gobuster``: the spec offers both as alternatives; FFUF is the
      canonical light dir-enum tool (gobuster intentionally not added).
    - ``WhatWeb / Wappalyzer``: WhatWeb is kept as the canonical fingerprinter.
    """

    TESTSSL = "testssl"
    SECURITY_HEADERS = "security_headers"  # security-headers / Observatory
    WHATWEB = "whatweb"
    NUCLEI = "nuclei"
    ZAP_BASELINE = "zap_baseline"
    ZAP_FULL_ACTIVE = "zap_full_active"
    NIKTO = "nikto"
    KATANA = "katana"
    FFUF = "ffuf"
    SQLMAP = "sqlmap"
    SUBFINDER = "subfinder"
    DNSX = "dnsx"
    HEXSTRIKE = "hexstrike"
