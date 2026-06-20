"""DERIVATION kind — compute / extract / aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
from src.workflows.infrastructure.services.rules.kinds._shared.citations import (
    build_citations,
)
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
from src.workflows.infrastructure.services.rules.kinds._shared.schema import (
    assert_valid_schema,
)


_CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["output_shape"],
    "properties": {
        "output_shape": {
            "description": (
                "JSON Schema that defines the shape of `WorkflowRuleResult.output`. "
                "Edited from the UI through the JsonSchemaBuilder."
            ),
            "type": "object",
        }
    },
}


@dataclass
class DerivationKind:
    name: str = "DERIVATION"
    label: str = "Derivación"
    description: str = (
        "Computa, extrae o agrega datos estructurados según un schema de salida definido en config.output_shape."
    )
    config_schema: dict[str, Any] = field(default_factory=lambda: _CONFIG_SCHEMA)
    # Default is the safe stub so the kind boots without LLM creds and unit
    # tests can instantiate it directly. The app bootstrap rewires this to an
    # AgnoLLMRunner via `register_default_kinds()`.
    llm_runner: LLMRunner = field(
        default_factory=lambda: StaticLLMRunner(payload={}),
    )

    def default_config(self) -> dict[str, Any]:
        return {
            "output_shape": {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            }
        }

    def output_schema_for(self, rule: WorkflowRule) -> dict[str, Any]:
        shape = rule.config.get("output_shape")
        if not isinstance(shape, dict):
            msg = "DERIVATION rule.config.output_shape must be a JSON Schema object"
            raise InvalidWorkflowRuleConfigError(msg)
        return shape

    async def compile(
        self,
        rule: WorkflowRule,
        ctx: CompileContext,
    ) -> CompilationOutcome:
        shape = self.output_schema_for(rule)
        assert_valid_schema(shape, label="DERIVATION.output_shape")

        inputs = _compile_inputs(rule.prompt, ctx)
        tokens = _compile_tokens(rule.prompt)
        knowledge_refs = await _compile_knowledge_refs(rule.prompt, ctx)

        artifact = {
            "version": 1,
            "prompt": rule.prompt,
            "output_shape_validated": True,
            "inputs": inputs,
            "tokens": tokens,
            "knowledge_refs": knowledge_refs,
        }
        compiled_with = {
            "kind": self.name,
            "compiler": "derivation.compile",
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
        artifact_inputs = artifact.get("inputs") or []

        try:
            resolved_by_ref: dict[str, list[ResolvedValue]] = {}
            for entry in artifact_inputs:
                ref = _doc_ref_from_artifact_entry(entry)
                if ref.raw in resolved_by_ref:
                    continue
                resolved_by_ref[ref.raw] = resolve_doc_ref(
                    ref,
                    inputs.documents,
                    required=bool(entry.get("required", True)),
                )
        except Exception as exc:
            return EvaluationOutcome(
                output=None,
                reasoning=None,
                error=str(exc),
                rendered_prompt=None,
            )

        rendered = _render_prompt(rule, resolved_by_ref, inputs.tokens or {})
        shape = self.output_schema_for(rule)
        try:
            payload = await self.llm_runner.run(
                system=_DERIVATION_SYSTEM_PROMPT,
                user=rendered,
                output_schema=shape,
            )
        except Exception as exc:
            return EvaluationOutcome(
                output=None,
                reasoning=None,
                error=str(exc),
                rendered_prompt=rendered,
            )

        citations = [citation for resolved in resolved_by_ref.values() for citation in build_citations(resolved)]
        return EvaluationOutcome(
            output=payload,
            reasoning=None,
            citations=citations,
            evaluation_metadata={"raw_payload": payload},
            rendered_prompt=rendered,
        )

    def contribute_to_verdict(
        self,
        rule: WorkflowRule,
        result: WorkflowRuleResult,
    ) -> VerdictSignal | None:
        return None


_DERIVATION_SYSTEM_PROMPT = (
    "You compute structured data from one or more documents. Respond strictly as "
    "a JSON object that conforms to the provided output schema. Do not include "
    "any text outside the JSON."
)


def _doc_ref_from_artifact_entry(entry: dict[str, Any]) -> DocRef:
    # Artifact target shape uses {ref, doctype, path}; older artifacts used {slug, raw}.
    slug = entry.get("doctype") or entry.get("slug")
    raw = entry.get("ref") or entry.get("raw") or _rebuild_raw(entry, slug)
    return DocRef(
        slug=slug,
        path=entry.get("path") or None,
        kind=entry.get("kind") or "scalar",
        raw=raw,
    )


def _rebuild_raw(entry: dict[str, Any], slug: str) -> str:
    raw = f"@{slug}"
    path = entry.get("path")
    if path:
        if not path.startswith("[") and not path.startswith("."):
            raw = f"{raw}.{path}"
        else:
            raw = f"{raw}{path}"
    return raw


def _render_prompt(
    rule: WorkflowRule,
    resolved_by_ref: dict[str, list[ResolvedValue]],
    tokens: dict[str, Any],
) -> str:
    if resolved_by_ref:
        fields_block = "\n".join(
            f"- {ref}: " + ", ".join(f"{r.field_path or '<doc>'}={r.value!r}" for r in resolved)
            for ref, resolved in resolved_by_ref.items()
        )
    else:
        fields_block = "(none)"
    return f"Instruction:\n{rule.prompt}\n\nResolved fields:\n{fields_block}\n\nTokens:\n{tokens or {}}"


def _compile_inputs(prompt: str, ctx: CompileContext) -> list[dict[str, Any]]:
    """Build the canonical inputs[] shape: {ref, doctype, path, required, kind}."""
    refs = parse_doc_refs(prompt)
    if not refs:
        return []
    available_slugs = {getattr(dt, "slug", None) for dt in ctx.document_types if getattr(dt, "slug", None)}
    inputs: list[dict[str, Any]] = []
    for ref in refs:
        if ref.slug not in available_slugs:
            msg = (
                f"DERIVATION prompt references unknown doctype slug '@{ref.slug}'. "
                f"Known slugs: {sorted(s for s in available_slugs if s)}"
            )
            raise InvalidWorkflowRuleConfigError(msg)
        kind, path = _artifact_kind_and_path(ref)
        inputs.append(
            {
                "ref": ref.raw,
                "doctype": ref.slug,
                "path": path,
                "required": True,
                "kind": kind,
            }
        )
    return inputs


def _artifact_kind_and_path(ref: DocRef) -> tuple[str, str]:
    """Translate parser DocRef to the artifact's inputs[] kind/path shape.

    Two kinds in artifact entries: `scalar` and `array`. The bare collection
    marker `@slug[]` becomes `kind="array"` with an empty path; nested
    `field[]` collapses to `kind="array"` with `[]` stripped from the
    trailing position; a field inside an array (`items[].cantidad`) is
    reported as `kind="scalar"` because the leaf value is a scalar even
    though it is reached via an iteration.
    """
    raw_path = ref.path or ""
    if raw_path in ("", "[]"):
        return ("array" if ref.kind == "collection" else "scalar"), ""
    if raw_path.endswith("[]"):
        return "array", raw_path[:-2]
    return "scalar", raw_path


def _compile_tokens(prompt: str) -> list[str]:
    tokens = parse_tokens(prompt)
    token_registry.assert_known(tokens, label="DERIVATION prompt")
    return tokens


async def _compile_knowledge_refs(prompt: str, ctx: CompileContext) -> list[str]:
    slugs = parse_kb_refs(prompt)
    if not slugs:
        return []
    if ctx.kb_resolver is None:
        msg = f"DERIVATION prompt references KB slugs {slugs} but no kb_resolver was provided in the compile context"
        raise InvalidWorkflowRuleConfigError(msg)
    resolved = await ctx.kb_resolver.resolve(ctx.tenant_id, ctx.workflow_id, slugs)
    missing = [s for s in slugs if s not in resolved]
    if missing:
        msg = f"DERIVATION prompt references unknown KB slugs: {missing}. Upload the documents or fix the slug."
        raise InvalidWorkflowRuleConfigError(msg)
    return [str(resolved[s].uuid) for s in slugs]
