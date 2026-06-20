"""Deterministic ``x-source`` projection over an output JSON Schema.

Spec ``product/plans/case-output/case-output.md`` §4.1: each property of an output schema may
declare its source via the ``x-source`` extension keyword, reusing the rule
token grammar (``_shared/refs.py``):

- ``{{token}}``        → system token registry (``ProjectionContext.system_tokens``).
- ``@slug.path``       → extracted fields of the case documents (``path_resolver``).
- ``@rule.<slug>.path``→ the ``output`` of that rule's ``WorkflowRuleResult``(s).
- ``#kb_slug``         → NOT supported in E2: warning + delegated to the LLM.

Properties without ``x-source`` are collected as ``llm_pointers`` for the
synthesis agent. Resolution is tolerant: a source that cannot be resolved
projects ``null`` plus a warning — it is never delegated to the LLM (decision:
deterministic fields stay deterministic).

.. warning:: **"rule" is a RESERVED document-type slug for x-source.**
   ``@rule.<...>`` always resolves against rule results, so a DocumentType
   whose slug is literally ``rule`` can never be referenced from ``x-source``.

Provenance: every resolved field carries ``Citation``s keyed by the JSON
Pointer of the field (RFC 6901, e.g. ``/totals/amount``). For ``@rule`` refs
the citation points at the first document the result evaluated
(``document_refs = {slug: [ids]}``) with ``document_type_slug="rule"`` and
``sub_check_id=str(result.uuid)``. Persist citations with
``model_dump(mode="json")``.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared import path_resolver
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    MissingDocumentError,
    _parse_path,
    _walk_segments,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import (
    DocRef,
    parse_doc_refs,
    parse_tokens,
)

# Reserved slug: `@rule.<slug>` refs resolve against rule results, never docs.
RULE_REF_SLUG = "rule"

# Citation.value is informational — cap it so collection refs don't balloon
# the provenance JSONB with whole documents.
_CITATION_VALUE_MAX = 500


@dataclass
class ProjectionContext:
    """Cross-source inputs for one projection pass.

    ``documents`` follow the rule scope_resolver convention: ``document_id``,
    ``document_type_slug`` and ``extracted_fields`` already flattened from the
    ``{value, bbox}`` extraction wrappers (see ``flatten_extraction``).
    ``rule_results_by_slug`` is keyed by ``WorkflowRule.slug``.
    """

    documents: list[EvalDocumentInput] = field(default_factory=list)
    rule_results_by_slug: dict[str, list[WorkflowRuleResult]] = field(default_factory=dict)
    system_tokens: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectionResult:
    resolved: dict[str, Any] = field(default_factory=dict)
    citations: dict[str, list[Citation]] = field(default_factory=dict)
    llm_pointers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_sources(self) -> bool:
        """True when the schema declared at least one resolvable ``x-source``."""
        return bool(self.resolved)


def project_schema(schema: dict[str, Any], context: ProjectionContext) -> ProjectionResult:
    """Resolve every ``x-source``-annotated property of ``schema``.

    Walks ``properties`` recursively (nested objects produce pointers like
    ``/a/b``). Returns the resolved values keyed by JSON Pointer, their
    citations, the pointers left for the LLM, and non-blocking warnings.
    """
    result = ProjectionResult()
    _walk_properties(schema or {}, "", context, result)
    return result


def apply_resolved(base: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``base`` with each JSON Pointer set to its resolved value.

    Used to merge the deterministic layer over the LLM output — resolved
    values always win (anti-hallucination).
    """
    merged = copy.deepcopy(base)
    for pointer, value in resolved.items():
        node = merged
        segments = [_unescape_pointer(s) for s in pointer.split("/")[1:]]
        for segment in segments[:-1]:
            child = node.get(segment)
            if not isinstance(child, dict):
                child = {}
                node[segment] = child
            node = child
        node[segments[-1]] = value
    return merged


