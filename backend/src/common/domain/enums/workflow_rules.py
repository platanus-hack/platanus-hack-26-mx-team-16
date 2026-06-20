"""Enums for the redesigned workflow rules domain (spec §3, §5, §7)."""

from src.common.domain.enums.base_enum import BaseEnum


class WorkflowAnalysisRunStatus(str, BaseEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELING = "CANCELING"
    CANCELED = "CANCELED"

    @property
    def is_active(self) -> bool:
        return self in (WorkflowAnalysisRunStatus.RUNNING, WorkflowAnalysisRunStatus.CANCELING)

    @property
    def is_terminal(self) -> bool:
        return self in (
            WorkflowAnalysisRunStatus.COMPLETED,
            WorkflowAnalysisRunStatus.FAILED,
            WorkflowAnalysisRunStatus.CANCELED,
        )


class WorkflowAnalysisRunTrigger(str, BaseEnum):
    USER = "USER"
    RETRY = "RETRY"
    SCHEDULED = "SCHEDULED"
    SYSTEM = "SYSTEM"


class WorkflowRuleCompilationStatus(str, BaseEnum):
    """Lifecycle of a compilation row (spec §3.2)."""

    PENDING = "PENDING"
    COMPILING = "COMPILING"
    READY = "READY"
    FAILED = "FAILED"
    STALE = "STALE"

    @property
    def is_pending(self) -> bool:
        return self == WorkflowRuleCompilationStatus.PENDING

    @property
    def is_compiling(self) -> bool:
        return self == WorkflowRuleCompilationStatus.COMPILING

    @property
    def is_ready(self) -> bool:
        return self == WorkflowRuleCompilationStatus.READY

    @property
    def is_failed(self) -> bool:
        return self == WorkflowRuleCompilationStatus.FAILED

    @property
    def is_stale(self) -> bool:
        return self == WorkflowRuleCompilationStatus.STALE

    @property
    def is_terminal(self) -> bool:
        return self.is_ready or self.is_failed or self.is_stale


class WorkflowRuleResultStatus(str, BaseEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERRORED = "ERRORED"
    SKIPPED = "SKIPPED"

    @property
    def is_success(self) -> bool:
        return self == WorkflowRuleResultStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self == WorkflowRuleResultStatus.FAILED

    @property
    def is_errored(self) -> bool:
        return self == WorkflowRuleResultStatus.ERRORED

    @property
    def is_skipped(self) -> bool:
        return self == WorkflowRuleResultStatus.SKIPPED


class WorkflowRuleScopeMode(str, BaseEnum):
    SINGLE_DOCUMENT = "SINGLE_DOCUMENT"
    TUPLE_CARTESIAN = "TUPLE_CARTESIAN"
    AGGREGATE_OVER_TYPE = "AGGREGATE_OVER_TYPE"
    ALL_DOCUMENTS = "ALL_DOCUMENTS"

    @property
    def is_single_document(self) -> bool:
        return self == WorkflowRuleScopeMode.SINGLE_DOCUMENT

    @property
    def is_tuple_cartesian(self) -> bool:
        return self == WorkflowRuleScopeMode.TUPLE_CARTESIAN

    @property
    def is_aggregate_over_type(self) -> bool:
        return self == WorkflowRuleScopeMode.AGGREGATE_OVER_TYPE

    @property
    def is_all_documents(self) -> bool:
        return self == WorkflowRuleScopeMode.ALL_DOCUMENTS


class WorkflowRuleOnEmpty(str, BaseEnum):
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    PASSED = "PASSED"

    @property
    def is_skipped(self) -> bool:
        return self == WorkflowRuleOnEmpty.SKIPPED

    @property
    def is_failed(self) -> bool:
        return self == WorkflowRuleOnEmpty.FAILED

    @property
    def is_passed(self) -> bool:
        return self == WorkflowRuleOnEmpty.PASSED


class WorkflowRuleSeverity(str, BaseEnum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

    @property
    def is_blocking(self) -> bool:
        return self == WorkflowRuleSeverity.BLOCKER

    @property
    def is_major(self) -> bool:
        return self == WorkflowRuleSeverity.MAJOR

    @property
    def is_minor(self) -> bool:
        return self == WorkflowRuleSeverity.MINOR

    @property
    def is_info(self) -> bool:
        return self == WorkflowRuleSeverity.INFO


class WorkflowRuleVerdictPolarity(str, BaseEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEUTRAL = "NEUTRAL"

    @property
    def is_pass(self) -> bool:
        return self == WorkflowRuleVerdictPolarity.PASS

    @property
    def is_fail(self) -> bool:
        return self == WorkflowRuleVerdictPolarity.FAIL

    @property
    def is_neutral(self) -> bool:
        return self == WorkflowRuleVerdictPolarity.NEUTRAL


class WorkflowRuleFailAction(str, BaseEnum):
    BLOCK = "BLOCK"
    WARN = "WARN"

    @property
    def is_blocking(self) -> bool:
        return self == WorkflowRuleFailAction.BLOCK

    @property
    def is_warning(self) -> bool:
        return self == WorkflowRuleFailAction.WARN
