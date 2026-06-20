"""Validate the *format* of Colombian CC (Cédula de Ciudadanía) numbers.

IMPORTANT: the Colombian cédula has **no publicly documented verifier
digit**, so this is a pure format check, not a checksum. What can be
validated deterministically:

- a purely numeric body of 6 to 10 digits (legacy cédulas are 6-8 digits;
  post-2003 NUIP numbers are 10 digits), with no alphabetic characters.

Thousand separators (dots) and surrounding whitespace are tolerated and
stripped before validation: `1.020.713.756` validates like `1020713756`.
"""

from __future__ import annotations

import re

_CC_RE = re.compile(r"^\d{6,10}$")


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip().replace(".", "").replace(" ", "")
    return _CC_RE.match(cleaned) is not None
