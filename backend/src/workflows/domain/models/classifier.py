"""Registry de clasificadores tenant-scoped (phases-config · F3 · D-C).

``classify_pages.classifier`` referencia una entrada de este registry por slug.
La fila guarda QUÉ motor corre (``kind``) y su ``config`` (lambda/prompt/tool);
la **resolución** ocurre en la activity ``resolve_classifier`` (no en el código
del workflow) para no romper el determinismo de Temporal.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.enums.pipelines import ClassifierKind


class Classifier(BaseModel):
    uuid: UUID
    tenant_id: UUID
    # Único por tenant; lo referencia ``classify_pages.classifier``.
    slug: str
    kind: ClassifierKind
    # Contrato por kind (lo consume ``resolve_classifier``):
    #   lambda → {function, alias?} · prompt → {provider, prompt_template,
    #   output_schema} · tool → {tool_slug, transport}
    config: dict = {}
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
