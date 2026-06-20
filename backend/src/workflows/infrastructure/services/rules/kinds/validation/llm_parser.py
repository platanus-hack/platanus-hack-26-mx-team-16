"""LLM-based PARSER agent that decomposes a VALIDATION prompt into tree+sub_checks.

The PARSER takes the natural-language rule prompt plus the catalogues
(available doctypes, KB slugs, tokens) and returns a structured assertion
tree the dispatcher can execute. The parser_runner is an `LLMRunner`; tests
inject a `StaticLLMRunner` with a recorded payload, prod injects the real
runner. We post-validate every payload regardless of source so a hallucinated
sub_check or invalid params can never make it into the artifact.

Default behaviour with the stock `StaticLLMRunner` (no tree wired): the parser
falls back to a single `LLM_CHECK` sub_check that bundles the original prompt
as the question. This keeps compile productive while real PARSER agents land.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    LLMRunner,
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import (
    parse_doc_refs,
)
from src.workflows.infrastructure.services.rules.kinds.validation.methods import (
    known_methods,
    validate_params,
)


_PARSER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["tree", "sub_checks"],
    "properties": {
        "tree": {
            "type": "object",
            "description": (
                "Boolean tree. Either a leaf `{ref: <sub_check.id>}` or a "
                "node `{op: AND|OR|NOT, children: [...]}`. NOT must have "
                "exactly one child."
            ),
        },
        "sub_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "method", "inputs", "params"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Stable string id (e.g. 'c1'); referenced by tree leaves.",
                    },
                    "description": {"type": "string"},
                    "inputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of `@slug.path` refs taken verbatim from the prompt.",
                    },
                    "tokens": {"type": "array", "items": {"type": "string"}},
                    "knowledge_refs": {"type": "array", "items": {"type": "string"}},
                    "method": {
                        "type": "string",
                        "enum": [
                            "FORMAT_CHECK",
                            "RANGE_CHECK",
                            "DATE_CHECK",
                            "CHECKSUM_CHECK",
                            "CROSS_REF_CHECK",
                            "AGGREGATE_CHECK",
                            "LLM_CHECK",
                        ],
                    },
                    "params": {"type": "object"},
                },
            },
        },
    },
}


@dataclass
class ParserResult:
    tree: dict[str, Any]
    sub_checks: list[dict[str, Any]]


@dataclass
class ValidationParser:
    """Wraps an LLMRunner that returns `{tree, sub_checks}` for a VALIDATION prompt."""

    # Default falls back to the prompt-as-question fallback; bootstrap rewires
    # this to an AgnoLLMRunner so prod actually decomposes the prompt.
    llm_runner: LLMRunner = field(default_factory=lambda: StaticLLMRunner(payload={}))

    async def parse(
        self,
        *,
        prompt: str,
        available_slugs: list[str],
        kb_slugs: list[str],
        tokens: list[str],
    ) -> ParserResult:
        user_payload = json.dumps(
            {
                "prompt": prompt,
                "available_slugs": available_slugs,
                "kb_slugs": kb_slugs,
                "tokens": tokens,
            },
            ensure_ascii=False,
        )
        payload = await self.llm_runner.run(
            system=_PARSER_SYSTEM_PROMPT,
            user=user_payload,
            output_schema=_PARSER_OUTPUT_SCHEMA,
        )

        if not _looks_like_parser_payload(payload):
            payload = _fallback_payload(prompt)

        tree = payload.get("tree")
        sub_checks_raw = payload.get("sub_checks")
        if not isinstance(tree, dict) or not isinstance(sub_checks_raw, list):
            msg = "ValidationParser: response must include {tree: object, sub_checks: array}"
            raise InvalidWorkflowRuleConfigError(msg)

        normalized = [_normalize_sub_check(sc, prompt) for sc in sub_checks_raw]
        _validate_sub_checks(
            normalized,
            prompt=prompt,
            available_slugs=available_slugs,
            tokens=tokens,
            kb_slugs=kb_slugs,
        )
        _validate_tree(tree, sub_checks=normalized)
        return ParserResult(tree=tree, sub_checks=normalized)


def _looks_like_parser_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and "tree" in payload and "sub_checks" in payload


def _fallback_payload(prompt: str) -> dict[str, Any]:
    return {
        "tree": {"ref": "c1"},
        "sub_checks": [
            {
                "id": "c1",
                "description": prompt[:160].strip() or "Validate prompt",
                "inputs": [],
                "tokens": [],
                "knowledge_refs": [],
                "method": "LLM_CHECK",
                "params": {"question": prompt},
            }
        ],
    }


def _strip_nulls(value: Any) -> Any:
    """Drop null-valued keys so an optional param emitted as `null` by the PARSER
    LLM reads as "not provided" (handlers all use `params.get(...)`), instead of
    tripping the method schema's typed properties (e.g. `{"type": "string"}`)."""
    if isinstance(value, dict):
        return {k: _strip_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nulls(v) for v in value]
    return value


