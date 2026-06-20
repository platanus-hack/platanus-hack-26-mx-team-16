from dataclasses import dataclass, field
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.processing.workflow_document_group import WorkflowDocumentGroup
from src.workflows.presentation.presenters.workflow_document import WorkflowDocumentPresenter
from src.workflows.presentation.presenters.workflow_document_group import WorkflowDocumentGroupPresenter


@dataclass
class WorkflowCasePresenter(Presenter[WorkflowCase]):
    instance: WorkflowCase
    documents: list[WorkflowDocument] | None = None
    # Re-IA 2026-06: algún run de procesamiento FAILED ⇒ badge «Procesamiento
    # fallido» en la lista (el estado público del caso NO cambia).
    has_failed_runs: bool = False

    @property
    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "case_id": str(self.instance.uuid),
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "name": self.instance.name,
            "status": self.instance.status.value,
            "last_ocr_provider": self.instance.last_ocr_provider,
            "created_by": str(self.instance.created_by) if self.instance.created_by else None,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
            # E5 · fan-out: lineage child→padre (null en casos normales).
            "parentCaseId": str(self.instance.parent_case_id) if self.instance.parent_case_id else None,
            "hasFailedRuns": self.has_failed_runs,
        }
        # N documents per document_type_id are possible (bulk uploads), so the
        # frontend groups client-side. A null document_type_id means the extractor
        # classified a doctype that isn't part of this workflow ("Otros" bucket).
        docs = self.documents or []
        result["documents"] = [WorkflowDocumentPresenter(instance=d).to_dict for d in docs]
        return result


def present_children_summary(children_by_status: dict[str, int] | None) -> dict[str, Any] | None:
    """``{total, byStatus}`` del fan-out (E5) — None si el caso no tiene children."""
    if not children_by_status:
        return None
    return {
        "total": sum(children_by_status.values()),
        "byStatus": dict(children_by_status),
    }


@dataclass
class WorkflowCaseDetailPresenter(Presenter[WorkflowCase]):
    instance: WorkflowCase
    document_groups: list[WorkflowDocumentGroup] = field(default_factory=list)
    timeline: list[Any] | None = None  # CaseEvent desc, límite 50 (E4)
    # E5 · fan-out: {status: n} de los children (None/{} ⇒ sin children).
    children_by_status: dict[str, int] | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": str(self.instance.uuid),
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "name": self.instance.name,
            "status": self.instance.status.value,
            "last_ocr_provider": self.instance.last_ocr_provider,
            "created_by": str(self.instance.created_by) if self.instance.created_by else None,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
            "document_groups": [WorkflowDocumentGroupPresenter(instance=g).to_dict for g in self.document_groups],
            # E4 — shapes EXACTOS del FE (camelCase):
            "timeline": [
                {
                    "uuid": str(e.uuid),
                    "type": e.type,
                    "payload": e.payload,
                    "actor": e.actor,
                    "createdAt": optional_datetime_string(e.created_at),
                }
                for e in self.timeline or []
            ],
            "completeness": self.instance.completeness,
            "readyAt": optional_datetime_string(self.instance.ready_at),
            # E5 · fan-out: lineage + resumen de children (None si no es padre).
            "parentCaseId": str(self.instance.parent_case_id) if self.instance.parent_case_id else None,
            "children": present_children_summary(self.children_by_status),
        }
