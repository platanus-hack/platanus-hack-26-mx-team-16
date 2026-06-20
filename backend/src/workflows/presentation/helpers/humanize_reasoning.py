"""Translate raw check-engine reasoning strings into user-friendly Spanish.

The validation engine emits structured-but-technical reasons like
`c1: FORMAT_CHECK failed for 2 value(s)`. The DB keeps these verbatim so
debugging stays precise, but the API surfaces a humanized version to the
UI via the result presenter.

Recognized patterns are translated explicitly; anything unknown falls
back to a generic message tagged with the sub-check id so the user
still sees something coherent without leaking internals.
"""

from __future__ import annotations

import re
from typing import Iterable

# Each entry: (regex, formatter). The first match wins.
_PATTERNS: list[tuple[re.Pattern[str], object]] = [
    (
        re.compile(r"^FORMAT_CHECK failed for (?P<n>\d+) value\(s\)$"),
        lambda m: (
            f"El formato no es válido en {m['n']} valor."
            if m["n"] == "1"
            else f"El formato no es válido en {m['n']} valores."
        ),
    ),
    (
        re.compile(r"^FORMAT_CHECK ok$"),
        lambda _m: "El formato es correcto.",
    ),
    (
        re.compile(r"^RANGE_CHECK: value (?P<v>.+) below min (?P<min>.+)$"),
        lambda m: f"El valor {m['v']} está por debajo del mínimo permitido ({m['min']}).",
    ),
    (
        re.compile(r"^RANGE_CHECK: value (?P<v>.+) above max (?P<max>.+)$"),
        lambda m: f"El valor {m['v']} excede el máximo permitido ({m['max']}).",
    ),
    (
        re.compile(r"^RANGE_CHECK: value is missing$"),
        lambda _m: "Falta el valor a validar.",
    ),
    (
        re.compile(r"^RANGE_CHECK ok$"),
        lambda _m: "El valor está dentro del rango permitido.",
    ),
    (
        re.compile(r"^DATE_CHECK: value (?P<v>.+) not parseable$"),
        lambda m: f"No se pudo interpretar la fecha {m['v']}.",
    ),
    (
        re.compile(r"^DATE_CHECK: (?P<d>[^ ]+) not before (?P<ref>[^ ]+)$"),
        lambda m: f"La fecha {m['d']} no es anterior a {m['ref']}.",
    ),
    (
        re.compile(r"^DATE_CHECK: (?P<d>[^ ]+) not after (?P<ref>[^ ]+)$"),
        lambda m: f"La fecha {m['d']} no es posterior a {m['ref']}.",
    ),
    (
        re.compile(r"^DATE_CHECK ok$"),
        lambda _m: "La fecha cumple el criterio.",
    ),
    (
        re.compile(r"^CHECKSUM_CHECK\[(?P<algo>[^\]]+)\] failed for (?P<n>\d+) value\(s\)$"),
        lambda m: (
            f"La verificación de dígito de control ({m['algo']}) falló en {m['n']} valor."
            if m["n"] == "1"
            else f"La verificación de dígito de control ({m['algo']}) falló en {m['n']} valores."
        ),
    ),
    (
        re.compile(r"^CHECKSUM_CHECK\[(?P<algo>[^\]]+)\] ok$"),
        lambda m: f"El dígito de control ({m['algo']}) es correcto.",
    ),
    (
        # Generic "<METHOD> raised: ..." → internal engine error.
        re.compile(r"^(?P<method>[A-Z_]+) raised: .*$"),
        lambda _m: "Hubo un problema técnico al ejecutar esta regla.",
    ),
]

_SUB_CHECK_PREFIX = re.compile(r"^(?P<id>c\d+):\s*(?P<rest>.+)$")


def humanize(reasoning: str | None) -> str | None:
    """Translate a raw check-engine reasoning string into a user-friendly one.

    `reasoning` is the value the engine writes onto `WorkflowRuleResult.reasoning`.
    It may carry one or more sub-check reasons separated by `"; "` (joined
    by the tree evaluator). Each piece is humanized independently; the
    output joins them back with `"; "`.

    Returns the original string verbatim when nothing matches — never
    drops information.
    """
    if reasoning is None or not reasoning.strip():
        return reasoning

    # Pass through the engine's canonical "everything passed" sentinel.
    if reasoning.strip() == "All checks passed":
        return "Todas las verificaciones pasaron."
    if reasoning.strip() == "Tree failed":
        return "La regla no se cumplió."

    parts = [p.strip() for p in reasoning.split(";") if p.strip()]
    # Single sub-check → drop the `[c1]` tag (it's internal noise).
    show_prefix = len(parts) > 1
    humanized = [_humanize_part(p, show_prefix=show_prefix) for p in parts]
    return "; ".join(humanized)


def _humanize_part(part: str, *, show_prefix: bool) -> str:
    rest = part
    prefix = ""
    m = _SUB_CHECK_PREFIX.match(part)
    if m:
        if show_prefix:
            prefix = f"[{m['id']}] "
        rest = m["rest"]

    for pattern, formatter in _PATTERNS:
        match = pattern.match(rest)
        if match:
            return prefix + formatter(match)  # type: ignore[operator]

    # Last-resort fallback — drop the prefix and keep the body so the
    # user gets at least a hint instead of raw machine output.
    return prefix + rest


def humanize_many(reasons: Iterable[str | None]) -> list[str | None]:
    """Convenience helper for batch-translating a list of reasonings."""
    return [humanize(r) for r in reasons]
