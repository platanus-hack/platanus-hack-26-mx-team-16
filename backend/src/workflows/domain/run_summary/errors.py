from src.common.domain.exceptions._base import DomainError


class SummaryNotFoundError(DomainError):
    def __init__(self, run_id: str = ""):
        super().__init__(
            code="processing.SummaryNotFound",
            message=f"Summary not found for run: {run_id}" if run_id else "Summary not found",
            status_code=404,
        )


class SynthesisDisabledError(DomainError):
    def __init__(self, workflow_id: str = ""):
        super().__init__(
            code="processing.SynthesisDisabled",
            message=(
                f"Synthesis is disabled for workflow: {workflow_id}"
                if workflow_id
                else "Synthesis is disabled for this workflow"
            ),
            status_code=400,
        )


class OutputSchemaInvalidError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.OutputSchemaInvalid",
            message=f"Synthesis output_schema is invalid: {reason}",
            status_code=400,
        )


class SynthesisOutputInvalidError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.SynthesisOutputInvalid",
            message=f"Synthesis output does not match workflow.output_schema: {reason}",
            status_code=422,
        )
