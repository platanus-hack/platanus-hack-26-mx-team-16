"""``security-headers`` shim — a single root request, raw JSON to stdout.

A light "Observatory / security-headers"-style check (spec §4.2): one request to
the target root with the identifiable ``SCANNER_USER_AGENT``, printing the
response security headers as JSON to stdout. 05's parser consumes that raw JSON;
this module does NOT score or interpret.

Invoked as ``security-headers <url>`` via subprocess (TOOL_SPECS base_argv). The
HTTP call is lazy-imported so the module imports cleanly without the dependency.
"""

from __future__ import annotations

import json
import sys

from src.common.domain.legal.constants import SCANNER_USER_AGENT

#: Security-relevant response headers reported by the shim.
SECURITY_HEADERS: tuple[str, ...] = (
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-xss-protection",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
)


def collect_headers(url: str, *, timeout_s: float = 30.0) -> dict[str, object]:
    """One root GET; return ``{url, status, headers:{...present...}, missing:[...]}``.

    ``httpx`` is imported lazily so this module is importable without it. On any
    network error the result carries ``error`` so the parser can emit a coverage
    note rather than a finding.
    """
    import httpx  # lazy: keep module import light

    try:
        resp = httpx.get(
            url,
            timeout=timeout_s,
            follow_redirects=True,
            headers={"User-Agent": SCANNER_USER_AGENT},
        )
    except Exception as exc:  # noqa: BLE001 - report as data, never crash the shim
        return {"url": url, "error": f"{type(exc).__name__}: {exc}"}

    present = {h: resp.headers[h] for h in SECURITY_HEADERS if h in resp.headers}
    missing = [h for h in SECURITY_HEADERS if h not in resp.headers]
    return {"url": url, "status": resp.status_code, "headers": present, "missing": missing}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(json.dumps({"error": "usage: security-headers <url>"}))
        return 2
    print(json.dumps(collect_headers(args[0])))
    return 0


if __name__ == "__main__":  # pragma: no cover - entrypoint
    raise SystemExit(main())
