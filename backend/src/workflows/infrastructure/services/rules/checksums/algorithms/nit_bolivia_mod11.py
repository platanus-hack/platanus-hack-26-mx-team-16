"""Validate Bolivian NIT identifiers using the mod-11 verifier digit.

A NIT (Número de Identificación Tributaria, SIN Bolivia) is `<body><dv>`
where `dv` is a single verifier digit. The mod-11 algorithm walks the body
digits right-to-left multiplying by `2..9` cyclically, sums, and computes
`11 - (sum % 11)` mapped to the edge cases: `11 → 0` and `10 → 1`.

Accepted input shapes: plain digits (`1234567897`), with an optional hyphen
or space before the verifier (`123456789-7`), and thousand separators
(dots/spaces) which are stripped before validation.

Separators are validated *before* stripping: only digits, well-placed dot/space
thousand groups and a single optional `-`/space before the DV are allowed.
This rejects separator soup (`1.2.3.4.5.6.7.8.9-7`) that previously slipped
through because every dot/space was stripped unconditionally — an ambiguity
that produced ~10% spurious PASSes.
"""

from __future__ import annotations

import re

from src.workflows.infrastructure.services.rules.checksums.algorithms._format import (
    normalize_nit,
)

_NIT_RE = re.compile(r"^(\d{4,12})-?(\d)$")

_MULTIPLIERS = [2, 3, 4, 5, 6, 7, 8, 9]


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = normalize_nit(value)
    if cleaned is None:
        return False
    match = _NIT_RE.match(cleaned)
    if not match:
        return False
    body, verifier = match.group(1), match.group(2)
    total = 0
    for idx, digit in enumerate(reversed(body)):
        total += int(digit) * _MULTIPLIERS[idx % len(_MULTIPLIERS)]
    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "1" if remainder == 10 else str(remainder)
    return verifier == expected
