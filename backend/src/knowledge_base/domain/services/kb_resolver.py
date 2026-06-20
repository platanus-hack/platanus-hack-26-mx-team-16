"""Bulk slug → KBDocument lookup with workflow → tenant fallback.

Compile pipelines call this to validate `#{kb_slug}` references in rule
prompts; evaluation pipelines call it to seed `knowledge_context`. Workflow
KBs win over tenant-level KBs when the same slug is registered in both
scopes (the repository enforces uniqueness inside each scope).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)


@dataclass
class KBDocumentResolver:
    repo: KBDocumentRepository

    async def resolve(
        self,
        tenant_id: UUID,
        workflow_id: UUID,
        slugs: Iterable[str],
    ) -> dict[str, KBDocument]:
        return await self.repo.resolve_slugs(tenant_id, workflow_id, slugs)
