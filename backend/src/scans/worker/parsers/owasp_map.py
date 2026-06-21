"""Static OWASP-category mapping (05-agent-team spec §2.2, plan §2).

The mapping from a tool's native signal (CWE id, nuclei tag, missing-header name,
ZAP alertRef/cweid, agentic probe id) to the OWASP ``A01..A10`` / OWASP-LLM
``LLM01..LLM10`` taxonomy is a **curated static dict**, NEVER asked to the LLM
(spec §2.2 / plan §2). Parsers call :func:`category_for_cwe`,
:func:`category_for_nuclei_tags`, :func:`category_for_header` to assign
``Finding.category`` deterministically.

Keeping the mapping in one module means the taxonomy is auditable in a single
place and shared by every parser; a tool-id/cwe/tag that is not mapped falls back
to a deterministic default (``A05`` "Security Misconfiguration" for web,
``LLM01`` for agentic) — never an exception, so a novel template never breaks a
scan (plan §9 test ``test_owasp_map``).
"""

from __future__ import annotations

from src.common.domain.enums.scans import FindingCategory

#: Deterministic fallback for an unmapped web signal — most scanner findings that
#: do not map cleanly are misconfigurations.
DEFAULT_WEB_CATEGORY: str = FindingCategory.A05.value
#: Deterministic fallback for an unmapped agentic signal.
DEFAULT_AGENTIC_CATEGORY: str = FindingCategory.LLM01.value

# CWE id -> OWASP A0x. Curated from the OWASP Top-10 2021 CWE mappings; only the
# high-signal CWEs the prioritized scanners emit are listed. Unmapped -> A05.
_CWE_TO_CATEGORY: dict[int, str] = {
    # A01 Broken Access Control
    22: FindingCategory.A01.value,  # Path Traversal
    23: FindingCategory.A01.value,
    35: FindingCategory.A01.value,
    59: FindingCategory.A01.value,
    200: FindingCategory.A01.value,  # Exposure of Sensitive Information
    201: FindingCategory.A01.value,
    264: FindingCategory.A01.value,
    275: FindingCategory.A01.value,
    284: FindingCategory.A01.value,  # Improper Access Control
    285: FindingCategory.A01.value,  # Improper Authorization
    639: FindingCategory.A01.value,  # IDOR
    668: FindingCategory.A01.value,
    # A02 Cryptographic Failures
    259: FindingCategory.A02.value,
    295: FindingCategory.A02.value,  # Improper Certificate Validation
    310: FindingCategory.A02.value,
    319: FindingCategory.A02.value,  # Cleartext Transmission
    326: FindingCategory.A02.value,  # Inadequate Encryption Strength
    327: FindingCategory.A02.value,  # Broken/Risky Crypto
    328: FindingCategory.A02.value,
    916: FindingCategory.A02.value,
    # A03 Injection
    20: FindingCategory.A03.value,  # Improper Input Validation
    74: FindingCategory.A03.value,
    77: FindingCategory.A03.value,  # Command Injection
    78: FindingCategory.A03.value,  # OS Command Injection
    79: FindingCategory.A03.value,  # XSS
    89: FindingCategory.A03.value,  # SQL Injection
    90: FindingCategory.A03.value,  # LDAP Injection
    91: FindingCategory.A03.value,
    94: FindingCategory.A03.value,  # Code Injection
    113: FindingCategory.A03.value,  # HTTP Response Splitting
    # A04 Insecure Design
    209: FindingCategory.A04.value,  # Information Exposure via error message
    256: FindingCategory.A04.value,
    501: FindingCategory.A04.value,
    522: FindingCategory.A04.value,
    # A05 Security Misconfiguration
    16: FindingCategory.A05.value,  # Configuration
    548: FindingCategory.A05.value,  # Directory listing
    611: FindingCategory.A05.value,  # XXE
    614: FindingCategory.A05.value,  # Sensitive cookie without Secure
    693: FindingCategory.A05.value,  # Protection Mechanism Failure
    732: FindingCategory.A05.value,
    1021: FindingCategory.A05.value,  # Clickjacking / missing frame options
    # A06 Vulnerable and Outdated Components
    937: FindingCategory.A06.value,
    1035: FindingCategory.A06.value,
    1104: FindingCategory.A06.value,  # Use of Unmaintained Third Party Components
    # A07 Identification and Authentication Failures
    287: FindingCategory.A07.value,  # Improper Authentication
    307: FindingCategory.A07.value,  # Improper Restriction of Excessive Auth Attempts
    384: FindingCategory.A07.value,  # Session Fixation
    521: FindingCategory.A07.value,  # Weak Password Requirements
    613: FindingCategory.A07.value,  # Insufficient Session Expiration
    # A08 Software and Data Integrity Failures
    345: FindingCategory.A08.value,
    353: FindingCategory.A08.value,
    494: FindingCategory.A08.value,  # Download of Code Without Integrity Check
    829: FindingCategory.A08.value,
    # A09 Security Logging and Monitoring Failures
    532: FindingCategory.A09.value,  # Insertion of Sensitive Info into Log
    778: FindingCategory.A09.value,  # Insufficient Logging
    # A10 Server-Side Request Forgery
    918: FindingCategory.A10.value,  # SSRF
}

