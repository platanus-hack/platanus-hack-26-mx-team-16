"""ISO-7064 mod-97 checksum used by IBAN bank accounts."""

from __future__ import annotations


def validate(value: str) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.replace(" ", "").upper()
    if len(cleaned) < 4:
        return False
    rotated = cleaned[4:] + cleaned[:4]
    digits = []
    for ch in rotated:
        if ch.isdigit():
            digits.append(ch)
        elif "A" <= ch <= "Z":
            digits.append(str(ord(ch) - 55))
        else:
            return False
    numeric = int("".join(digits))
    return numeric % 97 == 1