def flatten_extraction(fields: dict[str, Any]) -> dict[str, Any]:
    """Unwrap top-level ``{value, bbox}`` extraction shapes to the scalar value.

    Mirrors the flattening the analysis activities apply before building
    ``EvalDocumentInput`` for rules, so ``@invoice.total`` projects the scalar
    and not the wrapper dict.
    """
    if not isinstance(fields, dict):
        return fields
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, dict) and "value" in value and "bbox" in value:
            out[key] = value["value"]
        else:
            out[key] = value
    return out


# ── internals ────────────────────────────────────────────────────────────────


def _walk_properties(
    node: dict[str, Any],
    pointer: str,
    context: ProjectionContext,
    result: ProjectionResult,
) -> None:
    properties = node.get("properties")
    if not isinstance(properties, dict):
        return
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        child_pointer = f"{pointer}/{_escape_pointer(str(name))}"
        source = prop.get("x-source")
        if isinstance(source, str) and source.strip():
            _resolve_source(source.strip(), child_pointer, context, result)
            continue
        if prop.get("type") == "object" and isinstance(prop.get("properties"), dict):
            _walk_properties(prop, child_pointer, context, result)
            continue
        result.llm_pointers.append(child_pointer)


def _resolve_source(
    source: str,
    pointer: str,
    context: ProjectionContext,
    result: ProjectionResult,
) -> None:
    if "{{" in source:
        _resolve_token(source, pointer, context, result)
        return
    if source.startswith("#"):
        result.llm_pointers.append(pointer)
        result.warnings.append(
            f"{pointer}: '#kb' x-source is not supported in E2; field delegated to the LLM ({source!r})"
        )
        return
    if source.startswith("@"):
        refs = parse_doc_refs(source)
        if not refs:
            result.resolved[pointer] = None
            result.warnings.append(f"{pointer}: unparseable x-source ref {source!r}; resolved to null")
            return
        ref = refs[0]
        if ref.slug == RULE_REF_SLUG:
            _resolve_rule_ref(ref, pointer, context, result)
        else:
            _resolve_doc_ref(ref, pointer, context, result)
        return
    result.resolved[pointer] = None
    result.warnings.append(f"{pointer}: unrecognized x-source {source!r}; resolved to null")


def _resolve_token(
    source: str,
    pointer: str,
    context: ProjectionContext,
    result: ProjectionResult,
) -> None:
    tokens = parse_tokens(source)
    if not tokens:
        result.resolved[pointer] = None
        result.warnings.append(f"{pointer}: unparseable token x-source {source!r}; resolved to null")
        return
    name = tokens[0]
    if name not in context.system_tokens:
        result.resolved[pointer] = None
        result.warnings.append(f"{pointer}: unknown system token '{{{{{name}}}}}'; resolved to null")
        return
    # System tokens carry no citation: they don't trace back to a document.
    result.resolved[pointer] = context.system_tokens[name]


def _resolve_doc_ref(
    ref: DocRef,
    pointer: str,
    context: ProjectionContext,
    result: ProjectionResult,
) -> None:
    try:
        values = path_resolver.resolve(ref, context.documents, required=False)
    except MissingDocumentError:
        result.resolved[pointer] = None
        result.warnings.append(f"{pointer}: no document of type '{ref.slug}' in the case; resolved to null")
        return
    if not values:
        result.resolved[pointer] = None
        result.warnings.append(f"{pointer}: {ref.raw!r} matched no extracted field; resolved to null")
        return

    if ref.kind == "scalar":
        if len(values) > 1:
            result.warnings.append(
                f"{pointer}: {ref.raw!r} matched {len(values)} values for a scalar ref; using the first"
            )
        chosen = values[:1]
        result.resolved[pointer] = chosen[0].value
    else:
        chosen = values
        result.resolved[pointer] = [v.value for v in values]
    result.citations[pointer] = [_citation_from_resolved(v) for v in chosen]


