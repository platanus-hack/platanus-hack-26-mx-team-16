"""Per-document structured output (spec case-output §4.0 — DOCUMENT OUTPUT level).

For every ``WorkflowDocument`` of the case (tenant-filtered):

- If its ``DocumentType`` declares an ``output_schema`` → run the
  deterministic ``x-source`` projection scoped to THAT document plus the
  rule results whose ``document_refs`` include it. **E2 is deterministic
  only**: properties without ``x-source`` (LLM fields) emit a warning and are
  left out — there is no per-document LLM synthesis yet.
- If there is no schema → ``output`` is the ``mapped_extraction`` verbatim,
  with per-top-level-field provenance (a ``Citation`` pointing at the
  document itself).

``jsonschema.validate`` runs best-effort: a validation failure logs a warning
but the output is persisted anyway (the case-level synthesis still validates
its own schema strictly).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jsonschema

from src.common.application.logging import get_logger
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.projection import (
    ProjectionContext,
    apply_resolved,
    flatten_extraction,
    project_schema,
    _stringify,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)

logger = get_logger(__name__)


@dataclass
class BuildDocumentOutputs(UseCase):
    """Project and persist ``output`` / ``output_provenance`` for each case document."""

    run_id: UUID
    case_id: UUID
    workflow_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    rule_repository: WorkflowRuleRepository
    result_repository: WorkflowRuleResultRepository

    async def execute(self) -> list[WorkflowDocument]:
        documents = await self.document_repository.list_by_case(self.case_id, self.tenant_id)
        if not documents:
            return []

        doc_types = await self.document_type_repository.list_by_workflow(
            self.workflow_id, self.tenant_id
        )
        types_by_id = {dt.uuid: dt for dt in doc_types}
        rules = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        slug_by_rule_id = {r.uuid: r.slug for r in rules if r.slug}
        results = await self.result_repository.list_by_run(self.run_id, self.tenant_id)

        updated: list[WorkflowDocument] = []
        for doc in documents:
            doc_type = types_by_id.get(doc.document_type_id) if doc.document_type_id else None
            # `output_schema` lands on DocumentType in a parallel change —
            # tolerate models that don't carry the field yet.
            schema = getattr(doc_type, "output_schema", None) if doc_type else None
            if schema:
                output, provenance, warnings = self._project_document(
                    doc, doc_type.slug, schema, results, slug_by_rule_id
                )
            else:
                output, provenance, warnings = self._passthrough_output(doc, doc_type)
            for warning in warnings:
                logger.warning(
                    "document_output.warning",
                    document_id=str(doc.uuid),
                    run_id=str(self.run_id),
                    detail=warning,
                )
            updated.append(
                await self.document_repository.update(
                    doc.model_copy(update={"output": output, "output_provenance": provenance})
                )
            )
        return updated

    def _project_document(
        self,
        doc: WorkflowDocument,
        doc_type_slug: str | None,
        schema: dict[str, Any],
        results: list[WorkflowRuleResult],
        slug_by_rule_id: dict[UUID, str],
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        fields = doc.mapped_extraction or doc.extraction or {}
        context = ProjectionContext(
            documents=[
                EvalDocumentInput(
                    document_id=doc.uuid,
                    document_type_id=doc.document_type_id,
                    document_type_slug=doc_type_slug,
                    extracted_fields=flatten_extraction(fields),
                    text=doc.extracted_text,
                )
            ],
            rule_results_by_slug=self._results_for_document(doc.uuid, results, slug_by_rule_id),
            # No verdict/confidence at document level — the summary doesn't
            # exist yet when document outputs are built.
            system_tokens={"run_id": str(self.run_id), "case_id": str(self.case_id)},
        )
        projection = project_schema(schema, context)
        warnings = list(projection.warnings)
        if projection.llm_pointers:
            # E2: no per-document LLM synthesis — LLM fields stay absent.
            warnings.append(
                "LLM fields are not supported per-document in E2; left unset: "
                + ", ".join(projection.llm_pointers)
            )
        output = apply_resolved({}, projection.resolved)
        try:
            jsonschema.validate(instance=output, schema=schema)
        except jsonschema.ValidationError as exc:
            warnings.append(f"output does not validate against the document output_schema: {exc.message}")
        except jsonschema.SchemaError as exc:
            warnings.append(f"invalid document output_schema: {exc.message}")
        provenance = {
            pointer: [c.model_dump(mode="json") for c in citations]
            for pointer, citations in projection.citations.items()
        }
        return output, provenance, warnings

    def _passthrough_output(
        self,
        doc: WorkflowDocument,
        doc_type: Any,
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        """No schema → mapped_extraction verbatim + self-citation per top-level field."""
        output = dict(doc.mapped_extraction or {})
        slug = (doc_type.slug if doc_type else None) or "document"
        flattened = flatten_extraction(output)
        provenance = {
            f"/{name}": [
                Citation(
                    document_id=doc.uuid,
                    document_type_slug=slug,
                    field_path=name,
                    value=_stringify(flattened.get(name)),
                ).model_dump(mode="json")
            ]
            for name in output
        }
        return output, provenance, []

    def _results_for_document(
        self,
        document_id: UUID,
        results: list[WorkflowRuleResult],
        slug_by_rule_id: dict[UUID, str],
    ) -> dict[str, list[WorkflowRuleResult]]:
        """Rule results whose ``document_refs`` reference this document, keyed by rule slug."""
        by_slug: dict[str, list[WorkflowRuleResult]] = {}
        for result in results:
            slug = slug_by_rule_id.get(result.rule_id)
            if slug is None:
                continue
            if not _references_document(result.document_refs, document_id):
                continue
            by_slug.setdefault(slug, []).append(result)
        return by_slug


def _references_document(document_refs: dict[str, Any] | None, document_id: UUID) -> bool:
    target = str(document_id)
    for ids in (document_refs or {}).values():
        if isinstance(ids, (list, tuple)) and any(str(i) == target for i in ids):
            return True
    return False
