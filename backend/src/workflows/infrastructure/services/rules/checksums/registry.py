"""Registry of value-checksum algorithms used by `CHECKSUM_CHECK` sub_checks.

Algorithms self-register at app bootstrap (see `algorithms/`). The dispatcher
looks up an algorithm by name and applies it to the resolved value.
"""

from __future__ import annotations

from collections.abc import Callable

ChecksumFn = Callable[[str], bool]

_REGISTRY: dict[str, ChecksumFn] = {}


def register(name: str, fn: ChecksumFn) -> None:
    _REGISTRY[name] = fn


def get(name: str) -> ChecksumFn:
    if name not in _REGISTRY:
        msg = f"Unknown checksum algorithm: {name!r}. Known: {sorted(_REGISTRY)}"
        raise KeyError(msg)
    return _REGISTRY[name]


def known() -> set[str]:
    return set(_REGISTRY.keys())


def clear() -> None:
    _REGISTRY.clear()
