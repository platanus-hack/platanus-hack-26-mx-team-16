"""Shared separator normalization for tax-id checksums (E5 drift fix).

The NIT validators used to strip every dot and space unconditionally before
matching, so arbitrarily-placed separators (`1.2.3.4.5.6.7.8.9-7`,
`123 456 789 7`) collapsed into a clean number and validated — a ~10% spurious
PASS rate driven by separator ambiguity. `normalize_nit` validates separator
*placement* first and returns the bare `<digits>[-<dv>]` string, or `None` when
the shape is not a legitimately-formatted identifier.

Accepted:
- bare digits (`8001972684`);
- thousand groups joined by dots OR spaces (first group 1-3 digits, every later
  group exactly 3) — e.g. `800.197.268`, `1 234 567`;
- an optional single `-` (or a lone space) immediately before the one-digit
  verifier — e.g. `800.197.268-4`, `123456789-7`.

Rejected:
- mixed dot+space grouping, repeated/edge separators, groups that are not valid
  thousand groups (`1.2.3.4`), more than one hyphen, a hyphen anywhere but
  before the final digit.
"""

from __future__ import annotations

import re

_BODY_PLAIN = re.compile(r"^\d+$")
_BODY_DOT_GROUPED = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
_BODY_SPACE_GROUPED = re.compile(r"^\d{1,3}(?: \d{3})+$")


def normalize_nit(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None

    body, dv = _split_verifier(raw)
    if body is None:
        return None
    if not _is_valid_body(body):
        return None

    digits = body.replace(".", "").replace(" ", "")
    if dv is not None:
        return f"{digits}-{dv}"
    return digits


def _split_verifier(raw: str) -> tuple[str | None, str | None]:
    """Return (body, dv) where dv is the digit after a single `-`/space sep, or
    (body, None) when there is no explicit verifier separator. (None, None)
    when the hyphen placement is malformed."""
    if "-" in raw:
        # Exactly one hyphen, immediately before the final single digit.
        if raw.count("-") != 1:
            return None, None
        head, _, tail = raw.rpartition("-")
        if not re.fullmatch(r"\d", tail) or not head:
            return None, None
        return head.strip(), tail
    # A trailing " <digit>" acts as a verifier separator only when the body
    # itself is not space-grouped (otherwise it's just another thousand group).
    trailing = re.search(r" (\d)$", raw)
    if trailing:
        candidate_body = raw[: trailing.start()].strip()
        if _is_valid_body(candidate_body) and not _BODY_SPACE_GROUPED.match(raw):
            return candidate_body, trailing.group(1)
    return raw, None


def _is_valid_body(body: str) -> bool:
    if "." in body and " " in body:
        return False  # no mixed grouping
    return bool(
        _BODY_PLAIN.match(body) or _BODY_DOT_GROUPED.match(body) or _BODY_SPACE_GROUPED.match(body)
    )