def _normalize_sub_check(sc: Any, prompt: str) -> dict[str, Any]:
    if not isinstance(sc, dict):
        msg = f"ValidationParser: each sub_check must be an object, got {type(sc).__name__}"
        raise InvalidWorkflowRuleConfigError(msg)
    return {
        "id": str(sc.get("id") or ""),
        "description": str(sc.get("description") or ""),
        "inputs": list(sc.get("inputs") or []),
        "tokens": list(sc.get("tokens") or []),
        "knowledge_refs": list(sc.get("knowledge_refs") or []),
        "method": str(sc.get("method") or ""),
        "params": _strip_nulls(dict(sc.get("params") or {})),
    }


def _validate_sub_checks(
    sub_checks: list[dict[str, Any]],
    *,
    prompt: str,
    available_slugs: list[str],
    tokens: list[str],
    kb_slugs: list[str],
) -> None:
    if not sub_checks:
        msg = "ValidationParser: at least one sub_check is required"
        raise InvalidWorkflowRuleConfigError(msg)

    seen_ids: set[str] = set()
    methods = known_methods()
    available_set = set(available_slugs)
    tokens_set = set(tokens)
    kb_slugs_set = set(kb_slugs)

    prompt_refs_raw = {ref.raw for ref in parse_doc_refs(prompt)}

    for sc in sub_checks:
        sc_id = sc["id"]
        if not sc_id:
            msg = "ValidationParser: sub_check missing id"
            raise InvalidWorkflowRuleConfigError(msg)
        if sc_id in seen_ids:
            msg = f"ValidationParser: duplicate sub_check id {sc_id!r}"
            raise InvalidWorkflowRuleConfigError(msg)
        seen_ids.add(sc_id)

        method = sc["method"]
        if method not in methods:
            msg = f"ValidationParser: unknown method {method!r} in sub_check {sc_id!r}"
            raise InvalidWorkflowRuleConfigError(msg)
        validate_params(method, sc["params"])

        # Refs declared in sub_check.inputs must exist in the prompt and resolve to known slugs.
        for raw in sc["inputs"]:
            if not isinstance(raw, str) or not raw.startswith("@"):
                msg = f"ValidationParser: sub_check {sc_id!r} input {raw!r} must be a `@{{slug}}` ref"
                raise InvalidWorkflowRuleConfigError(msg)
            if raw not in prompt_refs_raw:
                msg = f"ValidationParser: sub_check {sc_id!r} references {raw!r} not present in prompt"
                raise InvalidWorkflowRuleConfigError(msg)
            input_refs = parse_doc_refs(raw)
            for ref in input_refs:
                if ref.slug not in available_set:
                    msg = f"ValidationParser: sub_check {sc_id!r} input slug {ref.slug!r} unknown"
                    raise InvalidWorkflowRuleConfigError(msg)

        for token in sc["tokens"]:
            if token not in tokens_set:
                msg = f"ValidationParser: sub_check {sc_id!r} token {token!r} not in prompt"
                raise InvalidWorkflowRuleConfigError(msg)

        for kb_slug in sc["knowledge_refs"]:
            if kb_slug not in kb_slugs_set:
                msg = f"ValidationParser: sub_check {sc_id!r} kb_ref {kb_slug!r} not in prompt"
                raise InvalidWorkflowRuleConfigError(msg)

        # Any `@`-style ref inside params must use a known slug. We do NOT
        # require it to be declared in this sub_check's `inputs` or even to
        # appear verbatim in the prompt: the PARSER often synthesises iterator
        # refs (e.g. `@contract.partes[]`) and collection refs derived from
        # the array fields the user wrote (e.g. `@contract.partes[].nombre`).
        # The dispatcher fails at evaluate time if a path doesn't actually
        # resolve.
        for raw in _collect_param_refs(sc["params"]):
            for parsed in parse_doc_refs(raw):
                if parsed.slug not in available_set:
                    msg = (
                        f"ValidationParser: sub_check {sc_id!r} params reference slug {parsed.slug!r} which is unknown"
                    )
                    raise InvalidWorkflowRuleConfigError(msg)


def _collect_param_refs(params: dict[str, Any]) -> set[str]:
    refs: set[str] = set()

    def _walk(value: Any) -> None:
        if isinstance(value, str):
            for ref in parse_doc_refs(value):
                refs.add(ref.raw)
        elif isinstance(value, dict):
            for v in value.values():
                _walk(v)
        elif isinstance(value, list):
            for v in value:
                _walk(v)

    _walk(params)
    return refs


