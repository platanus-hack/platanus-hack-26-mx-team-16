from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.kind_protocol import WorkflowRuleKind


@dataclass
class WorkflowRuleKindPresenter(Presenter[WorkflowRuleKind]):
    instance: WorkflowRuleKind

    @property
    def to_dict(self) -> dict[str, Any]:
        # output_schema may depend on a rule (DERIVATION). The registry endpoint
        # returns the *static* shape: a sample built from default_config.
        sample_rule = WorkflowRule(
            uuid=__import__("uuid").uuid4(),
            tenant_id=__import__("uuid").uuid4(),
            workflow_id=__import__("uuid").uuid4(),
            name="__sample__",
            kind=self.instance.name,
            prompt="sample",
            config=self.instance.default_config(),
        )
        try:
            output_schema = self.instance.output_schema_for(sample_rule)
        except Exception:
            output_schema = {}

        return {
            "name": self.instance.name,
            "label": self.instance.label,
            "description": self.instance.description,
            "config_schema": RawJson(self.instance.config_schema),
            "default_config": RawJson(self.instance.default_config()),
            "output_schema": RawJson(output_schema),
        }
