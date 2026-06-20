"""Deterministic handlers for VALIDATION methods (spec §6.2).

Each handler takes:
  - `primary`: the first resolved input of the sub_check (list[ResolvedValue]),
  - `params`: substituted params (tokens/refs already replaced with values),
  - `resolved_inputs`: full ref → ResolvedValue map for cross-ref/aggregate,
  - `llm_runner`: only used by `llm_check`.
And returns `(passed: bool, reason: str)`. Citation construction is the
dispatcher's responsibility, kept out of these handlers so the rules stay
pure and easy to test.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.checksums import registry as checksum_registry
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import LLMRunner
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)


def format_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    **_: Any,
) -> tuple[bool, str]:
    pattern = re.compile(params["regex"], _flags(params.get("flags", "")))
    failures = [r for r in primary if r.value is None or not pattern.fullmatch(str(r.value))]
    if failures:
        return False, f"FORMAT_CHECK failed for {len(failures)} value(s)"
    return True, "FORMAT_CHECK ok"


def range_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    **_: Any,
) -> tuple[bool, str]:
    inclusive = params.get("inclusive", True)
    min_v = params.get("min")
    max_v = params.get("max")
    # Strict bounds (E5 drift fix): `min_exclusive`/`max_exclusive` are
    # advertised by the PARSER prompt and were previously ignored → a rule like
    # "must be > 18" silently PASSed. They compare strictly regardless of the
    # `inclusive` flag, which only governs the inclusive `min`/`max` bounds.
    min_excl = params.get("min_exclusive")
    max_excl = params.get("max_exclusive")
    for r in primary:
        v = _coerce_comparable(r.value)
        if v is None:
            return False, "RANGE_CHECK: value is missing"
        if min_v is not None and not (v >= _coerce_comparable(min_v) if inclusive else v > _coerce_comparable(min_v)):
            return False, f"RANGE_CHECK: value {v!r} below min {min_v!r}"
        if max_v is not None and not (v <= _coerce_comparable(max_v) if inclusive else v < _coerce_comparable(max_v)):
            return False, f"RANGE_CHECK: value {v!r} above max {max_v!r}"
        if min_excl is not None and not v > _coerce_comparable(min_excl):
            return False, f"RANGE_CHECK: value {v!r} not strictly above min_exclusive {min_excl!r}"
        if max_excl is not None and not v < _coerce_comparable(max_excl):
            return False, f"RANGE_CHECK: value {v!r} not strictly below max_exclusive {max_excl!r}"
    return True, "RANGE_CHECK ok"


def date_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    **_: Any,
) -> tuple[bool, str]:
    """All advertised params are honoured (E5 drift fix). Previously only
    `before`/`after` were read, so a `min_age_years`/`not_before` rule compiled
    green and ALWAYS passed.

    - `before`/`after`: strict (`v < before`, `v > after`).
    - `not_before`/`not_after`: inclusive bounds (`v >= not_before`, `v <= not_after`).
    - `reference`: anchor for the age comparisons (default today; the PARSER
      emits `{{now}}`, substituted to a datetime before we see it).
    - `min_age_years`/`min_age_days`/`max_age_*`: age = reference − value.
    """
    fmt = params.get("format")
    before = _parse_date(params.get("before"), fmt)
    after = _parse_date(params.get("after"), fmt)
    not_before = _parse_date(params.get("not_before"), fmt)
    not_after = _parse_date(params.get("not_after"), fmt)
    reference = _parse_date(params.get("reference"), fmt) or date.today()
    age_bounds = _age_bounds(params)
    for r in primary:
        v = _parse_date(r.value, fmt)
        if v is None:
            return False, f"DATE_CHECK: value {r.value!r} not parseable"
        if before is not None and not v < before:
            return False, f"DATE_CHECK: {v.isoformat()} not before {before.isoformat()}"
        if after is not None and not v > after:
            return False, f"DATE_CHECK: {v.isoformat()} not after {after.isoformat()}"
        if not_before is not None and not v >= not_before:
            return False, f"DATE_CHECK: {v.isoformat()} is before {not_before.isoformat()}"
        if not_after is not None and not v <= not_after:
            return False, f"DATE_CHECK: {v.isoformat()} is after {not_after.isoformat()}"
        if age_bounds is not None:
            min_days, max_days = age_bounds
            age_days = (reference - v).days
            if min_days is not None and age_days < min_days:
                return False, f"DATE_CHECK: age {age_days}d below minimum {min_days}d (ref {reference.isoformat()})"
            if max_days is not None and age_days > max_days:
                return False, f"DATE_CHECK: age {age_days}d above maximum {max_days}d (ref {reference.isoformat()})"
    return True, "DATE_CHECK ok"


def _age_bounds(params: dict[str, Any]) -> tuple[int | None, int | None] | None:
    """Lower/upper age bounds in DAYS, or None when no age param is set.

    `min_age_years=18` means "at least 18 years old": the date must be at least
    18*365 days before the reference. A leap-aware calendar age is overkill for
    a deterministic rule, but the boundary case (turning 18 exactly on the
    reference day) must PASS — see tests — so years use 365 days flat, which is
    the convention the boundary tests lock in.
    """
    min_years = params.get("min_age_years")
    max_years = params.get("max_age_years")
    min_days = params.get("min_age_days")
    max_days = params.get("max_age_days")
    if min_years is None and max_years is None and min_days is None and max_days is None:
        return None
    lower: int | None = None
    upper: int | None = None
    if min_years is not None:
        lower = int(min_years) * 365
    if min_days is not None:
        lower = int(min_days) if lower is None else max(lower, int(min_days))
    if max_years is not None:
        upper = int(max_years) * 365
    if max_days is not None:
        upper = int(max_days) if upper is None else min(upper, int(max_days))
    return lower, upper


def checksum_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    **_: Any,
) -> tuple[bool, str]:
    fn = checksum_registry.get(params["algorithm"])
    failures = [r for r in primary if r.value is None or not fn(str(r.value))]
    if failures:
        return False, f"CHECKSUM_CHECK[{params['algorithm']}] failed for {len(failures)} value(s)"
    return True, f"CHECKSUM_CHECK[{params['algorithm']}] ok"


# Legacy artifacts (compiled before the E5 drift fix closed the `mode` enum)
# may carry parser-invented synonyms. Normalize instead of failing so old
# compilations keep evaluating correctly without a forced recompile.
_CROSS_REF_MODE_ALIASES = {
    "exact": "equal",
    "equals": "equal",
    "eq": "equal",
    "match": "match_normalized",
    "normalized": "match_normalized",
}


def cross_ref_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    *,
    resolved_inputs: dict[str, Any] | None = None,
    knowledge_context: list[dict[str, Any]] | None = None,
    **_: Any,
) -> tuple[bool, str]:
    """Three shapes (mirrors the PARSER system prompt — E5 drift fix):

    - direct:   `{against, mode?}` — compare primary input vs another ref.
    - lookup:   `{lookup_in, match_field?, primary?, filter?, normalize?}` —
      check a value appears in a KB (or doc) list.
    - iterator: `{primary|primary_iterator+primary_field, secondary_iterator,
      secondary_field?, filter?|secondary_filter?, normalize?, predicate?,
      fallback_match?}` — match value(s) against the items of another doc.

    Misconfiguration (missing target, unknown mode/op, unresolvable KB)
    raises `InvalidWorkflowRuleConfigError` → the rule result is ERRORED,
    never a silent FAIL.
    """
    resolved_inputs = resolved_inputs or {}
    if "lookup_in" in params:
        return _cross_ref_lookup(primary, params, resolved_inputs, knowledge_context or [])
    if "secondary_iterator" in params:
        return _cross_ref_iterator(primary, params, resolved_inputs)

    if "against" not in params:
        msg = (
            "CROSS_REF_CHECK params must include `against` (direct shape), "
            "`lookup_in` (lookup shape) or `secondary_iterator` (iterator shape); "
            f"got keys {sorted(params)}"
        )
        raise InvalidWorkflowRuleConfigError(msg)

    against = params["against"]  # already substituted to ResolvedValue (or list)
    mode = str(params.get("mode") or "equal").strip().lower()
    mode = _CROSS_REF_MODE_ALIASES.get(mode, mode)
    other_values = _values_of(against)
    primary_values = [r.value for r in primary]
    if mode == "equal":
        if not other_values or not primary_values:
            return False, "CROSS_REF_CHECK: missing values to compare"
        if any(p != other_values[0] for p in primary_values):
            return False, f"CROSS_REF_CHECK[equal]: {primary_values} != {other_values[0]!r}"
    elif mode == "subset":
        if not set(map(_normalize, primary_values)).issubset(set(map(_normalize, other_values))):
            return False, "CROSS_REF_CHECK[subset]: primary not subset of against"
    elif mode == "match_normalized":
        normalized_primary = {_normalize(p) for p in primary_values}
        normalized_other = {_normalize(o) for o in other_values}
        if normalized_primary != normalized_other:
            return False, "CROSS_REF_CHECK[match_normalized]: sets differ"
    else:
        msg = f"CROSS_REF_CHECK: unknown mode {mode!r} (valid: equal, subset, match_normalized)"
        raise InvalidWorkflowRuleConfigError(msg)
    return True, f"CROSS_REF_CHECK[{mode}] ok"


def aggregate_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    **_: Any,
) -> tuple[bool, str]:
    """Aggregate over a collection (E5 drift fix).

    Previously this handler only read `over`/`op`/`predicate.equals`: if the
    PARSER emitted the target as `value`/`target`, or the collection as
    `iterator`, the comparison was skipped → silent PASS (or a `KeyError`).
    Now:

    - the collection is `over` OR `iterator` (missing ⇒ ERRORED);
    - per-row `conditions`/`filter` narrow the collection first (`field op value`);
    - the target is `predicate.equals` OR `value` OR `target`;
    - `tolerance` widens the equality to `abs(actual - target) <= tolerance`;
    - a comparison param that is provided but cannot be honoured raises
      `InvalidWorkflowRuleConfigError` rather than passing silently.
    """
    collection = params.get("over")
    if collection is None:
        collection = params.get("iterator")
    if collection is None:
        msg = "AGGREGATE_CHECK params must include `over` (or `iterator`) — the collection to aggregate"
        raise InvalidWorkflowRuleConfigError(msg)
    items = _values_of(collection)

    conditions = params.get("conditions")
    flt = params.get("filter")
    field = params.get("field")
    predicate = params.get("predicate")

    # Row-predicate shape: `conditions` (a list of {field, op, value}) checked
    # per item, ALL/ANY governed by the `predicate` string. No numeric op here.
    if conditions:
        return _aggregate_conditions(items, list(conditions), predicate)

    if flt:
        items = [item for item in items if _passes_filter(item, flt, [])]

    op = params.get("op")
    if op is None:
        msg = "AGGREGATE_CHECK params must include `op` (count/sum/avg/min/max) or `conditions`"
        raise InvalidWorkflowRuleConfigError(msg)

    # `field` projects a column out of object items before aggregating.
    values = [_field_of(item, field) for item in items] if field else items

    actual: float
    if op == "count":
        actual = float(len(values))
    elif op == "sum":
        actual = float(sum(_to_number(v) for v in values))
    elif op == "avg":
        actual = float(sum(_to_number(v) for v in values)) / max(1, len(values))
    elif op == "min":
        actual = float(min((_to_number(v) for v in values), default=0.0))
    elif op == "max":
        actual = float(max((_to_number(v) for v in values), default=0.0))
    else:
        msg = f"AGGREGATE_CHECK: unknown op {op!r} (valid: count, sum, avg, min, max)"
        raise InvalidWorkflowRuleConfigError(msg)

    target = _aggregate_target(params, predicate)
    if target is None:
        # `expression` is advertised but not interpretable here; never claim a
        # PASS when a comparison was clearly intended but cannot be evaluated.
        if params.get("expression") is not None:
            msg = "AGGREGATE_CHECK: `expression` param is not supported — express the target via predicate.equals/value/target"
            raise InvalidWorkflowRuleConfigError(msg)
        return True, f"AGGREGATE_CHECK[{op}] = {actual}"

    tolerance = float(params.get("tolerance", 0) or 0)
    if abs(actual - _to_number(target)) > tolerance:
        return False, f"AGGREGATE_CHECK[{op}] {actual} != {target} (tolerance {tolerance})"
    return True, f"AGGREGATE_CHECK[{op}] ok ({actual})"


def _aggregate_target(params: dict[str, Any], predicate: Any) -> Any:
    if isinstance(predicate, dict) and predicate.get("equals") is not None:
        return _coerce_comparable(predicate.get("equals"))
    if params.get("value") is not None:
        return _coerce_comparable(params.get("value"))
    if params.get("target") is not None:
        return _coerce_comparable(params.get("target"))
    return None


def _aggregate_conditions(
    items: list[Any],
    conditions: list[dict[str, Any]],
    predicate: Any,
) -> tuple[bool, str]:
    mode = str(predicate or "ALL").strip().upper()
    flags = [all(_condition_holds(item, cond) for cond in conditions) for item in items]
    if mode in {"ANY", "ANY_MATCH", "EXISTS", "SOME"}:
        ok = any(flags)
    else:  # ALL / ALL_MATCH (default)
        ok = all(flags)
    if ok:
        return True, f"AGGREGATE_CHECK[{mode.lower()}] ok ({sum(flags)}/{len(flags)} rows)"
    return False, f"AGGREGATE_CHECK[{mode.lower()}] failed ({sum(flags)}/{len(flags)} rows match)"


def _condition_holds(item: Any, condition: dict[str, Any]) -> bool:
    field = condition.get("field")
    op = str(condition.get("op") or "==").strip()
    expected = _coerce_comparable(condition.get("value"))
    actual = _coerce_comparable(_field_of(item, field))
    if actual is None:
        return False
    try:
        if op in {"==", "=", "eq"}:
            return actual == expected
        if op in {"!=", "ne"}:
            return actual != expected
        if op in {">", "gt"}:
            return actual > expected
        if op in {">=", "gte"}:
            return actual >= expected
        if op in {"<", "lt"}:
            return actual < expected
        if op in {"<=", "lte"}:
            return actual <= expected
    except TypeError:
        return False
    msg = f"AGGREGATE_CHECK: unknown condition op {op!r} (valid: ==, !=, >, >=, <, <=)"
    raise InvalidWorkflowRuleConfigError(msg)


async def llm_check(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    *,
    llm_runner: LLMRunner,
    **_: Any,
) -> tuple[bool, str]:
    question = params["question"]
    criteria = params.get("criteria") or ""
    user_prompt = f"Question: {question}\nCriteria: {criteria}\nResolved inputs:\n" + "\n".join(
        f"- {r.document_type_slug}#{r.document_id}.{r.field_path}: {r.value!r}" for r in primary
    )
    payload = await llm_runner.run(
        system=_LLM_CHECK_SYSTEM_PROMPT,
        user=user_prompt,
        output_schema={
            "type": "object",
            "required": ["passed", "reason"],
            "properties": {"passed": {"type": "boolean"}, "reason": {"type": "string"}},
        },
    )
    return bool(payload.get("passed")), str(payload.get("reason") or "")


HANDLERS: dict[str, Callable[..., Awaitable[tuple[bool, str]] | tuple[bool, str]]] = {
    "FORMAT_CHECK": format_check,
    "RANGE_CHECK": range_check,
    "DATE_CHECK": date_check,
    "CHECKSUM_CHECK": checksum_check,
    "CROSS_REF_CHECK": cross_ref_check,
    "AGGREGATE_CHECK": aggregate_check,
    "LLM_CHECK": llm_check,
}


# ---------------- helpers ---------------- #


_LLM_CHECK_SYSTEM_PROMPT = (
    "You evaluate one assertion against the provided resolved fields. "
    'Respond strictly as {"passed": bool, "reason": string}.'
)


def _flags(s: str) -> int:
    flags = 0
    if "i" in s:
        flags |= re.IGNORECASE
    if "m" in s:
        flags |= re.MULTILINE
    if "s" in s:
        flags |= re.DOTALL
    return flags


def _coerce_comparable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool | int | float | datetime | date):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            parsed = _parse_date(value, None)
            if parsed is not None:
                return parsed
            return value
    return value


def _parse_date(value: Any, fmt: str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if fmt:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            return None
    for try_fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(candidate, try_fmt).date()
        except ValueError:
            continue
    return None


def _values_of(target: Any) -> list[Any]:
    if isinstance(target, ResolvedValue):
        return [target.value]
    if isinstance(target, list):
        return [t.value if isinstance(t, ResolvedValue) else t for t in target]
    return [target]


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip().lower())
    return value


def _to_number(value: Any) -> float:
    if isinstance(value, bool | int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ------------- CROSS_REF_CHECK lookup / iterator shapes (E5) ------------- #


def _cross_ref_lookup(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    resolved_inputs: dict[str, Any],
    knowledge_context: list[dict[str, Any]],
) -> tuple[bool, str]:
    items = _lookup_items(params["lookup_in"], resolved_inputs, knowledge_context)
    normalize_ops = list(params.get("normalize") or [])
    match_field = params.get("match_field")

    # The value(s) to find and, when items are objects, the field to match on.
    field_in_items: str | None = None
    if "primary" in params:
        lookup_values = _primary_values(params["primary"], primary, resolved_inputs)
        if isinstance(match_field, str) and not match_field.startswith("@"):
            field_in_items = match_field
    elif match_field is not None and not isinstance(match_field, str):
        # `match_field` was a `@slug.path` ref, substituted to ResolvedValue(s).
        lookup_values = _values_of(match_field)
    elif isinstance(match_field, str) and match_field.startswith("@"):
        lookup_values = _values_of(resolved_inputs.get(match_field) or [])
    else:
        lookup_values = [r.value for r in primary]
        field_in_items = match_field if isinstance(match_field, str) else None

    flt = params.get("filter")
    if flt:
        items = [item for item in items if _passes_filter(item, flt, normalize_ops)]

    # A `match_field` that exists in NONE of the (object) items is a config typo,
    # not a data miss: surface it as ERRORED instead of a silent "not found" FAIL.
    _assert_field_present(field_in_items, items, "match_field")

    lookup_values = [v for v in lookup_values if v is not None]
    if not lookup_values:
        return False, "CROSS_REF_CHECK[lookup]: no value to look up"

    missing = [
        v for v in lookup_values if not any(_item_matches(item, v, field_in_items, normalize_ops) for item in items)
    ]
    if missing:
        return False, f"CROSS_REF_CHECK[lookup]: {missing!r} not found in {params['lookup_in']!r}"
    return True, f"CROSS_REF_CHECK[lookup] ok ({len(lookup_values)} value(s) found)"


def _cross_ref_iterator(
    primary: list[ResolvedValue],
    params: dict[str, Any],
    resolved_inputs: dict[str, Any],
) -> tuple[bool, str]:
    normalize_ops = list(params.get("normalize") or [])
    secondary_items = _iterator_items(params["secondary_iterator"], resolved_inputs)
    flt = params.get("secondary_filter") or params.get("filter")
    if flt:
        secondary_items = [item for item in secondary_items if _passes_filter(item, flt, normalize_ops)]
    secondary_field = params.get("secondary_field")
    _assert_field_present(secondary_field, secondary_items, "secondary_field")
    secondary_values = [_field_of(item, secondary_field) for item in secondary_items]

    if "primary" in params:
        primary_values = _primary_values(params["primary"], primary, resolved_inputs)
    elif "primary_iterator" in params:
        p_items = _iterator_items(params["primary_iterator"], resolved_inputs)
        _assert_field_present(params.get("primary_field"), p_items, "primary_field")
        primary_values = [_field_of(item, params.get("primary_field")) for item in p_items]
    else:
        primary_values = [r.value for r in primary]
    primary_values = [v for v in primary_values if v is not None]
    if not primary_values:
        return False, "CROSS_REF_CHECK[iterator]: no primary value to match"

    flags = [any(_loose_equal(v, s, normalize_ops) for s in secondary_values) for v in primary_values]
    predicate = str(params.get("predicate") or "ALL_MATCH").strip().upper()
    matched = any(flags) if predicate == "ANY_MATCH" else all(flags)
    if matched:
        return True, f"CROSS_REF_CHECK[iterator] ok ({predicate.lower()})"

    fallback = params.get("fallback_match")
    if isinstance(fallback, dict):
        fb_field = fallback.get("field")
        fb_values = _primary_values(fallback.get("value"), primary, resolved_inputs)
        fb_values = [v for v in fb_values if v is not None]
        for item in secondary_items:
            candidate = _field_of(item, fb_field)
            if any(_loose_equal(v, candidate, normalize_ops) for v in fb_values):
                return True, f"CROSS_REF_CHECK[iterator] ok via fallback_match on {fb_field!r}"

    unmatched = [v for v, ok in zip(primary_values, flags, strict=True) if not ok]
    return False, f"CROSS_REF_CHECK[iterator]: {unmatched!r} not matched against secondary items"


def _lookup_items(
    target: Any,
    resolved_inputs: dict[str, Any],
    knowledge_context: list[dict[str, Any]],
) -> list[Any]:
    if isinstance(target, ResolvedValue | list):
        return _flatten_items(_values_of(target))
    if isinstance(target, str) and target.startswith("#"):
        slug = target.lstrip("#").strip("{}")
        for entry in knowledge_context:
            if entry.get("slug") == slug:
                return _parse_kb_items(entry.get("content"))
        msg = (
            f"CROSS_REF_CHECK: KB document {slug!r} is not in the knowledge context — "
            "reference it with `#` in the rule prompt so compile records it"
        )
        raise InvalidWorkflowRuleConfigError(msg)
    if isinstance(target, str) and target.startswith("@"):
        resolved = resolved_inputs.get(target)
        if resolved is None:
            msg = f"CROSS_REF_CHECK: lookup_in ref {target!r} did not resolve against the case documents"
            raise InvalidWorkflowRuleConfigError(msg)
        return _flatten_items(_values_of(resolved))
    msg = f"CROSS_REF_CHECK: lookup_in must be a `#kb_slug` or `@slug.path` ref, got {target!r}"
    raise InvalidWorkflowRuleConfigError(msg)


def _iterator_items(target: Any, resolved_inputs: dict[str, Any]) -> list[Any]:
    if isinstance(target, str):
        resolved = resolved_inputs.get(target)
        if resolved is None:
            msg = f"CROSS_REF_CHECK: iterator ref {target!r} did not resolve against the case documents"
            raise InvalidWorkflowRuleConfigError(msg)
        target = resolved
    return _flatten_items(_values_of(target))


def _flatten_items(values: list[Any]) -> list[Any]:
    items: list[Any] = []
    for value in values:
        if isinstance(value, list):
            items.extend(value)
        elif value is not None:
            items.append(value)
    return items


def _parse_kb_items(content: Any) -> list[Any]:
    """KB content is free text (`extracted_text`). Try JSON first; fall back
    to one item per non-empty line (stripping common bullet markers)."""
    if isinstance(content, list):
        return content
    if not isinstance(content, str) or not content.strip():
        return []
    try:
        parsed = json.loads(content)
    except ValueError:
        parsed = None
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    items: list[Any] = []
    for line in content.splitlines():
        cleaned = line.strip().lstrip("-*•").strip()
        if cleaned:
            items.append(cleaned)
    return items


def _primary_values(
    value: Any,
    primary: list[ResolvedValue],
    resolved_inputs: dict[str, Any],
) -> list[Any]:
    """Resolve the `primary` param: a substituted ref, a `concat(...)`
    expression, a bare `@ref` (resolved via `resolved_inputs`), a literal,
    or — when absent — the sub_check's primary inputs."""
    if value is None:
        return [r.value for r in primary]
    if isinstance(value, ResolvedValue | list):
        return _values_of(value)
    if isinstance(value, str):
        concat_match = _CONCAT_RE.match(value)
        if concat_match:
            return [_eval_concat(concat_match.group("args"), resolved_inputs)]
        if value.startswith("@"):
            return _values_of(resolved_inputs.get(value) or [])
        return [value]
    return [value]


