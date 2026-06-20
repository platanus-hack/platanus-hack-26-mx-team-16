"""Render enrich-phase Tool args + URL path with case data (E3 · plan §4.7).

Reuses the rules engine's resolution primitives instead of inventing a parallel
template language:

- ``@slug.path`` (braces optional, same as rule prompts) resolves against the
  case's EXTRACTED documents via ``_shared/path_resolver``; bare refs are
  normalised to the braced form so ``_shared/substitution`` does the walking.
- ``{{token}}`` resolves via the system token registry (the caller resolves the
  names with ``token_resolver`` and passes the values here).
- The URL ``path`` template accepts ``{placeholder}`` keyed by **rendered arg
  names**; consumed args are removed from the body/query by the caller.

Two disjoint error families:

- :class:`ToolConfigRenderError` — the template itself is broken (placeholder
  without a matching arg, token not declared). Configuration error ⇒ the
  activity raises a non-retryable ``ApplicationError`` (never ``on_failure``).
- :class:`UnresolvedRefError` — the template is fine but THIS case lacks the
  data (no doc with that slug, missing field, token out of scope). Data
  condition ⇒ the phase applies its ``on_failure`` mode.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared import (
    path_resolver,
    substitution,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import (
    DocRef,
    parse_doc_refs,
    parse_tokens,
)


class ToolConfigRenderError(Exception):
    """The args/path template is misconfigured (non-retryable config error)."""


class UnresolvedRefError(Exception):
    """A ref/token cannot be resolved for this case (``on_failure`` path)."""


# Full-string forms only — same semantics as the rules substitution walk.
_FULL_DOC_REF_RE = re.compile(
    r"^\s*@(?:\{[a-z0-9][a-z0-9_-]*\}|[a-z0-9][a-z0-9_-]*)(?:\.[A-Za-z_][\w]*|\[\d*\])*\s*$"
)
_FULL_TOKEN_RE = re.compile(r"^\s*\{\{\s*[A-Za-z_][\w.]*\s*\}\}\s*$")
_PATH_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][\w]*)\}")


def collect_doc_refs(args: dict) -> list[DocRef]:
    """Doc refs referenced by full-string arg values, deduped by canonical raw."""
    refs: dict[str, DocRef] = {}
    for value in _iter_strings(args):
        if _FULL_DOC_REF_RE.match(value):
            for ref in parse_doc_refs(value):
                refs.setdefault(_canonical_raw(ref), ref)
    return list(refs.values())


def collect_tokens(args: dict) -> list[str]:
    """Token names referenced by full-string arg values, deduped, in order."""
    names: dict[str, None] = {}
    for value in _iter_strings(args):
        if _FULL_TOKEN_RE.match(value):
            for name in parse_tokens(value):
                names.setdefault(name, None)
    return list(names)


def render_args(
    args: dict,
    *,
    documents: list[EvalDocumentInput],
    tokens: dict[str, Any],
) -> dict:
    """Replace ``@slug.path`` / ``{{token}}`` full-string values with case data."""
    normalized = _normalize(args)
    resolved_inputs: dict[str, Any] = {}
    for ref in collect_doc_refs(args):
        try:
            values = path_resolver.resolve(ref, documents, required=True)
        except path_resolver.MissingDocumentError as exc:
            msg = f"no EXTRACTED document of type '{ref.slug}' in this case"
            raise UnresolvedRefError(msg) from exc
        except path_resolver.MissingFieldError as exc:
            raise UnresolvedRefError(str(exc)) from exc
        resolved_inputs[_canonical_raw(ref)] = _plain(ref, values)
    try:
        return substitution.substitute(
            normalized,
            resolved_inputs=resolved_inputs,
            resolved_tokens={name: _json_safe(value) for name, value in tokens.items()},
            sub_check_id="enrich",
        )
    except InvalidWorkflowRuleConfigError as exc:
        raise ToolConfigRenderError(str(exc)) from exc


def render_path(template: str, args: dict) -> tuple[str, set[str]]:
    """Fill ``{placeholder}`` in the URL path with rendered arg values.

    Returns the rendered path plus the set of consumed arg keys (the caller
    removes them from the body/query). Values are URL-quoted.
    """
    consumed: set[str] = set()

    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in args:
            msg = f"path placeholder {{{key}}} has no matching arg"
            raise ToolConfigRenderError(msg)
        value = args[key]
        if value is None or isinstance(value, dict | list):
            msg = f"path placeholder {{{key}}} resolved to a non-scalar value"
            raise UnresolvedRefError(msg)
        consumed.add(key)
        return quote(str(_json_safe(value)), safe="")

    return _PATH_PLACEHOLDER_RE.sub(_repl, template), consumed


def _canonical_raw(ref: DocRef) -> str:
    """Braced raw form (`@{slug}.path`) that `substitution.py` recognises."""
    if ref.path is None:
        return f"@{{{ref.slug}}}"
    if ref.path.startswith("["):
        return f"@{{{ref.slug}}}{ref.path}"
    return f"@{{{ref.slug}}}.{ref.path}"


def _normalize(value: Any) -> Any:
    """Rewrite bare `@slug.path` full-string values to the braced alias."""
    if isinstance(value, str):
        if _FULL_DOC_REF_RE.match(value):
            refs = parse_doc_refs(value)
            if refs:
                return _canonical_raw(refs[0])
        return value
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _plain(ref: DocRef, values: list[path_resolver.ResolvedValue]) -> Any:
    """Strip trace info: HTTP args want plain JSON values, not ResolvedValue."""
    plain = [_json_safe(rv.value) for rv in values]
    if ref.kind == "scalar" and len(plain) == 1:
        return plain[0]
    return plain


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
