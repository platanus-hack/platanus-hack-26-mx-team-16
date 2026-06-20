"""Enums for the workflow-analysis-run summary aggregate (synthesis spec §3, §5.1)."""

from src.common.domain.enums.base_enum import BaseEnum


class Verdict(str, BaseEnum):
    """Final reproducible decision the verdict_aggregator computes from VerdictSignals."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class NarrativeStatus(str, BaseEnum):
    """State machine of the LLM-driven narrative leg of the summary."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
