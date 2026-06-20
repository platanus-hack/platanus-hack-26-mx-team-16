from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)


@dataclass
class WorkflowRuleCompilationPresenter(Presenter[WorkflowRuleCompilation]):
    instance: WorkflowRuleCompilation

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "rule_id": str(self.instance.rule_id),
            "version": self.instance.version,
            "kind": self.instance.kind,
            "status": self.instance.status.value,
            "artifact": RawJson(self.instance.artifact),
            "compiled_with": RawJson(self.instance.compiled_with),
            "error": self.instance.error,
            "created_at": optional_datetime_string(self.instance.created_at),
            "completed_at": optional_datetime_string(self.instance.completed_at),
        }
