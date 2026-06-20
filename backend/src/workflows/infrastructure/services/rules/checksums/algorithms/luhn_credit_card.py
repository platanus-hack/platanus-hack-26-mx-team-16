"""Luhn (mod-10) checksum used by credit card numbers and similar identifiers."""

from __future__ import annotations


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    digits = [c for c in value if c.isdigit()]
    if not digits:
        return False
    total = 0
    for idx, ch in enumerate(reversed(digits)):
        n = int(ch)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
