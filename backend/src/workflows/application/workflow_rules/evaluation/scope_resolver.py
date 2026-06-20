"""Convert a rule's scope (spec §7) into a list of evaluation invocations.

Produces a list of ``Combination`` instances; each becomes one
``WorkflowRuleResult`` row keyed by ``document_refs_hash``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from itertools import product
from typing import Any
from uuid import UUID

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleOnEmpty,
    WorkflowRuleScopeMode,
)
from src.common.domain.exceptions.workflow_rules import (
    WorkflowRuleScopeMismatchError,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument


@dataclass(frozen=True)
class ScopedDocument:
    document_id: UUID
    document_type_id: UUID | None
    document_type_slug: str | None


@dataclass
class Combination:
    """One concrete evaluation invocation produced by the resolver."""

    documents: list[ScopedDocument] = field(default_factory=list)
    document_refs: dict[str, Any] = field(default_factory=dict)
    is_synthetic_empty: bool = False
    synthetic_outcome: WorkflowRuleOnEmpty | None = None

    @property
    def document_refs_hash(self) -> str:
        canonical = json.dumps(self.document_refs, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _refs_for_documents(docs: list[ScopedDocument]) -> dict[str, Any]:
    """Map slug -> [doc_ids]; multiple docs of the same slug collapse into a list."""
    refs: dict[str, list[str]] = {}
    for doc in docs:
        slug = doc.document_type_slug or str(doc.document_type_id) or "unknown"
        refs.setdefault(slug, []).append(str(doc.document_id))
    return refs


def resolve_scope(
    *,
    scope: dict[str, Any],
    documents: list[WorkflowDocument],
    slug_by_document_type: dict[UUID, str | None],
) -> list[Combination]:
    """Expand the scope into the combinations to evaluate.

    `documents` should already be filtered to those eligible for the case
    (e.g. EXTRACTED status). `slug_by_document_type` maps document_type uuid
    to slug for cleaner ref keys.
    """
    raw_mode = scope.get("mode") or WorkflowRuleScopeMode.ALL_DOCUMENTS.value
    try:
        mode = WorkflowRuleScopeMode(raw_mode)
    except ValueError as exc:
        msg = f"unknown scope mode: {raw_mode}"
        raise WorkflowRuleScopeMismatchError(msg) from exc

    raw_on_empty = scope.get("on_empty") or WorkflowRuleOnEmpty.SKIPPED.value
    try:
        on_empty = WorkflowRuleOnEmpty(raw_on_empty)
    except ValueError as exc:
        msg = f"unknown on_empty: {raw_on_empty}"
        raise WorkflowRuleScopeMismatchError(msg) from exc

    if mode == WorkflowRuleScopeMode.ALL_DOCUMENTS:
        scoped = [
            ScopedDocument(
                document_id=d.uuid,
                document_type_id=d.document_type_id,
                document_type_slug=slug_by_document_type.get(d.document_type_id) if d.document_type_id else None,
            )
            for d in documents
        ]
        if not scoped:
            return _empty_or_synthetic(on_empty)
        return [
            Combination(
                documents=scoped,
                document_refs=_refs_for_documents(scoped),
            )
        ]

    if mode == WorkflowRuleScopeMode.SINGLE_DOCUMENT:
        target = scope.get("document_type")
        if not target:
            msg = "SINGLE_DOCUMENT requires document_type"
            raise WorkflowRuleScopeMismatchError(msg)
        target_uuid = UUID(str(target))
        matched = [
            ScopedDocument(
                document_id=d.uuid,
                document_type_id=d.document_type_id,
                document_type_slug=slug_by_document_type.get(d.document_type_id) if d.document_type_id else None,
            )
            for d in documents
            if d.document_type_id == target_uuid
        ]
        if not matched:
            return _empty_or_synthetic(on_empty)
        return [
            Combination(
                documents=[doc],
                document_refs=_refs_for_documents([doc]),
            )
            for doc in matched
        ]

    if mode == WorkflowRuleScopeMode.AGGREGATE_OVER_TYPE:
        target = scope.get("document_type")
        if not target:
            msg = "AGGREGATE_OVER_TYPE requires document_type"
            raise WorkflowRuleScopeMismatchError(msg)
        target_uuid = UUID(str(target))
        matched = [
            ScopedDocument(
                document_id=d.uuid,
                document_type_id=d.document_type_id,
                document_type_slug=slug_by_document_type.get(d.document_type_id) if d.document_type_id else None,
            )
            for d in documents
            if d.document_type_id == target_uuid
        ]
        if not matched:
            return _empty_or_synthetic(on_empty)
        return [
            Combination(
                documents=matched,
                document_refs=_refs_for_documents(matched),
            )
        ]

    if mode == WorkflowRuleScopeMode.TUPLE_CARTESIAN:
        types = scope.get("document_types") or []
        if len(types) < 2:
            msg = "TUPLE_CARTESIAN requires document_types with at least 2 entries"
            raise WorkflowRuleScopeMismatchError(
                msg,
            )
        type_uuids = [UUID(str(t)) for t in types]
        groups: list[list[ScopedDocument]] = []
        for type_uuid in type_uuids:
            grouped = [
                ScopedDocument(
                    document_id=d.uuid,
                    document_type_id=d.document_type_id,
                    document_type_slug=slug_by_document_type.get(d.document_type_id) if d.document_type_id else None,
                )
                for d in documents
                if d.document_type_id == type_uuid
            ]
            if not grouped:
                return _empty_or_synthetic(on_empty)
            groups.append(grouped)
        combos: list[Combination] = []
        for tuple_ in product(*groups):
            docs = list(tuple_)
            combos.append(
                Combination(
                    documents=docs,
                    document_refs=_refs_for_documents(docs),
                )
            )
        return combos

    msg = f"unhandled mode: {mode.value}"
    raise WorkflowRuleScopeMismatchError(msg)


def _empty_or_synthetic(on_empty: WorkflowRuleOnEmpty) -> list[Combination]:
    """Return a synthetic combination representing an empty scope (spec §7.2)."""
    return [
        Combination(
            documents=[],
            document_refs={},
            is_synthetic_empty=True,
            synthetic_outcome=on_empty,
        )
    ]
