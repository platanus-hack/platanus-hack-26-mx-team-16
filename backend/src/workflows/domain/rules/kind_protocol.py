"""Protocol for plugin-style rule kinds (spec §4.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.verdict_signal import VerdictSignal
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult

from uuid import UUID

if TYPE_CHECKING:
    from src.knowledge_base.domain.services.kb_resolver import KBDocumentResolver


@dataclass
class CompileContext:
    """Auxiliary inputs available during compilation."""

    workflow_id: UUID
    tenant_id: UUID
    document_types: list[DocumentType] = field(default_factory=list)
    kb_resolver: KBDocumentResolver | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompilationOutcome:
    artifact: dict[str, Any]
    compiled_with: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalDocumentInput:
    """A single document that takes part in this evaluation, with its extracted fields."""

    document_id: UUID
    document_type_id: UUID | None
    document_type_slug: str | None
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    text: str | None = None


@dataclass
class EvalInputs:
    """Concrete inputs for one invocation of a rule kind's evaluate()."""

    documents: list[EvalDocumentInput] = field(default_factory=list)
    document_refs: dict[str, Any] = field(default_factory=dict)
    knowledge_context: list[dict[str, Any]] = field(default_factory=list)
    tokens: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalContext:
    workflow_id: UUID
    tenant_id: UUID
    case_id: UUID
    workflow_analysis_run_id: UUID
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationOutcome:
    output: dict[str, Any] | None
    reasoning: str | None = None
    citations: list[Citation] = field(default_factory=list)
    evaluation_metadata: dict[str, Any] = field(default_factory=dict)
    rendered_prompt: str | None = None
    error: str | None = None


@runtime_checkable
class WorkflowRuleKind(Protocol):
    """A plugin contract: name, schemas, compile, evaluate, contribute_to_verdict.

    Implementations must expose either ``output_schema`` as an attribute or
    a method ``output_schema_for(rule)`` that returns a JSON-Schema dict
    (kinds whose output shape depends on the rule's config — e.g. DERIVATION).
    """

    name: str
    label: str
    description: str
    config_schema: dict[str, Any]

    def default_config(self) -> dict[str, Any]: ...

    def output_schema_for(self, rule: WorkflowRule) -> dict[str, Any]:
        """JSON Schema describing this kind's `WorkflowRuleResult.output`."""

    async def compile(
        self,
        rule: WorkflowRule,
        ctx: CompileContext,
    ) -> CompilationOutcome: ...

    async def evaluate(
        self,
        rule: WorkflowRule,
        compilation: WorkflowRuleCompilation,
        inputs: EvalInputs,
        ctx: EvalContext,
    ) -> EvaluationOutcome: ...

    def contribute_to_verdict(
        self,
        rule: WorkflowRule,
        result: WorkflowRuleResult,
    ) -> VerdictSignal | None:
        """Return ``None`` if this kind doesn't influence the verdict."""
