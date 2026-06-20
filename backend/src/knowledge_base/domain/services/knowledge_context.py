"""Build the ``knowledge_context`` injected into rule evaluation (F5 · B2 fix).

A rule carries ``knowledge_refs`` (KB document UUIDs). The evaluation activity used
to pass ``knowledge_context=[]`` — so ``#kb`` references resolved to nothing. This
hydrates those refs into the context the evaluator feeds the LLM, enabling e.g.
drug-name normalisation against a client-provided KB (B2).
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)


async def build_knowledge_context(
    repo: KBDocumentRepository,
    tenant_id: UUID,
    knowledge_refs: Iterable[UUID],
) -> list[dict]:
    """``[{slug, title, content}]`` for each resolvable, vectorised KB ref."""
    context: list[dict] = []
    for ref in knowledge_refs or []:
        document = await repo.find_by_id(ref, tenant_id)
        if document is None or not document.extracted_text:
            continue
        context.append(
            {
                "slug": document.slug,
                "title": document.file_name,
                "content": document.extracted_text,
            }
        )
    return context
