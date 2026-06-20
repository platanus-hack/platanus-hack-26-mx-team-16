"""Errors for the redesigned workflow rules domain (spec §10.1)."""

from src.common.domain.exceptions._base import DomainError


class WorkflowRuleNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowRuleNotFound",
            message=f"Workflow rule not found: {identifier}" if identifier else "Workflow rule not found",
            status_code=404,
        )


class UnknownWorkflowRuleKindError(DomainError):
    def __init__(self, kind: str):
        super().__init__(
            code="processing.UnknownWorkflowRuleKind",
            message=f"Unknown workflow rule kind: {kind}",
            status_code=400,
        )


class InvalidWorkflowRuleConfigError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.InvalidWorkflowRuleConfig",
            message=f"Invalid workflow rule config: {reason}",
            status_code=400,
        )


class CompilationFailedError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.WorkflowRuleCompilationFailed",
            message=f"Workflow rule compilation failed: {reason}",
            status_code=500,
        )


class WorkflowRuleScopeMismatchError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.WorkflowRuleScopeMismatch",
            message=f"Workflow rule scope mismatch: {reason}",
            status_code=400,
        )


class WorkflowRuleCompilationNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowRuleCompilationNotFound",
            message=(
                f"Workflow rule compilation not found: {identifier}"
                if identifier
                else "Workflow rule compilation not found"
            ),
            status_code=404,
        )


class WorkflowRuleResultNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowRuleResultNotFound",
            message=(
                f"Workflow rule result not found: {identifier}" if identifier else "Workflow rule result not found"
            ),
            status_code=404,
        )


class WorkflowAnalysisRunNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowAnalysisRunNotFound",
            message=(
                f"Workflow analysis run not found: {identifier}" if identifier else "Workflow analysis run not found"
            ),
            status_code=404,
        )
