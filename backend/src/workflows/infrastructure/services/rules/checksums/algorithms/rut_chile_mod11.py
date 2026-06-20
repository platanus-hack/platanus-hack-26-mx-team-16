"""Validate Chilean RUT identifiers using the mod-11 verifier digit.

A RUT is `<digits>-<verifier>` where the verifier is `0-9` or `K`. The mod-11
algorithm walks the digits right-to-left multiplying by `2..7` cyclically,
sums, divides by 11, and the verifier is `11 - (sum % 11)` mapped to `0`/`K`
for the edge cases.
"""

from __future__ import annotations

import re

_RUT_RE = re.compile(r"^\s*(\d{1,9})-?([0-9kK])\s*$")


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.replace(".", "").replace(" ", "")
    match = _RUT_RE.match(cleaned)
    if not match:
        return False
    body, verifier = match.group(1), match.group(2).upper()
    multipliers = [2, 3, 4, 5, 6, 7]
    total = 0
    for idx, digit in enumerate(reversed(body)):
        total += int(digit) * multipliers[idx % len(multipliers)]
    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
    return verifier == expected
