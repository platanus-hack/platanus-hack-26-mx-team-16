"""Import a workflow bundle envelope into an existing workflow (E6 · W4 · §4).

Order (dependency-driven):
  1. doc-types  — find-or-create by slug (versions on overwrite).
  2. pipeline   — append an immutable version to the workflow's OWN pipeline
                  (ADR 0002 · 1:1 ⇒ UNIQUE(workflow_id) forbids creating another),
                  then advance ``current_version`` (only if rules pass). No more
                  shared-recipe detection / slug re-scoping — pipelines are private.
  3. rules      — delegated to :class:`WorkflowRulesImporter` (resolves doc-type
                  + KB slugs against the destination).
  4. schedule recompilation of the imported rules (caller side, via report).

Transaction policy (documented, decisión §4): **NOT all-or-nothing in v1** — each
section is applied in order and the report records exactly what landed. The
caller owns the session/commit; ``dry_run`` previews without writing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.application.document_types.import_export.importer import (
    WorkflowDocumentTypesImporter,
)
from src.workflows.application.workflows.import_export.report import (
    WorkflowBundleImportReport,
)
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
    WorkflowRulesImporter,
)
from src.workflows.domain.models.phase_configs import validate_phase_configs
from src.workflows.domain.models.pipeline import Pipeline, PhaseSpec, PipelineVersion
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)

_SUPPORTED_SCHEMA_VERSIONS = {"1.0"}


def _get(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Read the first present key (camelCase or snake_case tolerant)."""
    for key in keys:
        if key in payload:
            return payload[key]
    return default


