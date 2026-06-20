"""VALIDATION kind — boolean criteria check."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleResultStatus,
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)
from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.common.domain.models.processing.verdict_signal import VerdictSignal
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.domain.rules.kind_protocol import (
    CompilationOutcome,
    CompileContext,
    EvalContext,
    EvalInputs,
    EvaluationOutcome,
)
from src.workflows.domain.services import token_registry
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    LLMRunner,
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
    resolve as resolve_doc_ref,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import (
    DocRef,
    parse_doc_refs,
    parse_kb_refs,
    parse_tokens,
)
from src.workflows.infrastructure.services.rules.kinds.validation.dispatcher import (
    SubCheckResult,
    evaluate_sub_check,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)
from src.workflows.infrastructure.services.rules.kinds.validation.tree_evaluator import (
    evaluate_tree,
)


_CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["severity"],
    "properties": {
        "severity": {
            "title": "Severidad",
            "description": "Gravedad cuando la regla falla.",
            "default": "MAJOR",
            "oneOf": [
                {
                    "const": "BLOCKER",
                    "title": "Bloqueante",
                    "description": "Bloquea el resultado del caso.",
                },
                {
                    "const": "MAJOR",
                    "title": "Mayor",
                    "description": "Peso alto en el resultado, no bloquea.",
                },
                {
                    "const": "MINOR",
                    "title": "Menor",
                    "description": "Peso bajo en el resultado.",
                },
                {
                    "const": "INFO",
                    "title": "Informativa",
                    "description": "No afecta el resultado.",
                },
            ],
        },
    },
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["passed", "reason"],
    "properties": {
        "passed": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}


@dataclass
class ValidationKind:
    name: str = "VALIDATION"
    label: str = "Validación"
    description: str = "Verifica un criterio booleano sobre el caso y produce {passed, reason}."
    config_schema: dict[str, Any] = field(default_factory=lambda: _CONFIG_SCHEMA)
    # Default is the safe stub; the app bootstrap rewires this to an
    # AgnoLLMRunner so prod LLM_CHECK sub_checks hit a real provider.
    llm_runner: LLMRunner = field(
        default_factory=lambda: StaticLLMRunner(
            payload={"passed": True, "reason": "stub: rule pending real LLM wiring"},
        )
    )
    parser: ValidationParser = field(default_factory=ValidationParser)

    def default_config(self) -> dict[str, Any]:
        return {"severity": "MAJOR"}

    def output_schema_for(self, rule: WorkflowRule) -> dict[str, Any]:
        return _OUTPUT_SCHEMA

    async def compile(
        self,
        rule: WorkflowRule,
        ctx: CompileContext,
    ) -> CompilationOutcome:
        """Decompose the natural-language prompt into machine-checkable assertions."""
        available_slugs = sorted({dt.slug for dt in ctx.document_types if getattr(dt, "slug", None)})

        kb_slugs = parse_kb_refs(rule.prompt)
        tokens = parse_tokens(rule.prompt)
        token_registry.assert_known(tokens, label="VALIDATION prompt")

        # Resolve KB slugs upfront so the PARSER (and the dispatcher later)
        # operate on slugs that are guaranteed to exist.
        if kb_slugs:
            if ctx.kb_resolver is None:
                msg = (
                    f"VALIDATION prompt references KB slugs {kb_slugs} but no kb_resolver "
                    "was provided in the compile context"
                )
                raise InvalidWorkflowRuleConfigError(msg)
            resolved = await ctx.kb_resolver.resolve(ctx.tenant_id, ctx.workflow_id, kb_slugs)
            missing = [s for s in kb_slugs if s not in resolved]
            if missing:
                msg = (
                    f"VALIDATION prompt references unknown KB slugs: {missing}. Upload the documents or fix the slug."
                )
                raise InvalidWorkflowRuleConfigError(msg)
            knowledge_refs = [str(resolved[s].uuid) for s in kb_slugs]
        else:
            knowledge_refs = []

        parser_result = await self.parser.parse(
            prompt=rule.prompt,
            available_slugs=available_slugs,
            kb_slugs=kb_slugs,
            tokens=tokens,
        )

        artifact = {
            "version": 1,
            "prompt": rule.prompt,
            "available_slugs": available_slugs,
            "tree": parser_result.tree,
            "sub_checks": parser_result.sub_checks,
            "knowledge_refs": knowledge_refs,
        }
        compiled_with = {
            "kind": self.name,
            "compiler": "validation.compile",
            "compiler_version": "1.0",
        }
        return CompilationOutcome(artifact=artifact, compiled_with=compiled_with)

    async def evaluate(
        self,
        rule: WorkflowRule,
        compilation: WorkflowRuleCompilation,
        inputs: EvalInputs,
        ctx: EvalContext,
    ) -> EvaluationOutcome:
        artifact = compilation.artifact or {}
        sub_checks = artifact.get("sub_checks") or []
        tree = artifact.get("tree") or {}
        if not sub_checks or not tree:
            return EvaluationOutcome(
                output=None,
                reasoning=None,
                error="VALIDATION artifact missing tree/sub_checks — recompile the rule",
                rendered_prompt=None,
            )

        try:
            sub_check_results: list[SubCheckResult] = []
            for sub_check in sub_checks:
                resolved_inputs = _resolve_sub_check_inputs(sub_check, inputs)
                resolved_tokens = _filter_tokens(sub_check, inputs.tokens or {})
                result = await evaluate_sub_check(
                    sub_check,
                    resolved_inputs=resolved_inputs,
                    resolved_tokens=resolved_tokens,
                    llm_runner=self.llm_runner,
                    knowledge_context=inputs.knowledge_context,
                )
                sub_check_results.append(result)
            passed, reason = evaluate_tree(tree, sub_check_results)
        except Exception as exc:
            return EvaluationOutcome(
                output=None,
                reasoning=None,
                error=str(exc),
                rendered_prompt=None,
            )

        citations = [c for r in sub_check_results for c in r.citations]
        return EvaluationOutcome(
            output={"passed": passed, "reason": reason},
            reasoning=reason,
            citations=citations,
            evaluation_metadata={
                "sub_check_results": [
                    {"id": r.sub_check_id, "passed": r.passed, "reason": r.reason} for r in sub_check_results
                ],
            },
            rendered_prompt=None,
        )

    def contribute_to_verdict(
        self,
        rule: WorkflowRule,
        result: WorkflowRuleResult,
    ) -> VerdictSignal | None:
        if result.status != WorkflowRuleResultStatus.SUCCESS or not result.output:
            return None
        severity = WorkflowRuleSeverity(rule.config.get("severity", "MAJOR"))
        polarity = (
            WorkflowRuleVerdictPolarity.PASS if result.output.get("passed") else WorkflowRuleVerdictPolarity.FAIL
        )
        return VerdictSignal(
            rule_id=rule.uuid,
            kind=self.name,
            severity=severity,
            polarity=polarity,
            detail={"reason": result.output.get("reason")},
        )


def _resolve_sub_check_inputs(
    sub_check: dict[str, Any],
    inputs: EvalInputs,
) -> dict[str, list[ResolvedValue]]:
    resolved_inputs: dict[str, list[ResolvedValue]] = {}
    for raw in _all_sub_check_refs(sub_check):
        if raw in resolved_inputs:
            continue
        refs = parse_doc_refs(raw)
        if not refs:
            continue
        ref: DocRef = refs[0]
        resolved_inputs[raw] = resolve_doc_ref(ref, inputs.documents)
    return resolved_inputs


def _all_sub_check_refs(sub_check: dict[str, Any]) -> list[str]:
    declared = list(sub_check.get("inputs") or [])
    for raw in _scan_param_refs(sub_check.get("params") or {}):
        if raw not in declared:
            declared.append(raw)
    return declared


def _scan_param_refs(value: Any) -> list[str]:
    refs: list[str] = []

    def _walk(v: Any) -> None:
        if isinstance(v, str):
            for ref in parse_doc_refs(v):
                refs.append(ref.raw)
        elif isinstance(v, dict):
            for vv in v.values():
                _walk(vv)
        elif isinstance(v, list):
            for vv in v:
                _walk(vv)

    _walk(value)
    return refs


def _filter_tokens(sub_check: dict[str, Any], all_tokens: dict[str, Any]) -> dict[str, Any]:
    declared = sub_check.get("tokens") or []
    return {name: all_tokens[name] for name in declared if name in all_tokens}
