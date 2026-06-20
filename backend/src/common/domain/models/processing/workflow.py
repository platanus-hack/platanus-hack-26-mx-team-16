from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkflowAccessType = Literal["organization", "private"]

DEFAULT_REVIEWER_MODEL = "gpt-5"
DEFAULT_CRITIC_MODEL = "gemini-2.5-pro"
DEFAULT_CONSENSUS_SAMPLES = 5


class Workflow(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    industry_id: UUID | None = Field(default=None)
    # Receta del intérprete que corre todo upload (E1). None ⇒ fallback al
    # pipeline `standard-extraction` del tenant en el dispatcher.
    pipeline_id: UUID | None = Field(default=None)
    name: str = Field(..., min_length=1, max_length=255)
    # Slug git-able del workflow (nullable en BD). El bundle import lo genera si
    # falta para que el find-or-create por slug sea estable (E6 · W4).
    slug: str | None = Field(default=None, max_length=120)
    # E7 · F2: `workflow_type` (STANDARD|ANALYSIS) murió — las capacidades se
    # derivan del pipeline (derive_capabilities), no de un enum.
    access_type: WorkflowAccessType = Field(default="organization")
    created_by_id: UUID | None = Field(default=None)
    selected_doc_types: list = Field(default_factory=list)
    kb_document_ids: list = Field(default_factory=list)
    per_doc_kb_ids: dict = Field(default_factory=dict)
    structuring_model: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
    analysis_reviewer_model: str | None = Field(default=None, max_length=100)
    analysis_critic_model: str | None = Field(default=None, max_length=100)
    analysis_consensus_samples: int | None = Field(default=None, ge=3, le=9)
    output_schema: dict[str, Any] | None = Field(default=None)
    synthesis_template: str | None = Field(default=None)
    synthesis_enabled: bool = Field(default=False)
    synthesis_uses_documents: bool = Field(default=False)  # A4
    webhook_url: str | None = Field(default=None, max_length=2048)
    webhook_enabled: bool = Field(default=False)
    webhook_secret: str | None = Field(default=None, max_length=255)
    webhook_events: list[str] = Field(default_factory=lambda: ["document.extracted", "document.failed"])
    # Sustantivo visible del caso, configurable por workflow (es/en · one/other).
    # None ⇒ la UI usa el default i18n («Caso/Casos», "Case/Cases"). El nombre
    # técnico `case` no cambia (product/specs/data-model/case-noun.md).
    case_noun: dict | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def reviewer_model(self) -> str:
        return self.analysis_reviewer_model or DEFAULT_REVIEWER_MODEL

    @property
    def critic_model(self) -> str:
        return self.analysis_critic_model or DEFAULT_CRITIC_MODEL

    @property
    def consensus_samples(self) -> int:
        return self.analysis_consensus_samples or DEFAULT_CONSENSUS_SAMPLES

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "industry_id": self.industry_id,
            "name": self.name,
            "access_type": self.access_type,
            "created_by_id": self.created_by_id,
            "selected_doc_types": self.selected_doc_types,
            "kb_document_ids": self.kb_document_ids,
            "per_doc_kb_ids": self.per_doc_kb_ids,
            "structuring_model": self.structuring_model,
            "llm_model": self.llm_model,
            "analysis_reviewer_model": self.analysis_reviewer_model,
            "analysis_critic_model": self.analysis_critic_model,
            "analysis_consensus_samples": self.analysis_consensus_samples,
            "output_schema": self.output_schema,
            "synthesis_template": self.synthesis_template,
            "synthesis_enabled": self.synthesis_enabled,
            "webhook_url": self.webhook_url,
            "webhook_enabled": self.webhook_enabled,
            "webhook_secret": self.webhook_secret,
            "webhook_events": self.webhook_events,
            "case_noun": self.case_noun,
        }
