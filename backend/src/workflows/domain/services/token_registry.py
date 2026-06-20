"""Catalogue of `{{token}}` names allowed in rule prompts and templates.

Compile-time validators (`derivation.compile`, `validation.compile`,
`prompt_renderer`) call `assert_known` to make sure every `{{token}}`
referenced in user input exists here. Evaluate-time resolver
(`token_resolver`) maps these names to runtime values from the
case/tenant/run context.

Adding a token is a two-step change: register it here with the right scope
and provide a corresponding lookup in `token_resolver`. Anything not declared
fails compile, which is the desired UX so authors don't ship typos to prod.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError

TokenScope = Literal["runtime", "case", "tenant", "rule", "run", "workflow"]

_TOKEN_RE = re.compile(r"\{\{\s*(?P<name>[A-Za-z_][\w.]*)\s*\}\}")


@dataclass(frozen=True)
class TokenSpec:
    name: str
    scope: TokenScope
    description: str


REGISTRY: dict[str, TokenSpec] = {
    spec.name: spec
    for spec in (
        TokenSpec("now", "runtime", "Current ISO-8601 timestamp at evaluation time."),
        TokenSpec("today", "runtime", "Current date (YYYY-MM-DD) at evaluation time."),
        TokenSpec("today.year", "runtime", "Current year as integer."),
        TokenSpec("case.name", "case", "Display name of the analysis case under evaluation."),
        TokenSpec("tenant.name", "tenant", "Display name of the tenant the case belongs to."),
        TokenSpec("rule.severity", "rule", "Configured severity of the running rule."),
        TokenSpec("run.id", "run", "UUID of the workflow analysis run currently being summarised."),
        TokenSpec(
            "run.completed_at",
            "run",
            "ISO-8601 timestamp at which the run reached COMPLETED status.",
        ),
    )
}


def is_known(token: str) -> bool:
    return token in REGISTRY


def get(name: str) -> TokenSpec:
    if name not in REGISTRY:
        msg = f"Unknown token: {name!r}"
        raise KeyError(msg)
    return REGISTRY[name]


def known_for_scope(scope: TokenScope) -> set[str]:
    return {spec.name for spec in REGISTRY.values() if spec.scope == scope}


def known_names() -> set[str]:
    return set(REGISTRY.keys())


def parse_tokens(text: str) -> list[str]:
    """Return `{{token}}` names referenced in `text`, deduped, in first-occurrence order."""
    seen: dict[str, None] = {}
    for match in _TOKEN_RE.finditer(text):
        seen.setdefault(match.group("name"), None)
    return list(seen.keys())


def assert_known(tokens: Iterable[str], *, label: str = "template") -> None:
    """Raise `InvalidWorkflowRuleConfigError` listing any token not in the registry."""
    unknown = [t for t in tokens if t not in REGISTRY]
    if unknown:
        msg = f"{label} references unknown tokens: {unknown}. Known tokens: {sorted(REGISTRY)}"
        raise InvalidWorkflowRuleConfigError(msg)