@dataclass
class WorkflowBundleImporter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    payload: dict[str, Any]
    strategy: ImportConflictStrategy
    workflow_repository: WorkflowRepository
    pipeline_repository: PipelineRepository
    rule_repository: WorkflowRuleRepository
    document_type_repository: DocumentTypeRepository
    kb_document_repository: KBDocumentRepository
    dry_run: bool = False
    # ids de reglas creadas/actualizadas ⇒ el endpoint programa su recompilación.
    rule_ids_to_recompile: list[UUID] | None = None

    async def execute(self) -> WorkflowBundleImportReport:
        report = WorkflowBundleImportReport(dry_run=self.dry_run)
        self.rule_ids_to_recompile = []

        schema_version = _get(self.payload, "schemaVersion", "schema_version")
        if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            report.errors.append(f"unsupported schemaVersion: {schema_version!r}")
            return report

        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))

        # --- 0. Workflow config (case_noun) -------------------------------
        # Sustantivo del caso (no-secreto). Se persiste up-front para que
        # sobreviva sin importar el resultado de pipeline/reglas — las
        # plantillas dependen de esto para sembrar el noun. §3.6.
        workflow_section = _get(self.payload, "workflow", default={}) or {}
        case_noun = _get(workflow_section, "caseNoun", "case_noun")
        if case_noun is not None and not self.dry_run:
            workflow.case_noun = case_noun
            await self.workflow_repository.update(workflow)

        # --- 1. Doc-types --------------------------------------------------
        doc_types_payload = _get(self.payload, "documentTypes", "document_types", default=[]) or []
        dt_report = await WorkflowDocumentTypesImporter(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            payload=doc_types_payload,
            strategy=self.strategy,
            document_type_repository=self.document_type_repository,
            dry_run=self.dry_run,
        ).execute()
        report.doc_types_created = dt_report.created
        report.doc_types_overwritten = dt_report.overwritten
        report.doc_types_skipped = dt_report.skipped
        report.doc_types_failed = dt_report.failed
        report.errors.extend(dt_report.errors)

        # --- 2. Pipeline ---------------------------------------------------
        # Prepara el contenedor + la versión nueva, pero DIFIERE el avance de
        # ``current_version`` y el rebind de ``workflow.pipeline_id`` hasta que
        # las reglas resuelvan limpiamente (atomicidad razonable, bug nº5): si
        # una regla falla, ni el pipeline activo ni el binding del workflow
        # quedan tocados.
        pending: _PendingPipelineBind | None = None
        pipeline_payload = _get(self.payload, "pipeline")
        if pipeline_payload:
            try:
                pending = await self._import_pipeline(workflow, pipeline_payload, report)
            except (ValidationError, ValueError) as exc:
                report.errors.append(f"pipeline: {exc}")

        # --- 3. Rules ------------------------------------------------------
        rules_payload = _get(self.payload, "rules", default=[]) or []
        rules_failed = 0
        if rules_payload:
            rules_importer = WorkflowRulesImporter(
                workflow_id=self.workflow_id,
                tenant_id=self.tenant_id,
                payload={"schema_version": "1.0", "rules": rules_payload},
                strategy=self.strategy,
                workflow_repository=self.workflow_repository,
                rule_repository=self.rule_repository,
                document_type_repository=self.document_type_repository,
                kb_document_repository=self.kb_document_repository,
                dry_run=self.dry_run,
            )
            rule_report = await rules_importer.execute()
            report.rules_created = rule_report.created
            report.rules_overwritten = rule_report.overwritten
            report.rules_skipped = rule_report.skipped
            report.rules_renamed = rule_report.renamed
            report.rules_failed = rule_report.failed
            rules_failed = rule_report.failed
            report.errors.extend(rule_report.errors)
            report.unresolved_kb_refs.extend(rule_report.unresolved_kb_refs)
            report.unresolved_doc_type_slugs.extend(rule_report.unresolved_doc_type_slugs)

            if not self.dry_run:
                # Reglas recién materializadas ⇒ recompilar (delegado al endpoint).
                imported = await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
                self.rule_ids_to_recompile = [r.uuid for r in imported if r.is_active]
                report.recompilation_scheduled = len(self.rule_ids_to_recompile)

        # --- 4. Finalize pipeline bind ------------------------------------
        # Solo activamos la receta importada (avance de ``current_version`` +
        # rebind del workflow) si las reglas resolvieron sin fallos duros. Una
        # regla rota (p.ej. document_type_slug irresoluble) deja al workflow
        # apuntando a su pipeline original; la versión añadida queda inerte.
        if pending is not None and not self.dry_run:
            if rules_failed == 0:
                await self._finalize_pipeline_bind(workflow, pending)
                report.pipeline_bound = True
            else:
                report.errors.append(
                    f"pipeline: bind deferred — not activated because {rules_failed} rule(s) failed to import"
                )

        return report

    async def _import_pipeline(
        self,
        workflow: Any,
        pipeline_payload: dict[str, Any],
        report: WorkflowBundleImportReport,
    ) -> "_PendingPipelineBind | None":
        slug = (_get(pipeline_payload, "slug") or "").strip()
        if not slug:
            raise ValueError("pipeline.slug is required")
        name = _get(pipeline_payload, "name") or slug
        kind_raw = _get(pipeline_payload, "kind") or PipelineKind.EXTRACTION.value
        kind = PipelineKind(kind_raw)

        raw_phases = _get(pipeline_payload, "phases", default=[]) or []
        phases = [PhaseSpec.model_validate(p) for p in raw_phases]
        # Validate-on-write: cada config contra su modelo tipado. Lanza
        # InvalidPhaseConfigError (ValueError) ⇒ se captura arriba y se reporta.
        validate_phase_configs(phases)
        output_schema = _get(pipeline_payload, "outputSchema", "output_schema")
        # D-A: activación + completitud viajan plegadas en config de fase
        # (extraction_gate.config.activation / await_documents.config) ⇒ las valida
        # validate_phase_configs (arriba). No hay policies version-level que sellar.

        # ADR 0002: el import SIEMPRE appendea una versión al pipeline PROPIO del
        # workflow destino (UNIQUE(workflow_id) ⇒ imposible crear otro). Tras
        # copy-on-create todos lo tienen; defensivo: créalo si faltara (legacy).
        pipeline = await self.pipeline_repository.find_by_workflow(workflow.uuid, self.tenant_id)

        report.pipeline_slug = pipeline.slug if pipeline is not None else slug
        if self.dry_run:
            latest = await self.pipeline_repository.latest_version(pipeline.uuid) if pipeline else None
            report.pipeline_created = pipeline is None
            report.pipeline_version = (latest.version if latest else 0) + 1
            report.pipeline_bound = True
            return None

        if pipeline is None:
            report.pipeline_created = True
            pipeline = await self.pipeline_repository.upsert(
                Pipeline(
                    uuid=uuid4(),
                    workflow_id=workflow.uuid,
                    tenant_id=self.tenant_id,
                    slug=slug,
                    name=name,
                    kind=kind,
                    status=PipelineStatus.ACTIVE,
                    current_version=None,
                )
            )
            report.pipeline_slug = pipeline.slug

        latest = await self.pipeline_repository.latest_version(pipeline.uuid)
        next_version = (latest.version if latest else 0) + 1
        version = await self.pipeline_repository.add_version(
            PipelineVersion(
                uuid=uuid4(),
                pipeline_id=pipeline.uuid,
                version=next_version,
                phases=[p.model_dump(mode="json") for p in phases],
                output_schema=output_schema,
            )
        )
        report.pipeline_version = version.version
        # NO avanzamos current_version aquí: la versión queda añadida (append-only,
        # inocua) pero inerte hasta el finalize tras las reglas — el resolver sigue
        # viendo la receta previa hasta que se confirme.
        return _PendingPipelineBind(pipeline=pipeline, version=version.version, name=name, kind=kind)

    async def _finalize_pipeline_bind(self, workflow: Any, pending: "_PendingPipelineBind") -> None:
        pipeline = pending.pipeline
        # Avanzar el puntero (add_version no lo hace) + nombre/kind por si cambió.
        pipeline.current_version = pending.version
        pipeline.name = pending.name
        pipeline.kind = pending.kind
        await self.pipeline_repository.upsert(pipeline)

        # Tras copy-on-create ``workflow.pipeline_id`` ya apunta a su pipeline; solo
        # rebindeamos si lo acabamos de crear (legacy). Backfill del slug del
        # workflow (git-able W4) si falta.
        changed = False
        if workflow.pipeline_id != pipeline.uuid:
            workflow.pipeline_id = pipeline.uuid
            changed = True
        if not workflow.slug:
            existing_workflows = await self.workflow_repository.list_by_tenant(self.tenant_id)
            existing_slugs = {w.slug for w in existing_workflows if w.slug and w.uuid != workflow.uuid}
            base = slugify_doctype_name(workflow.name)
            workflow.slug = compute_unique_slug(base, existing_slugs)
            changed = True
        if changed:
            await self.workflow_repository.update(workflow)


@dataclass
class _PendingPipelineBind:
    """Pipeline + versión preparados, pendientes de activación tras las reglas."""

    pipeline: Pipeline
    version: int
    name: str
    kind: PipelineKind
