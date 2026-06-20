"""Wire the LLM call that turns a verdict + per-kind outputs into the summary `output`.

Uses the project-wide `LLMRunner` protocol; the production default is the
Agno-backed runner (see `default_llm_runner("synthesizer")`). The agent is
constrained by the workflow's `output_schema` — we pass it as the response
schema and validate the LLM's reply with `jsonschema` before persisting.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import jsonschema

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.domain.run_summary.errors import SynthesisOutputInvalidError
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    LLMRunner,
    StaticLLMRunner,
)


DEFAULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["verdict", "summary_text"],
    "properties": {
        "verdict": {"enum": ["PASS", "FAIL", "REVIEW"]},
        "summary_text": {"type": "string"},
        "key_findings": {"type": "array", "items": {"type": "string"}},
        "extracted_data": {"type": "object"},
        "citations": {"type": "array"},
    },
}

DEFAULT_SYNTHESIS_TEMPLATE = (
    "You consolidate analysis results into a structured summary. "
    "The verdict has already been decided by deterministic logic — do not "
    "alter it. Use the provided rule outputs to populate the schema."
)


@dataclass
class SynthesizerInput:
    tenant: Tenant | None
    verdict: Verdict
    blocking_failures: list[str]
    rule_results: list[WorkflowRuleResult]
    output_schema: dict[str, Any]
    synthesis_template: str
    # A4: case documents (mapped_extraction) — only fed when the pipeline opts in
    # (circulares needs them to list people; farmacia stays lean).
    documents: list[dict[str, Any]] = field(default_factory=list)
    uses_documents: bool = False
    # E2 · x-source projection: deterministically resolved fields, keyed by
    # JSON Pointer. Fixed context for the agent — it must NOT invent or alter
    # them; the runner overwrites them on the merged output anyway.
    resolved_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesizerOutput:
    output: dict[str, Any]
    model: str | None
    provider: str | None


@dataclass
class SynthesizerAgent:
    """Constrained LLM agent that emits a JSON Schema-conforming summary output."""

    # Default is the safe stub; the use-case wires an Agno-backed runner.
    llm_runner: LLMRunner = field(
        default_factory=lambda: StaticLLMRunner(
            payload={"verdict": "REVIEW", "summary_text": "stub: synthesizer pending real LLM wiring"}
        )
    )
    model: str | None = None
    provider: str | None = None

    async def synthesize(self, inputs: SynthesizerInput) -> SynthesizerOutput:
        system = _build_system_prompt(inputs.synthesis_template)
        user = _build_user_prompt(inputs)
        payload = await self.llm_runner.run(
            system=system,
            user=user,
            output_schema=inputs.output_schema,
        )
        try:
            jsonschema.validate(instance=payload, schema=inputs.output_schema)
        except jsonschema.ValidationError as exc:
            raise SynthesisOutputInvalidError(exc.message) from exc
        return SynthesizerOutput(output=payload, model=self.model, provider=self.provider)


def _build_system_prompt(template: str) -> str:
    return (
        f"{template}\n\n"
        "STRICT RULES:\n"
        "- The verdict is final; never change it.\n"
        "- Respond strictly as a JSON object that conforms to the provided schema.\n"
        "- Do not emit any text outside the JSON."
    )


def _build_user_prompt(inputs: SynthesizerInput) -> str:
    grouped = _group_results_by_kind(inputs.rule_results)
    body: dict[str, Any] = {
        "tenant": inputs.tenant.name if inputs.tenant else None,
        "verdict": inputs.verdict.value,
        "blocking_failures": inputs.blocking_failures,
        "rule_results_by_kind": grouped,
    }
    # A4 golden rule: everything that enters the prompt enters the hash. When the
    # pipeline opts in, the case documents are part of the prompt — and so the
    # cache key (see hashing.compute_input_hash) must include them too.
    if inputs.uses_documents:
        body["documents"] = inputs.documents
    # E2: fields already resolved by the deterministic x-source projection are
    # fixed context — the agent only fills the remaining (narrative) fields.
    if inputs.resolved_fields:
        body["resolved_fields"] = inputs.resolved_fields
        body["resolved_fields_note"] = (
            "These fields were resolved deterministically from the extracted "
            "documents and rule outputs. Copy them verbatim into the output; "
            "do NOT invent, alter or contradict them."
        )
    return json.dumps(body, ensure_ascii=False, default=str)


def _group_results_by_kind(results: Iterable[WorkflowRuleResult]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result.kind].append(
            {
                "rule_id": str(result.rule_id),
                "status": result.status.value,
                "output": result.output,
                "reasoning": result.reasoning,
                "citations": [c.model_dump(mode="json") for c in result.citations],
            }
        )
    return dict(grouped)