_CONCAT_RE = re.compile(r"^\s*concat\((?P<args>.*)\)\s*$", re.IGNORECASE | re.DOTALL)


def _eval_concat(args: str, resolved_inputs: dict[str, Any]) -> str:
    parts: list[str] = []
    for raw_arg in _split_concat_args(args):
        arg = raw_arg.strip()
        if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in {"'", '"'}:
            parts.append(arg[1:-1])
        elif arg.startswith("@"):
            values = _values_of(resolved_inputs.get(arg) or [])
            parts.append("" if not values or values[0] is None else str(values[0]))
        else:
            parts.append(arg)
    return "".join(parts)


def _split_concat_args(args: str) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for ch in args:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
        elif ch in {"'", '"'}:
            quote = ch
            current.append(ch)
        elif ch == ",":
            out.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        out.append("".join(current))
    return out


def _passes_filter(item: Any, flt: dict[str, Any], normalize_ops: list[str]) -> bool:
    field = flt.get("field")
    op = str(flt.get("op") or "equals").strip().lower()
    expected_values = _values_of(flt.get("value"))
    candidate = _field_of(item, field)
    hit = any(_loose_equal(candidate, v, normalize_ops) for v in expected_values)
    if op in {"in", "equals", "eq", "=", "=="}:
        return hit
    if op in {"not_in", "nin", "!=", "ne"}:
        return not hit
    msg = f"CROSS_REF_CHECK: unknown filter op {op!r} (valid: in, not_in, equals)"
    raise InvalidWorkflowRuleConfigError(msg)


