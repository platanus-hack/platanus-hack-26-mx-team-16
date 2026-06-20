"""Validate Colombian NIT identifiers using the DIAN mod-11 verifier digit.

A NIT is `<body>-<dv>` where `dv` is the dígito de verificación computed by
the DIAN routine: each body digit (right-to-left) is multiplied by the prime
sequence `3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`, the
products are summed, and with `r = sum % 11` the verifier is `r` when
`r < 2`, else `11 - r`.

For the common 9-digit NIT this is equivalent to applying the primes
`41, 37, 29, 23, 19, 17, 13, 7, 3` left-to-right.

Accepted input shapes: `800197268-4`, `800.197.268-4`, `8001972684`
(thousand separators and spaces are stripped; the hyphen is optional).

Separators are validated *before* stripping (see `_format.normalize_nit`): only
well-placed dot/space thousand groups and a single optional `-`/space before the
DV are allowed, rejecting separator soup that previously slipped through.
"""

from __future__ import annotations

import re

from src.workflows.infrastructure.services.rules.checksums.algorithms._format import (
    normalize_nit,
)

_NIT_RE = re.compile(r"^(\d{3,15})-?(\d)$")

# DIAN prime weights, applied right-to-left over the NIT body.
_PRIMES = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


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
        total += int(digit) * _PRIMES[idx]
    remainder = total % 11
    expected = remainder if remainder < 2 else 11 - remainder
    return verifier == str(expected)