def _validate_tree(node: Any, *, sub_checks: list[dict[str, Any]]) -> None:
    if not isinstance(node, dict):
        msg = f"ValidationParser: tree node must be object, got {type(node).__name__}"
        raise InvalidWorkflowRuleConfigError(msg)
    if "ref" in node:
        ref = node["ref"]
        ids = {sc["id"] for sc in sub_checks}
        if ref not in ids:
            msg = f"ValidationParser: tree leaf ref {ref!r} not found in sub_checks"
            raise InvalidWorkflowRuleConfigError(msg)
        return
    op = node.get("op")
    if op not in {"AND", "OR", "NOT"}:
        msg = f"ValidationParser: tree node must have op in {{AND, OR, NOT}}, got {op!r}"
        raise InvalidWorkflowRuleConfigError(msg)
    children = node.get("children")
    if not isinstance(children, list) or not children:
        msg = f"ValidationParser: tree {op} requires non-empty children"
        raise InvalidWorkflowRuleConfigError(msg)
    if op == "NOT" and len(children) != 1:
        msg = "ValidationParser: NOT requires exactly one child"
        raise InvalidWorkflowRuleConfigError(msg)
    for child in children:
        _validate_tree(child, sub_checks=sub_checks)


_PARSER_SYSTEM_PROMPT = (
    "You are a rule compiler. Decompose the user's VALIDATION prompt into a "
    "boolean tree of AND/OR/NOT over typed sub_checks. Output strictly the "
    "JSON object described by the schema, with NO prose or fencing.\n\n"
    "Tree shape:\n"
    ' - Each leaf is `{"ref": "<sub_check.id>"}` (the id of one sub_check).\n'
    ' - Each internal node is `{"op": "AND"|"OR"|"NOT", "children": [...]}`.\n'
    " - NOT must have EXACTLY one child.\n\n"
    "Each sub_check is `{id, description, inputs, tokens, knowledge_refs, method, params}`:\n"
    " - `id` is a stable short string (use `c1`, `c2`, …) referenced by the tree.\n"
    " - `inputs` is an array of `@slug.path` refs copied VERBATIM from the prompt.\n"
    " - `tokens` lists `{{name}}` tokens used (without the braces) and must be ones the user wrote.\n"
    " - `knowledge_refs` lists `#slug` KB slugs used (without the `#`).\n"
    " - `method` ∈ {FORMAT_CHECK, RANGE_CHECK, DATE_CHECK, CHECKSUM_CHECK, "
    "CROSS_REF_CHECK, AGGREGATE_CHECK, LLM_CHECK}.\n"
    " - `params` is method-specific. Common shapes:\n"
    "     FORMAT_CHECK    → {regex, flags?}\n"
    "     RANGE_CHECK     → {min?, max?, inclusive?, min_exclusive?, max_exclusive?}\n"
    "     DATE_CHECK      → {before?, after?, not_before?, min_age_years?, min_age_days?, reference?, format?}\n"
    "     CHECKSUM_CHECK  → {algorithm}  (e.g. rut_chile_mod11, nit_bolivia_mod11, ci_bolivia, "
    "nit_colombia_mod11, cc_colombia, luhn_credit_card, iso_iban_mod97)\n"
    "     CROSS_REF_CHECK → one of three shapes:\n"
    "       · direct:   {against: '@slug.path', mode?: 'equal'|'subset'|'match_normalized'} "
    "(mode defaults to 'equal')\n"
    "       · lookup:   {lookup_in: '#kb_slug' | '@slug.path', match_field?, primary?, filter?, normalize?} "
    "(checks the primary/match_field value appears in the looked-up list; match_field names the field "
    "inside each list item when items are objects)\n"
    "       · iterator: {primary: '@slug.path' | 'concat(@a.x, \" \", @a.y)' | primary_iterator+primary_field, "
    "secondary_iterator: '@slug.items[]', secondary_field, filter?|secondary_filter? "
    "({field, op: 'in'|'equals', value}), normalize? (lowercase|strip_accents|collapse_spaces|trim), "
    "predicate? ('ANY_MATCH'|'ALL_MATCH'), fallback_match? ({field, value})}\n"
    "     AGGREGATE_CHECK → {iterator|over, predicate?, op?, field?, value?, expression?, conditions?, filter?, target?, tolerance?}\n"
    "     LLM_CHECK       → {question?, criteria?, expected_values?, requires_visual_context?, cite_from?, topic?}\n"
    "Pick the most specific deterministic method when possible; fall back to LLM_CHECK only for "
    "subjective semantic checks. Always emit at least one sub_check."
)