# nuclei tag -> OWASP A0x. nuclei templates carry a ``tags`` list; the first tag
# that matches wins. High-signal tags only; unmatched -> CWE path or A05.
_TAG_TO_CATEGORY: dict[str, str] = {
    "sqli": FindingCategory.A03.value,
    "xss": FindingCategory.A03.value,
    "rce": FindingCategory.A03.value,
    "injection": FindingCategory.A03.value,
    "lfi": FindingCategory.A01.value,
    "traversal": FindingCategory.A01.value,
    "ssrf": FindingCategory.A10.value,
    "xxe": FindingCategory.A05.value,
    "exposure": FindingCategory.A01.value,
    "disclosure": FindingCategory.A01.value,
    "default-login": FindingCategory.A07.value,
    "auth-bypass": FindingCategory.A07.value,
    "ssl": FindingCategory.A02.value,
    "tls": FindingCategory.A02.value,
    "crypto": FindingCategory.A02.value,
    "misconfig": FindingCategory.A05.value,
    "cve": FindingCategory.A06.value,
    "tech": FindingCategory.A06.value,
    "takeover": FindingCategory.A01.value,
}

# Missing/weak security header -> OWASP A0x. testssl & security-headers parsers
# share this. Most missing headers are A05; HSTS/cookie-crypto issues map to A02.
_HEADER_TO_CATEGORY: dict[str, str] = {
    "strict-transport-security": FindingCategory.A02.value,
    "content-security-policy": FindingCategory.A05.value,
    "x-frame-options": FindingCategory.A05.value,
    "x-content-type-options": FindingCategory.A05.value,
    "referrer-policy": FindingCategory.A05.value,
    "permissions-policy": FindingCategory.A05.value,
    "x-xss-protection": FindingCategory.A05.value,
    "set-cookie": FindingCategory.A02.value,
}


def _normalize(token: str) -> str:
    return token.strip().lower()


def category_for_cwe(cwe: int | str | None) -> str | None:
    """Map a CWE id to an OWASP category, or ``None`` if not mapped.

    Accepts ``79``, ``"79"`` or ``"CWE-79"``; returns ``None`` for an unmapped or
    unparseable id so callers can fall through to another signal before defaulting.
    """
    if cwe is None:
        return None
    if isinstance(cwe, str):
        digits = "".join(ch for ch in cwe if ch.isdigit())
        if not digits:
            return None
        cwe = int(digits)
    return _CWE_TO_CATEGORY.get(int(cwe))


def category_for_nuclei_tags(tags: list[str] | tuple[str, ...] | None) -> str | None:
    """First tag (in order) that maps to an OWASP category, else ``None``."""
    if not tags:
        return None
    for tag in tags:
        mapped = _TAG_TO_CATEGORY.get(_normalize(tag))
        if mapped is not None:
            return mapped
    return None


def category_for_header(header: str | None) -> str:
    """Map a (missing/weak) security-header name to an OWASP category.

    Always returns a category — an unknown header defaults to ``A05`` since a
    header issue is by definition a misconfiguration.
    """
    if not header:
        return DEFAULT_WEB_CATEGORY
    return _HEADER_TO_CATEGORY.get(_normalize(header), DEFAULT_WEB_CATEGORY)


def web_category(
    *,
    cwe: int | str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Resolve a web finding's OWASP category from its signals (deterministic).

    Precedence: explicit CWE mapping → nuclei tag mapping → ``A05`` default. Never
    raises; an unmapped signal yields :data:`DEFAULT_WEB_CATEGORY`.
    """
    return (
        category_for_cwe(cwe)
        or category_for_nuclei_tags(tags)
        or DEFAULT_WEB_CATEGORY
    )
