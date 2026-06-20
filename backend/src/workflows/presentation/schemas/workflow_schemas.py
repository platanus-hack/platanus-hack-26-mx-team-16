from uuid import UUID

from pydantic import Field, field_validator

from src.common.application.helpers.webhooks.url_validation import validate_webhook_url
from src.common.domain.entities.common.requests import CamelCaseRequest


class CreateWorkflowRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)
    # E7 · F2: el alta elige una PLANTILLA de pipeline por slug (None ⇒ extracción
    # estándar). Reemplaza al difunto `workflow_type` STANDARD|ANALYSIS.
    template_slug: str | None = Field(default=None, max_length=120)
    industry_id: UUID | None = Field(default=None)
    selected_doc_types: list = Field(default_factory=list)
    kb_document_ids: list = Field(default_factory=list)
    per_doc_kb_ids: dict = Field(default_factory=dict)
    structuring_model: str | None = Field(default=None, max_length=100)
    llm_model: str | None = Field(default=None, max_length=100)


class CreateWorkflowFromYamlRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)
    # Texto YAML crudo de un envelope de bundle (mismo shape que GET /export):
    # doc-types + pipeline + reglas. El backend lo parsea e importa con overwrite.
    yaml: str = Field(..., min_length=1)


class UpdateWorkflowRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    selected_doc_types: list | None = Field(default=None)
    kb_document_ids: list | None = Field(default=None)
    per_doc_kb_ids: dict | None = Field(default=None)
    structuring_model: str | None = Field(default=None, max_length=100)
    llm_model: str | None = Field(default=None, max_length=100)
    webhook_url: str | None = Field(default=None, max_length=2048)
    webhook_enabled: bool | None = Field(default=None)
    webhook_events: list[str] | None = Field(default=None)
    # Sustantivo visible del caso por workflow: {es:{one,other}, en:{one,other}}.
    # product/specs/data-model/case-noun.md §2. null ⇒ borra el override (default i18n).
    case_noun: dict[str, dict[str, str]] | None = Field(default=None)

    @field_validator("webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        return validate_webhook_url(value)

    @field_validator("case_noun")
    @classmethod
    def _validate_case_noun(cls, value: dict | None) -> dict | None:
        # Si viene, ambos locales con `one`+`other` no vacíos (≤MAX chars). Los
        # plurales son SIEMPRE explícitos; la UI no pluraliza ni transforma.
        if value is None:
            return value
        max_len = 30
        for locale in ("es", "en"):
            forms = value.get(locale)
            if not isinstance(forms, dict):
                msg = f"case_noun[{locale!r}] is required with 'one' and 'other'"
                raise ValueError(msg)
            for form in ("one", "other"):
                text = forms.get(form)
                if not isinstance(text, str) or not text.strip():
                    msg = f"case_noun[{locale!r}][{form!r}] must be a non-empty string"
                    raise ValueError(msg)
                if len(text) > max_len:
                    msg = f"case_noun[{locale!r}][{form!r}] must be <= {max_len} chars"
                    raise ValueError(msg)
        return value
