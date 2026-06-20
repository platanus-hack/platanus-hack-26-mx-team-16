"""Execute a pending compilation: invoke kind.compile() and persist artifact."""

from __future__ import annotations

from dataclasses import dataclass
from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.exceptions.workflow_rules import (
    WorkflowRuleCompilationNotFoundError,
    WorkflowRuleNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.knowledge_base.domain.services.kb_resolver import KBDocumentResolver
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.rules.kind_protocol import CompileContext
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.infrastructure.services.rules import registry

from uuid import UUID

logger = get_logger(__name__)


@dataclass
class WorkflowRuleCompilationRunner(UseCase):
    """Run one pending compilation row to completion (success or failure)."""

    compilation_id: UUID
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository
    compilation_repository: WorkflowRuleCompilationRepository
    document_type_repository: DocumentTypeRepository
    kb_resolver: KBDocumentResolver | None = None

    async def execute(self) -> WorkflowRuleCompilation:
        rule = await self.rule_repository.find_by_id(self.rule_id, self.tenant_id)
        if not rule:
            raise WorkflowRuleNotFoundError(str(self.rule_id))

        compilation = await self.compilation_repository.find_by_id(self.compilation_id)
        if not compilation:
            raise WorkflowRuleCompilationNotFoundError(str(self.compilation_id))

        await self.compilation_repository.mark_status(self.compilation_id, WorkflowRuleCompilationStatus.COMPILING)

        kind = registry.get(rule.kind)
        ctx = CompileContext(
            workflow_id=rule.workflow_id,
            tenant_id=rule.tenant_id,
            document_types=await self.document_type_repository.list_by_workflow(rule.workflow_id, rule.tenant_id),
            kb_resolver=self.kb_resolver,
        )

        try:
            outcome = await kind.compile(rule, ctx)
        except Exception as exc:
            logger.exception("workflow_rule.compilation.failed", rule_id=str(rule.uuid))
            failed = await self.compilation_repository.mark_status(
                self.compilation_id,
                WorkflowRuleCompilationStatus.FAILED,
                error=str(exc),
            )
            return failed

        ready = await self.compilation_repository.mark_status(
            self.compilation_id,
            WorkflowRuleCompilationStatus.READY,
            artifact=outcome.artifact,
            compiled_with=outcome.compiled_with,
        )
        # Compile is the source of truth for `WorkflowRule.knowledge_refs`:
        # mirror the resolved UUIDs from the artifact onto the rule so eval
        # paths can read them without re-resolving slugs.
        artifact_kb_refs = [
            UUID(ref) if isinstance(ref, str) else ref for ref in (outcome.artifact.get("knowledge_refs") or [])
        ]
        if artifact_kb_refs != list(rule.knowledge_refs or []):
            rule.knowledge_refs = artifact_kb_refs
            await self.rule_repository.update(rule)
        await self.rule_repository.set_current_compilation(self.rule_id, self.tenant_id, ready.uuid)
        return ready
