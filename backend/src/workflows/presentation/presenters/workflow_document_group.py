from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_document_group import (
    WorkflowDocumentGroup,
)
from src.workflows.presentation.presenters.workflow_document import WorkflowDocumentPresenter
from src.workflows.presentation.presenters.document_type import (
    DocumentTypePresenter,
)


@dataclass
class WorkflowDocumentGroupPresenter(Presenter[WorkflowDocumentGroup]):
    instance: WorkflowDocumentGroup

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": DocumentTypePresenter(instance=self.instance.document_type).to_dict,
            "documents": [WorkflowDocumentPresenter(instance=d).to_dict for d in self.instance.documents],
        }
