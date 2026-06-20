"""Build canonical Citation objects from path_resolver outputs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from src.common.domain.models.processing.citation import Citation
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)


def build_citations(
    resolved: Iterable[ResolvedValue],
    *,
    sub_check_id: str | None = None,
) -> list[Citation]:
    return [
        Citation(
            document_id=r.document_id,
            document_type_slug=r.document_type_slug,
            field_path=r.field_path,
            value=_stringify(r.value),
            sub_check_id=sub_check_id,
        )
        for r in resolved
    ]


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)
