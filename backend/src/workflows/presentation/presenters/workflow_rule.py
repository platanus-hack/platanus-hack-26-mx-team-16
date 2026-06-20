from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.uuids import optional_string
from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_rule import WorkflowRule


@dataclass
class WorkflowRulePresenter(Presenter[WorkflowRule]):
    instance: WorkflowRule

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "name": self.instance.name,
            "slug": self.instance.slug,
            "position": self.instance.position,
            "is_active": self.instance.is_active,
            "kind": self.instance.kind,
            "prompt": self.instance.prompt,
            "when": self.instance.when,
            "config": RawJson(self.instance.config),
            "scope": RawJson(self.instance.scope),
            "knowledge_refs": [str(knowledge_ref) for knowledge_ref in (self.instance.knowledge_refs or [])],
            "current_compilation_id": optional_string(self.instance.current_compilation_id),
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
