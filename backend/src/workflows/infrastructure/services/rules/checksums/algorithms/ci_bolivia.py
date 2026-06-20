"""Validate the *format* of Bolivian CI (Cédula de Identidad) numbers.

IMPORTANT: the Bolivian CI has **no publicly documented verifier digit**,
so — unlike `rut_chile_mod11` or `nit_bolivia_mod11` — this is a pure
format check, not a checksum. What can be validated deterministically:

- a numeric body of 5 to 8 digits, and
- an optional departmental extension suffix (`LP`, `CB`, `SC`, `OR`, `PT`,
  `TJ`, `CH`, `BE`, `PD`), separated by an optional hyphen or space.

Examples accepted: `1234567`, `1234567 LP`, `1234567-LP`, `12345678SC`.
"""

from __future__ import annotations

import re

_DEPARTMENT_CODES = "LP|CB|SC|OR|PT|TJ|CH|BE|PD"

_CI_RE = re.compile(
    rf"^\s*(\d{{5,8}})(?:[\s-]?({_DEPARTMENT_CODES}))?\s*$",
    re.IGNORECASE,
)


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.replace(".", "")
    return _CI_RE.match(cleaned) is not None
