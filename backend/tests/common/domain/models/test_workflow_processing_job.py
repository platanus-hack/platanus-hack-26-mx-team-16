from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_none, equal, expect, raise_error
from pydantic import ValidationError

from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob


def _minimal_kwargs() -> dict:
    return {
        "uuid": uuid4(),
        "temporal_workflow_id": "CASE#abc_FILE#def",
        "tenant_id": uuid4(),
        "workflow_id": uuid4(),
        "file_id": uuid4(),
    }


def test_workflow_case_id__defaults_to_none_for_standard_workflows():
    processing_job = WorkflowProcessingJob(**_minimal_kwargs())

    expect(processing_job.workflow_case_id).to(be_none)


def test_status__defaults_to_pending():
    processing_job = WorkflowProcessingJob(**_minimal_kwargs())

    expect(processing_job.status).to(equal(WorkflowProcessingJobStatus.PENDING))


def test_last_seq__defaults_to_zero():
    processing_job = WorkflowProcessingJob(**_minimal_kwargs())

    expect(processing_job.last_seq).to(equal(0))


def test_attempts__defaults_to_zero():
    processing_job = WorkflowProcessingJob(**_minimal_kwargs())

    expect(processing_job.attempts).to(equal(0))


@pytest.mark.parametrize(
    "field",
    ["error", "result_summary", "current_step", "extracted_text", "classified_pages"],
)
def test_optional_fields__default_to_none(field):
    processing_job = WorkflowProcessingJob(**_minimal_kwargs())

    expect(getattr(processing_job, field)).to(be_none)


def test_workflow_case_id__accepts_uuid_for_analysis_workflows():
    case_id = uuid4()

    processing_job = WorkflowProcessingJob(
        **_minimal_kwargs(),
        workflow_case_id=case_id,
    )

    expect(processing_job.workflow_case_id).to(equal(case_id))


@pytest.mark.parametrize(
    "missing_field",
    ["uuid", "temporal_workflow_id", "tenant_id", "workflow_id", "file_id"],
)
def test_required_fields__missing_raises(missing_field):
    kwargs = _minimal_kwargs()
    del kwargs[missing_field]

    expect(lambda: WorkflowProcessingJob(**kwargs)).to(raise_error(ValidationError))


def test_status__accepts_enum_value_strings():
    processing_job = WorkflowProcessingJob(
        **_minimal_kwargs(),
        status=WorkflowProcessingJobStatus.RUNNING,
    )

    expect(processing_job.status).to(equal(WorkflowProcessingJobStatus.RUNNING))


def test_from_attributes__validates_orm_like_object():
    # Simulates SQLAlchemy ORM row → Pydantic model_validate flow.
    class FakeORM:
        uuid = uuid4()
        temporal_workflow_id = "CASE#xyz_FILE#qrs"
        tenant_id = uuid4()
        workflow_id = uuid4()
        workflow_case_id = None
        file_id = uuid4()
        status = "RUNNING"
        attempts = 1
        error = None
        result_summary = None
        current_step = "extract_text"
        last_seq = 7
        extracted_text = "s3://bucket/extracted.json"
        classified_pages = None
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

    processing_job = WorkflowProcessingJob.model_validate(FakeORM())

    expect(processing_job.status).to(equal(WorkflowProcessingJobStatus.RUNNING))
    expect(processing_job.last_seq).to(equal(7))
    expect(processing_job.current_step).to(equal("extract_text"))
