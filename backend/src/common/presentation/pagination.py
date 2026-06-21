"""Cursor-pagination helpers for the Owliver API surface (12-api §5.2).

Builds on the foundation's ``Page[T]`` / ``encode_cursor`` (no parallel codec):

- ``CursorPage[T]`` is a thin ``Page[T]`` factory: it takes ``limit + 1`` rows
  fetched by the repo, trims to ``limit``, and derives ``next_cursor`` from the
  trailing row via a caller-supplied ``cursor_of`` function. ``ApiJSONResponse``
  already serializes ``Page`` as
  ``{data, pagination: {nextCursor, limit}, timestamp}``.
- ``encode_severity_cursor`` / ``decode_severity_cursor`` add the **stable
  composite cursor** that ``GET /scans/{id}/findings`` needs to page a
  ``severity DESC, uuid DESC`` ordering — an extension of the same base64 codec,
  not a new cursor type. Findings live in one scan (bounded), so the use case
  sorts in memory and slices; the cursor only needs to encode ``(severity, uuid)``
  to resume deterministically.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from src.common.application.helpers.encoding import decode_base64, encode_base64
from src.common.application.helpers.pagination import encode_cursor
from src.common.domain.entities.common.pagination import Page
from src.common.settings import settings

# Severity ordering for the findings keyset (spec: "ordenados por severidad desc").
# Lower index == more severe; ``info`` (weight 0) sorts last.
SEVERITY_ORDER: tuple[str, ...] = ("critical", "high", "medium", "low", "info")
_SEVERITY_RANK: dict[str, int] = {sev: i for i, sev in enumerate(SEVERITY_ORDER)}

_SEPARATOR = "::"


def severity_rank(severity: str) -> int:
    """Rank for ``severity DESC`` ordering — unknown severities sort last."""
    return _SEVERITY_RANK.get(severity, len(SEVERITY_ORDER))


def encode_severity_cursor(severity: str, uuid: UUID) -> str:
    """Opaque base64 cursor over the ``(severity, uuid)`` keyset of a finding."""
    return encode_base64(f"{severity}{_SEPARATOR}{uuid}")


def decode_severity_cursor(cursor: str) -> tuple[str, UUID]:
    """Inverse of :func:`encode_severity_cursor`. Raises ``ValueError`` if malformed."""
    decoded = decode_base64(cursor)
    severity, raw_uuid = decoded.split(_SEPARATOR, 1)
    return severity, UUID(raw_uuid)


class CursorPage:
    """Factory that turns a ``limit + 1`` row window into a ``Page[T]``.

    Usage in a use case::

        rows = await repo.find_for_user(user.uuid, limit=limit, cursor=cursor)
        return CursorPage.build(
            rows,
            limit=limit,
            cursor_of=lambda scan: encode_cursor(scan.created_at, scan.uuid),
        )

    The repo always fetches ``limit + 1`` rows; if it returns more than ``limit``
    there is a next page and the cursor is derived from the **last kept** row.
    """

    @staticmethod
    def build(
        rows: list[Any],
        *,
        limit: int = settings.PAGINATION_PAGE_SIZE,
        cursor_of: Callable[[Any], str | None],
    ) -> Page:
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = cursor_of(items[-1]) if has_more and items else None
        return Page(items=items, next_cursor=next_cursor, limit=limit)


__all__ = [
    "SEVERITY_ORDER",
    "CursorPage",
    "decode_severity_cursor",
    "encode_cursor",
    "encode_severity_cursor",
    "severity_rank",
]
