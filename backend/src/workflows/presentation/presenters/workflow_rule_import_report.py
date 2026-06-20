from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.workflows.application.workflow_rules.import_export.report import WorkflowRuleImportReport


@dataclass
class WorkflowRuleImportReportPresenter(Presenter[WorkflowRuleImportReport]):
    instance: WorkflowRuleImportReport

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.instance.created,
            "overwritten": self.instance.overwritten,
            "skipped": self.instance.skipped,
            "renamed": self.instance.renamed,
            "failed": self.instance.failed,
            "errors": list(self.instance.errors),
            "unresolved_kb_refs": list(self.instance.unresolved_kb_refs),
            "unresolved_doc_type_slugs": list(self.instance.unresolved_doc_type_slugs),
        }
