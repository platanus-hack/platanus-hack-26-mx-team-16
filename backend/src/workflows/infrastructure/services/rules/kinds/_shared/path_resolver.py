"""Resolve `@{slug}.path` references against the live `EvalDocumentInput` set.

Compile records refs as syntactic objects (`DocRef`); evaluate consumes those
refs by walking each matching document's `extracted_fields` and producing one
or more `ResolvedValue`s. The returned list always conserves trace info even
when the field is missing — citations need to point at the document either
way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared.refs import DocRef

_SEGMENT_RE = re.compile(r"(?P<key>[A-Za-z_][\w]*)|\[(?P<index>\d*)\]")


class MissingDocumentError(InvalidWorkflowRuleConfigError):
    def __init__(self, slug: str):
        super().__init__(f"No document of type {slug!r} provided to evaluate this rule")
        self.slug = slug


class MissingFieldError(InvalidWorkflowRuleConfigError):
    def __init__(self, field_path: str, document_ids: list[UUID]):
        super().__init__(f"Required field {field_path!r} missing on document(s): {[str(d) for d in document_ids]}")
        self.field_path = field_path
        self.document_ids = document_ids


@dataclass(frozen=True)
class ResolvedValue:
    document_id: UUID
    document_type_slug: str
    field_path: str
    value: Any


def resolve(
    ref: DocRef,
    documents: list[EvalDocumentInput],
    *,
    required: bool = True,
) -> list[ResolvedValue]:
    matches = [d for d in documents if d.document_type_slug == ref.slug]
    if not matches:
        raise MissingDocumentError(ref.slug)

    if ref.kind == "collection" or ref.path is None:
        return [
            ResolvedValue(
                document_id=d.document_id,
                document_type_slug=ref.slug,
                field_path="",
                value=d.extracted_fields,
            )
            for d in matches
        ]

    segments = _parse_path(ref.path or "")
    resolved: list[ResolvedValue] = []
    missing_in: list[UUID] = []
    for doc in matches:
        for path_str, value in _walk_segments(doc.extracted_fields, segments):
            resolved.append(
                ResolvedValue(
                    document_id=doc.document_id,
                    document_type_slug=ref.slug,
                    field_path=path_str,
                    value=value,
                )
            )
        if not any(r.document_id == doc.document_id for r in resolved):
            missing_in.append(doc.document_id)
    if required and not resolved:
        raise MissingFieldError(ref.path or "", [d.document_id for d in matches])
    return resolved


def _parse_path(path: str) -> list[tuple[str, str | int | None]]:
    """Tokenize `a.items[].b[2].c` into ('key','a'), ('iter', None), ('key','b'), ('idx',2), ...."""
    if not path:
        return []
    tokens: list[tuple[str, str | int | None]] = []
    for match in _SEGMENT_RE.finditer(path):
        if match.group("key") is not None:
            tokens.append(("key", match.group("key")))
            continue
        idx = match.group("index")
        if idx == "":
            tokens.append(("iter", None))
        else:
            tokens.append(("idx", int(idx)))
    return tokens


def _walk_segments(
    root: Any,
    segments: list[tuple[str, str | int | None]],
) -> list[tuple[str, Any]]:
    """Return [(rendered_path, value), ...] enumerating all matching values."""
    results: list[tuple[str, Any]] = []

    def _step(value: Any, idx: int, path_so_far: str) -> None:
        if idx == len(segments):
            results.append((path_so_far, value))
            return
        kind, payload = segments[idx]
        if kind == "key":
            if isinstance(value, dict) and payload in value:
                next_path = f"{path_so_far}.{payload}" if path_so_far else str(payload)
                _step(value[payload], idx + 1, next_path)
        elif kind == "idx":
            if isinstance(value, list) and 0 <= int(payload or 0) < len(value):
                pos = int(payload or 0)
                next_path = f"{path_so_far}[{pos}]"
                _step(value[pos], idx + 1, next_path)
        elif kind == "iter":
            if isinstance(value, list):
                for pos, item in enumerate(value):
                    next_path = f"{path_so_far}[{pos}]"
                    _step(item, idx + 1, next_path)

    _step(root, 0, "")
    return results
