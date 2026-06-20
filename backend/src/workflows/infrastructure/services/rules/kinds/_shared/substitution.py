"""Replace `{{token}}` / `@{slug}.path` placeholders inside a `params` dict.

The dispatcher calls this once per sub_check before invoking a method handler,
so handlers never see template strings. Substitution is full-string only:
a value either *is* a recognized placeholder (replaced with the resolved
value, possibly non-string) or it's left as-is.
"""

from __future__ import annotations

import re
from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)

_TOKEN_FULL_RE = re.compile(r"^\s*\{\{\s*([A-Za-z_][\w.]*)\s*\}\}\s*$")
# Accepts both `@{slug}.path` and the bare `@slug.path` the PARSER actually
# emits (it copies refs VERBATIM from prompts) — mirrors `refs._DOC_REF_RE`.
_DOC_REF_FULL_RE = re.compile(
    r"^\s*(@(?:\{[a-z0-9][a-z0-9_-]*\}|[a-z0-9][a-z0-9_-]*)(?:\.[A-Za-z_][\w]*|\[\d*\])*)\s*$"
)


def substitute(
    params: dict[str, Any],
    *,
    resolved_inputs: dict[str, ResolvedValue | list[ResolvedValue]],
    resolved_tokens: dict[str, Any],
    sub_check_id: str,
) -> dict[str, Any]:
    return _walk(params, resolved_inputs=resolved_inputs, resolved_tokens=resolved_tokens, sub_check_id=sub_check_id)


def _walk(
    value: Any,
    *,
    resolved_inputs: dict[str, ResolvedValue | list[ResolvedValue]],
    resolved_tokens: dict[str, Any],
    sub_check_id: str,
) -> Any:
    if isinstance(value, str):
        token_match = _TOKEN_FULL_RE.match(value)
        if token_match:
            name = token_match.group(1)
            if name not in resolved_tokens:
                msg = (
                    f"sub_check {sub_check_id!r} params reference token {{{{{name}}}}} "
                    "but it was not declared in `tokens`"
                )
                raise InvalidWorkflowRuleConfigError(msg)
            return resolved_tokens[name]
        ref_match = _DOC_REF_FULL_RE.match(value)
        if ref_match:
            ref = ref_match.group(1)
            if ref not in resolved_inputs:
                msg = f"sub_check {sub_check_id!r} params reference {ref!r} but it was not declared in `inputs`"
                raise InvalidWorkflowRuleConfigError(msg)
            return resolved_inputs[ref]
        return value
    if isinstance(value, dict):
        return {
            k: _walk(v, resolved_inputs=resolved_inputs, resolved_tokens=resolved_tokens, sub_check_id=sub_check_id)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _walk(v, resolved_inputs=resolved_inputs, resolved_tokens=resolved_tokens, sub_check_id=sub_check_id)
            for v in value
        ]
    return value
