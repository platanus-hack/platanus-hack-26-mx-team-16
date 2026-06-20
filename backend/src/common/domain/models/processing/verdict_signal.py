from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)


@dataclass(frozen=True)
class VerdictSignal:
    """Derived, in-memory signal a rule kind contributes to the verdict aggregator
    (spec §3.4). Never persisted."""

    rule_id: UUID
    kind: str
    severity: WorkflowRuleSeverity
    polarity: WorkflowRuleVerdictPolarity
    weight: float = 1.0
    detail: dict[str, Any] = field(default_factory=dict)