def _resolve_rule_ref(
    ref: DocRef,
    pointer: str,
    context: ProjectionContext,
    result: ProjectionResult,
) -> None:
    # parse_doc_refs reads `@rule.credit_check.passed` as
    # DocRef(slug="rule", path="credit_check.passed") — the first path segment
    # is the rule slug, the remainder walks the result's output.
    raw_path = ref.path or ""
    rule_slug, _, rest = raw_path.partition(".")
    # `credit_check[].x` style: a bracket can ride on the first segment.
    if "[" in rule_slug:
        bracket = rule_slug.index("[")
        rest = rule_slug[bracket:] + (("." + rest) if rest else "")
        rule_slug = rule_slug[:bracket]
    if not rule_slug:
        result.resolved[pointer] = None
        result.warnings.append(f"{pointer}: {ref.raw!r} is missing the rule slug; resolved to null")
        return

    results = context.rule_results_by_slug.get(rule_slug) or []
    with_output = [r for r in results if r.output is not None]
    if not with_output:
        # Decision (spec §6): SKIPPED/FAILED/absent rule → null, never the LLM.
        result.resolved[pointer] = None
        result.warnings.append(
            f"{pointer}: rule '{rule_slug}' has no result with output in this run; resolved to null"
        )
        return

    expects_list = "[]" in rest
    values: list[Any] = []
    citations: list[Citation] = []
    for rule_result in with_output:
        walked = _walk_rule_output(rule_result.output, rest)
        if not walked:
            result.warnings.append(
                f"{pointer}: path '{rest or ''}' not found on output of rule '{rule_slug}' "
                f"(result {rule_result.uuid})"
            )
            continue
        document_id = _first_document_id(rule_result.document_refs)
        for walked_path, value in walked:
            values.append(value)
            if document_id is None:
                continue
            citations.append(
                Citation(
                    document_id=document_id,
                    document_type_slug=RULE_REF_SLUG,
                    field_path=walked_path,
                    value=_stringify(value),
                    sub_check_id=str(rule_result.uuid),
                )
            )
        if document_id is None:
            result.warnings.append(
                f"{pointer}: result {rule_result.uuid} of rule '{rule_slug}' has no document_refs; "
                "no citation emitted"
            )

    if not values:
        result.resolved[pointer] = None
        result.warnings.append(
            f"{pointer}: {ref.raw!r} resolved no value on rule '{rule_slug}'; resolved to null"
        )
        return

    if len(with_output) > 1 or expects_list:
        # Decision (spec §6): a rule evaluated over multiple documents
        # projects a LIST of values, one per result.
        result.resolved[pointer] = values
    else:
        if len(values) > 1:
            result.warnings.append(
                f"{pointer}: {ref.raw!r} matched {len(values)} values for a scalar ref; using the first"
            )
            citations = citations[:1]
        result.resolved[pointer] = values[0]
    if citations:
        result.citations[pointer] = citations


def _walk_rule_output(output: Any, rest: str) -> list[tuple[str, Any]]:
    if not rest:
        return [("", output)]
    return _walk_segments(output, _parse_path(rest))


def _first_document_id(document_refs: dict[str, Any] | None) -> UUID | None:
    """First document id of `{slug: [ids]}` — the doc the rule evaluated."""
    for ids in (document_refs or {}).values():
        if isinstance(ids, (list, tuple)) and ids:
            try:
                return ids[0] if isinstance(ids[0], UUID) else UUID(str(ids[0]))
            except (ValueError, TypeError):
                continue
    return None


def _citation_from_resolved(value: path_resolver.ResolvedValue) -> Citation:
    return Citation(
        document_id=value.document_id,
        document_type_slug=value.document_type_slug,
        field_path=value.field_path,
        value=_stringify(value.value),
    )


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text[:_CITATION_VALUE_MAX]


def _escape_pointer(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _unescape_pointer(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")
