"""Resolve `{{token}}` names against case/tenant/run context at evaluate time.

Compile validates that every token in a prompt is registered in the
`token_registry`; this resolver maps the registered names to runtime values.
The orchestrator builds a `TokenContext` once per run and calls `resolve_all`
to seed `EvalInputs.tokens` before invoking each kind's `evaluate`.

Resolved values keep their natural Python types (`int`, `datetime`, `str`).
Helpers that need to interpolate them into prompts call `to_prompt_value`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.domain.services import token_registry


@dataclass(frozen=True)
class TokenContext:
    case_name: str | None
    tenant: Tenant | None
    run_id: UUID | None
    rule: WorkflowRule | None
    now: datetime
    run_completed_at: datetime | None = None


class TokenScopeError(KeyError):
    """Raised when a token name is referenced but its scope cannot be resolved."""


def resolve(token: str, ctx: TokenContext) -> Any:
    spec = token_registry.get(token)
    name = spec.name
    if name == "now":
        return ctx.now
    if name == "today":
        return ctx.now.date()
    if name == "today.year":
        return ctx.now.year
    if name == "case.name":
        if ctx.case_name is None:
            msg = "case.name token referenced but no case in scope"
            raise TokenScopeError(msg)
        return ctx.case_name
    if name == "tenant.name":
        if ctx.tenant is None:
            msg = "tenant.name token referenced but no tenant in scope"
            raise TokenScopeError(msg)
        return ctx.tenant.name
    if name == "rule.severity":
        if ctx.rule is None:
            msg = "rule.severity token referenced but no rule in scope"
            raise TokenScopeError(msg)
        return ctx.rule.config.get("severity", "MAJOR")
    if name == "run.id":
        if ctx.run_id is None:
            msg = "run.id token referenced but no run in scope"
            raise TokenScopeError(msg)
        return ctx.run_id
    if name == "run.completed_at":
        if ctx.run_completed_at is None:
            msg = "run.completed_at token referenced but the run is not completed"
            raise TokenScopeError(msg)
        return ctx.run_completed_at
    msg = f"token_resolver: no runtime mapping for token {name!r}"
    raise TokenScopeError(msg)


def resolve_all(tokens: Iterable[str], ctx: TokenContext) -> dict[str, Any]:
    return {name: resolve(name, ctx) for name in tokens}


def to_prompt_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
