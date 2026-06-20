"""Route a sub_check to its method handler and aggregate the result.

The dispatcher does not know about the prompt or the tree — those are the
parser's and tree_evaluator's concerns. It receives a fully-resolved view
of inputs/tokens for one sub_check and returns a `SubCheckResult` the
tree_evaluator can fold into the final outcome.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.common.domain.models.processing.citation import Citation
from src.workflows.infrastructure.services.rules.kinds._shared.citations import (
    build_citations,
)
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import LLMRunner
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)
from src.workflows.infrastructure.services.rules.kinds._shared.substitution import (
    substitute,
)
from src.workflows.infrastructure.services.rules.kinds.validation.methods.handlers import (
    HANDLERS,
)


@dataclass(frozen=True)
class SubCheckResult:
    sub_check_id: str
    passed: bool
    reason: str
    citations: list[Citation]


async def evaluate_sub_check(
    sub_check: dict[str, Any],
    *,
    resolved_inputs: dict[str, list[ResolvedValue]],
    resolved_tokens: dict[str, Any],
    llm_runner: LLMRunner,
    knowledge_context: list[dict[str, Any]] | None = None,
) -> SubCheckResult:
    method = sub_check["method"]
    handler = HANDLERS.get(method)
    if handler is None:
        msg = f"Unknown method {method!r} in sub_check {sub_check['id']!r}"
        raise InvalidWorkflowRuleConfigError(msg)

    primary_ref = sub_check["inputs"][0] if sub_check.get("inputs") else None
    primary = resolved_inputs.get(primary_ref, []) if primary_ref else []

    substituted_params = substitute(
        sub_check.get("params") or {},
        resolved_inputs=resolved_inputs,
        resolved_tokens=resolved_tokens,
        sub_check_id=sub_check["id"],
    )

    try:
        result = handler(
            primary,
            substituted_params,
            resolved_inputs=resolved_inputs,
            llm_runner=llm_runner,
            knowledge_context=knowledge_context or [],
        )
        if inspect.isawaitable(result):
            passed, reason = await result
        else:
            passed, reason = result
    except InvalidWorkflowRuleConfigError:
        raise
    except KeyError as exc:
        # A missing required param is a *configuration* problem (bad artifact
        # shape), not a data failure: surface it as ERRORED, never a silent
        # FAIL (E5 drift fix).
        msg = f"{method} misconfigured in sub_check {sub_check['id']!r}: missing required param {exc}"
        raise InvalidWorkflowRuleConfigError(msg) from exc
    except Exception as exc:  # noqa: BLE001 — handler isolation
        # A handler crash is a configuration/data problem, never a data FAIL:
        # surfacing it as `passed=False` silently fails the rule (and a FAIL
        # under a NOT clause flips to a bogus PASS). Re-raise as a config error
        # so the rule result becomes ERRORED instead (E5 drift fix).
        msg = f"{method} raised in sub_check {sub_check['id']!r}: {exc}"
        raise InvalidWorkflowRuleConfigError(msg) from exc

    return SubCheckResult(
        sub_check_id=sub_check["id"],
        passed=passed,
        reason=reason,
        citations=build_citations(primary, sub_check_id=sub_check["id"]),
    )