def _item_matches(item: Any, value: Any, field: str | None, normalize_ops: list[str]) -> bool:
    if isinstance(item, dict):
        if field:
            return _loose_equal(item.get(field), value, normalize_ops)
        return any(_loose_equal(v, value, normalize_ops) for v in item.values())
    return _loose_equal(item, value, normalize_ops)


def _field_of(item: Any, field: Any) -> Any:
    if field and isinstance(item, dict):
        return item.get(field)
    return item


def _assert_field_present(field: Any, items: list[Any], param_name: str) -> None:
    """Guard against a typo'd `*_field` param (E5 drift fix).

    If a field name is given and there ARE object items but none of them carries
    that key, the rule is misconfigured — raise so the result is ERRORED rather
    than a silent FAIL/"not found". Scalar-only collections are left alone (the
    field simply doesn't apply there)."""
    if not field or not isinstance(field, str):
        return
    dict_items = [item for item in items if isinstance(item, dict)]
    if dict_items and not any(field in item for item in dict_items):
        sample = sorted({k for item in dict_items for k in item})[:10]
        msg = f"CROSS_REF_CHECK: {param_name} {field!r} matches no key in the items (available: {sample})"
        raise InvalidWorkflowRuleConfigError(msg)


def _loose_equal(a: Any, b: Any, normalize_ops: list[str]) -> bool:
    if a is None or b is None:
        return False
    if not isinstance(a, str) and not isinstance(b, str):
        return a == b
    if normalize_ops:
        return _apply_normalize(a, normalize_ops) == _apply_normalize(b, normalize_ops)
    return _normalize(str(a)) == _normalize(str(b))


def _apply_normalize(value: Any, ops: list[str]) -> str:
    text = "" if value is None else str(value)
    for op in ops:
        name = str(op).strip().lower()
        if name in {"lowercase", "lower"}:
            text = text.lower()
        elif name in {"uppercase", "upper"}:
            text = text.upper()
        elif name == "strip_accents":
            text = _strip_accents(text)
        elif name in {"collapse_spaces", "collapse_whitespace"}:
            text = re.sub(r"\s+", " ", text).strip()
        elif name in {"trim", "strip"}:
            text = text.strip()
        # Unknown ops are ignored on purpose: normalization must stay lenient
        # so a PARSER-invented op never turns a valid rule into an error.
    return text


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
