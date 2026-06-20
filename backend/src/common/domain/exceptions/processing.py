from src.common.domain.exceptions._base import DomainError


class WorkflowNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowNotFound",
            message=f"Extraction workflow not found: {identifier}" if identifier else "Extraction workflow not found",
            status_code=404,
        )


class InvalidWorkflowYamlError(DomainError):
    def __init__(self, detail: str = ""):
        super().__init__(
            code="processing.InvalidWorkflowYaml",
            message=f"Invalid workflow YAML template: {detail}" if detail else "Invalid workflow YAML template",
            status_code=422,
        )


class WorkflowTypeMismatchError(DomainError):
    def __init__(self, message: str = "Workflow type mismatch"):
        super().__init__(
            code="processing.WorkflowTypeMismatch",
            message=message,
            status_code=409,
        )


class WorkflowEventNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowEventNotFound",
            message=f"Workflow event not found: {identifier}" if identifier else "Workflow event not found",
            status_code=404,
        )


class WorkflowWebhookNotConfiguredError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="processing.WorkflowWebhookNotConfigured",
            message="Workflow has no webhook URL/secret configured; cannot deliver.",
            status_code=409,
        )


class WebhookDestinationNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WebhookDestinationNotFound",
            message=(
                f"Webhook destination not found: {identifier}"
                if identifier
                else "Webhook destination not found"
            ),
            status_code=404,
        )


class WorkflowAccessDeniedError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowAccessDenied",
            message=(
                f"You do not have access to this workflow: {identifier}"
                if identifier
                else "You do not have access to this workflow"
            ),
            status_code=403,
        )


class WorkflowMemberNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowMemberNotFound",
            message=f"Workflow member not found: {identifier}" if identifier else "Workflow member not found",
            status_code=404,
        )


class WorkflowMemberAlreadyExistsError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowMemberAlreadyExists",
            message=(
                f"User is already a member of this workflow: {identifier}"
                if identifier
                else "User is already a member of this workflow"
            ),
            status_code=409,
        )


class CaseNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.CaseNotFound",
            message=f"Extraction case not found: {identifier}" if identifier else "Extraction case not found",
            status_code=404,
        )


class DocumentNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.DocumentNotFound",
            message=f"Case document not found: {identifier}" if identifier else "Case document not found",
            status_code=404,
        )


class JobNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.JobNotFound",
            message=f"Extraction job not found: {identifier}" if identifier else "Extraction job not found",
            status_code=404,
        )


class WorkflowPipelineNotConfiguredError(DomainError):
    """El workflow no tiene receta utilizable: ni binding propio ni el
    pipeline `standard-extraction` del tenant con versión activa (E1)."""

    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.WorkflowPipelineNotConfigured",
            message="The workflow has no active pipeline version to run.",
            status_code=409,
            context={"workflow_id": identifier},
        )


class DocumentTypeNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.DocumentTypeNotFound",
            message=f"Document type not found: {identifier}" if identifier else "Document type not found",
            status_code=404,
        )


class InvalidJsonSchemaError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.InvalidJsonSchema",
            message=f"Invalid JSON schema: {reason}",
            status_code=400,
        )


class InvalidValidationRulesError(DomainError):
    def __init__(self, reason: str):
        super().__init__(
            code="processing.InvalidValidationRules",
            message=f"Invalid validation rules: {reason}",
            status_code=400,
        )


# Old AnalysisRule* errors removed — see src.common.domain.exceptions.workflow_rules
# (WorkflowRuleNotFoundError, WorkflowRuleResultNotFoundError, etc.).


class ExtractionAlreadyRunningError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="processing.AlreadyRunning",
            message=f"Extraction is already running for case: {case_id}"
            if case_id
            else "Extraction is already running",
            status_code=409,
        )


class AnalysisNotFoundError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="processing.AnalysisNotFound",
            message=f"Analysis results not found for case: {case_id}" if case_id else "Analysis results not found",
            status_code=404,
        )


class AnalysisAlreadyRunningError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="processing.AnalysisAlreadyRunning",
            message=f"Analysis is already running for case: {case_id}" if case_id else "Analysis is already running",
            status_code=409,
        )


class AnalysisRunNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.AnalysisRunNotFound",
            message=f"Analysis run not found: {identifier}" if identifier else "Analysis run not found",
            status_code=404,
        )


class ExtractionInProgressError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="processing.ExtractionInProgress",
            message=(
                f"Extraction is still in progress for case {case_id}; "
                "wait for it to finish before starting an analysis."
                if case_id
                else "Extraction is still in progress; wait for it to finish before starting an analysis."
            ),
            status_code=409,
        )


class NoDocumentsToAnalyzeError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="processing.NoDocumentsToAnalyze",
            message=(
                f"Case {case_id} has no documents to analyze; "
                "upload at least one document before starting an analysis."
                if case_id
                else "Case has no documents to analyze; upload at least one document before starting an analysis."
            ),
            status_code=422,
        )


class RuleCombinationsExceededError(DomainError):
    def __init__(self, rule_id: str = "", count: int = 0, cap: int = 0):
        super().__init__(
            code="processing.RuleCombinationsExceeded",
            message=(
                f"Rule {rule_id} would generate {count} evaluations (cap: {cap}); reduce documents or split the rule."
            ),
            status_code=400,
        )


class RunCombinationsExceededError(DomainError):
    def __init__(self, count: int = 0, cap: int = 0):
        super().__init__(
            code="processing.RunCombinationsExceeded",
            message=(
                f"This case would generate {count} total evaluations across rules "
                f"(cap: {cap}); reduce documents or rules."
            ),
            status_code=400,
        )


class SampleDocumentNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.SampleDocumentNotFound",
            message="El document type no tiene documento de ejemplo",
            status_code=422,
        )


class SampleTextNotExtractedError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="processing.SampleTextNotExtracted",
            message="El texto del documento de ejemplo aún no está disponible",
            status_code=422,
        )


class OCRError(RuntimeError):
    """Raised when OCR returns no text."""


class StructuringError(RuntimeError):
    """Raised when the LLM structuring step returns no output."""
