"""Run one pass of the synthesizer over a closed run's outputs (E2: hybrid).

E2 (spec case-output §4.1) makes this a two-layer pass:

1. **Deterministic projection** — `project_schema` resolves every
   ``x-source``-annotated property of ``workflow.output_schema`` against the
   case documents (`mapped_extraction`), the rule results (``@rule.<slug>``)
   and the system tokens (verdict/confidence/run/case). Resolved values are
   final: they override whatever the LLM emits (anti-hallucination) and carry
   per-field ``Citation`` provenance persisted as ``output_provenance``.
2. **LLM synthesis** — only the properties *without* ``x-source`` are left to
   the agent, which receives the resolved fields as fixed context.

Pure-deterministic path: when the schema leaves nothing for the LLM
(``llm_pointers`` empty) — or synthesis is disabled but the schema does carry
``x-source`` fields — no agent runs at all; the projection IS the output.
``synthesis_enabled=False`` with zero ``x-source`` keeps the historical
behavior (`SynthesisDisabledError`).

Documents are loaded ALWAYS for the projection; `synthesis_uses_documents`
only gates their inclusion in the LLM prompt (A4).

Idempotent by `input_hash` (cache v3: documents + resolved projection always
hashed). Use `force=True` to bypass the cache (re-synthesize endpoint).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jsonschema

from src.common.application.logging import get_logger
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash
from src.workflows.application.analysis_run_summary.projection import (
    ProjectionContext,
    ProjectionResult,
    apply_resolved,
    flatten_extraction,
    project_schema,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.domain.run_summary.errors import (
    SummaryNotFoundError,
    SynthesisDisabledError,
    SynthesisOutputInvalidError,
)
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    DEFAULT_OUTPUT_SCHEMA,
    DEFAULT_SYNTHESIS_TEMPLATE,
    SynthesizerAgent,
    SynthesizerInput,
)

logger = get_logger(__name__)


@dataclass
class SynthesisRunner(UseCase):
    """Project x-source fields → (optionally) invoke agent → persist outcome."""

    run_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository
    run_repository: WorkflowAnalysisRunRepository
    result_repository: WorkflowRuleResultRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository
    agent: SynthesizerAgent
    tenant: Tenant | None = None
    force: bool = False
    document_repository: WorkflowDocumentRepository | None = None
    # E2: needed to resolve `@slug.path` (document type slugs) and
    # `@rule.<slug>` (rule slugs). Optional so legacy wirings keep working —
    # without them the projection degrades to null + warning per ref.
    document_type_repository: DocumentTypeRepository | None = None
    rule_repository: WorkflowRuleRepository | None = None

    async def execute(self) -> WorkflowAnalysisRunSummary:
        run = await self.run_repository.find_by_id(self.run_id, self.tenant_id)
        if run is None:
            raise WorkflowAnalysisRunNotFoundError(str(self.run_id))
        workflow = await self.workflow_repository.find_by_id(run.workflow_id, self.tenant_id)
        if workflow is None:
            raise SynthesisDisabledError(str(run.workflow_id))

        summary = await self.summary_repository.find_by_run(self.run_id, self.tenant_id)
        if summary is None:
            raise SummaryNotFoundError(str(self.run_id))

        results = await self.result_repository.list_by_run(self.run_id, self.tenant_id)
        output_schema = workflow.output_schema or DEFAULT_OUTPUT_SCHEMA
        synthesis_template = workflow.synthesis_template or DEFAULT_SYNTHESIS_TEMPLATE
        uses_documents = workflow.synthesis_uses_documents

        # E2: documents are loaded ALWAYS (projection input); `uses_documents`
        # only gates whether they also enter the LLM prompt (A4).
        case_documents = await self._load_case_documents(run)
        slug_by_doc_type = await self._load_doc_type_slugs(run.workflow_id)
        prompt_documents = _prompt_documents(case_documents, slug_by_doc_type)
        projection = project_schema(
            output_schema,
            ProjectionContext(
                documents=_eval_documents(case_documents, slug_by_doc_type),
                rule_results_by_slug=await self._results_by_rule_slug(run.workflow_id, results),
                system_tokens={
                    "verdict": summary.verdict.value,
                    "confidence_score": summary.confidence_score,
                    "run_id": str(self.run_id),
                    "case_id": str(run.workflow_case_id),
                },
            ),
        )
        for warning in projection.warnings:
            logger.warning("synthesis.projection_warning", run_id=str(self.run_id), detail=warning)

        if not workflow.synthesis_enabled and not projection.has_sources:
            # Historical behavior: nothing deterministic to project and the
            # LLM leg is off → synthesis is simply disabled.
            raise SynthesisDisabledError(str(run.workflow_id))

        input_hash = compute_input_hash(
            verdict=summary.verdict,
            rule_results=results,
            output_schema=output_schema,
            synthesis_template=synthesis_template,
            model=self.agent.model,
            documents=prompt_documents,
            resolved_fields=projection.resolved,
        )
        if (
            not self.force
            and summary.narrative_status == NarrativeStatus.COMPLETED
            and summary.input_hash == input_hash
        ):
            logger.info("synthesis.cache_hit", run_id=str(self.run_id), input_hash=input_hash)
            return summary

        schema_snapshot = self._schema_snapshot(workflow, output_schema)
        provenance = _serialize_provenance(projection)

        deterministic_only = not workflow.synthesis_enabled or not projection.llm_pointers
        if deterministic_only:
            # Pure deterministic path: no agent. The projection IS the output.
            output = apply_resolved({}, projection.resolved)
            self._validate_best_effort(output, output_schema)
            return await self.summary_repository.update_narrative(
                self.run_id,
                self.tenant_id,
                status=NarrativeStatus.COMPLETED,
                output=output,
                output_provenance=provenance,
                output_schema_snapshot=schema_snapshot,
                synthesis_template_snapshot=synthesis_template,
                narrative_error=None,
                input_hash=input_hash,
            )

        await self.summary_repository.update_narrative(
            self.run_id,
            self.tenant_id,
            status=NarrativeStatus.RUNNING,
            input_hash=input_hash,
        )

        try:
            outcome = await self.agent.synthesize(
                SynthesizerInput(
                    tenant=self.tenant,
                    verdict=summary.verdict,
                    blocking_failures=[str(uid) for uid in summary.blocking_failures],
                    rule_results=results,
                    output_schema=output_schema,
                    synthesis_template=synthesis_template,
                    documents=prompt_documents,
                    uses_documents=uses_documents,
                    resolved_fields=projection.resolved,
                )
            )
        except SynthesisOutputInvalidError as exc:
            return await self.summary_repository.update_narrative(
                self.run_id,
                self.tenant_id,
                status=NarrativeStatus.FAILED,
                narrative_error=str(exc),
                output_schema_snapshot=schema_snapshot,
                synthesis_template_snapshot=synthesis_template,
            )
        except Exception as exc:
            logger.exception("synthesis.agent_failed", run_id=str(self.run_id))
            return await self.summary_repository.update_narrative(
                self.run_id,
                self.tenant_id,
                status=NarrativeStatus.FAILED,
                narrative_error=f"agent error: {exc}",
                output_schema_snapshot=schema_snapshot,
                synthesis_template_snapshot=synthesis_template,
            )

        # Anti-hallucination merge: deterministically resolved fields
        # overwrite whatever the agent emitted for them.
        output = apply_resolved(outcome.output, projection.resolved)
        self._validate_best_effort(output, output_schema)
        if projection.llm_pointers:
            # Edge case (spec §6): the agent doesn't emit per-field citations
            # yet, so LLM fields land without provenance — non-blocking.
            logger.warning(
                "synthesis.llm_fields_without_citations",
                run_id=str(self.run_id),
                pointers=projection.llm_pointers,
            )

        return await self.summary_repository.update_narrative(
            self.run_id,
            self.tenant_id,
            status=NarrativeStatus.COMPLETED,
            output=output,
            output_provenance=provenance,
            output_schema_snapshot=schema_snapshot,
            synthesis_template_snapshot=synthesis_template,
            narrative_error=None,
            model=outcome.model,
            provider=outcome.provider,
            input_hash=input_hash,
        )

    # ── loading helpers ─────────────────────────────────────────────────────

    async def _load_case_documents(self, run: WorkflowAnalysisRun) -> list[WorkflowDocument]:
        if self.document_repository is None:
            return []
        return await self.document_repository.list_by_case(run.workflow_case_id, self.tenant_id)

    async def _load_doc_type_slugs(self, workflow_id: UUID) -> dict[UUID, str | None]:
        if self.document_type_repository is None:
            return {}
        doc_types = await self.document_type_repository.list_by_workflow(workflow_id, self.tenant_id)
        return {dt.uuid: dt.slug for dt in doc_types}

    async def _results_by_rule_slug(
        self,
        workflow_id: UUID,
        results: list[WorkflowRuleResult],
    ) -> dict[str, list[WorkflowRuleResult]]:
        if self.rule_repository is None:
            return {}
        rules = await self.rule_repository.list_by_workflow(workflow_id, self.tenant_id)
        slug_by_rule_id = {r.uuid: r.slug for r in rules if r.slug}
        by_slug: dict[str, list[WorkflowRuleResult]] = {}
        for result in results:
            slug = slug_by_rule_id.get(result.rule_id)
            if slug is None:
                continue
            by_slug.setdefault(slug, []).append(result)
        return by_slug

    # ── misc ────────────────────────────────────────────────────────────────

    def _validate_best_effort(self, output: dict[str, Any], schema: dict[str, Any]) -> None:
        """Schema-validate the merged output; failures warn, never block.

        Deterministic nulls (unresolvable x-source → null by decision) may
        legitimately violate `type` constraints — the value is still the
        truthful projection, so we persist it and surface a warning.
        """
        try:
            jsonschema.validate(instance=output, schema=schema)
        except jsonschema.ValidationError as exc:
            logger.warning(
                "synthesis.merged_output_invalid", run_id=str(self.run_id), error=exc.message
            )
        except jsonschema.SchemaError as exc:
            logger.warning("synthesis.output_schema_invalid", run_id=str(self.run_id), error=exc.message)

    @staticmethod
    def _schema_snapshot(workflow: Any, output_schema: dict[str, Any]) -> dict[str, Any]:
        """Snapshot + (cheap) explicit version marker when the workflow has one."""
        version = getattr(workflow, "output_schema_version", None)
        if version is not None and workflow.output_schema:
            return {**output_schema, "x-output-schema-version": version}
        return output_schema


def _eval_documents(
    documents: list[WorkflowDocument],
    slug_by_doc_type: dict[UUID, str | None],
) -> list[EvalDocumentInput]:
    """Mirror the rule scope_resolver convention (flattened extracted fields)."""
    return [
        EvalDocumentInput(
            document_id=doc.uuid,
            document_type_id=doc.document_type_id,
            document_type_slug=(
                slug_by_doc_type.get(doc.document_type_id) if doc.document_type_id else None
            ),
            extracted_fields=flatten_extraction(doc.mapped_extraction or doc.extraction or {}),
            text=doc.extracted_text,
        )
        for doc in documents
    ]


def _prompt_documents(
    documents: list[WorkflowDocument],
    slug_by_doc_type: dict[UUID, str | None],
) -> list[dict[str, Any]]:
    """Case ``mapped_extraction`` for the A4 document-aware prompt (and hash)."""
    return [
        {
            "document_id": str(doc.uuid),
            "document_type_id": str(doc.document_type_id) if doc.document_type_id else None,
            "document_type_slug": (
                slug_by_doc_type.get(doc.document_type_id) if doc.document_type_id else None
            ),
            "document_index": doc.document_index,
            "fields": doc.mapped_extraction or {},
        }
        for doc in documents
    ]


def _serialize_provenance(projection: ProjectionResult) -> dict[str, Any]:
    return {
        pointer: [c.model_dump(mode="json") for c in citations]
        for pointer, citations in projection.citations.items()
    }
