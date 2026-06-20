from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow import Workflow


@dataclass
class WorkflowPresenter(Presenter[Workflow]):
    instance: Workflow
    # E7 · F0: capacidades derivadas del pipeline vigente (no de ``workflow_type``).
    # La capa de aplicación las precalcula (``WorkflowCapabilitiesResolver``) y el
    # FE las usa para gatear tabs/acciones. ``None`` ⇒ ``[]`` (aún no resueltas).
    capabilities: list[str] | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": str(self.instance.uuid),
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "industry_id": str(self.instance.industry_id) if self.instance.industry_id else None,
            "name": self.instance.name,
            # E7 · F2: `workflow_type` retirado — el FE gatea por `capabilities`.
            "capabilities": self.capabilities if self.capabilities is not None else [],
            "access_type": self.instance.access_type,
            "created_by_id": str(self.instance.created_by_id) if self.instance.created_by_id else None,
            "selected_doc_types": self.instance.selected_doc_types,
            "kb_document_ids": self.instance.kb_document_ids,
            "per_doc_kb_ids": RawJson(self.instance.per_doc_kb_ids),
            "structuring_model": self.instance.structuring_model,
            "llm_model": self.instance.llm_model,
            "output_schema": RawJson(self.instance.output_schema),
            "synthesis_template": self.instance.synthesis_template,
            "synthesis_enabled": self.instance.synthesis_enabled,
            "webhook_url": self.instance.webhook_url,
            "webhook_enabled": self.instance.webhook_enabled,
            "webhook_events": self.instance.webhook_events,
            # Sustantivo del caso por workflow (es/en · one/other) o null ⇒ default
            # i18n en el FE. La envoltura de respuesta cameliza a `caseNoun`; las
            # claves anidadas (es/en/one/other) no llevan guion ⇒ intactas.
            "case_noun": self.instance.case_noun,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
