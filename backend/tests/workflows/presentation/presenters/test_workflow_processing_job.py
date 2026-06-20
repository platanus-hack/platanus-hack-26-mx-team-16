from datetime import UTC, datetime
from uuid import uuid4

from expects import be_none, contain, equal, expect, have_key

from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.presentation.presenters.workflow_processing_job import (
    WorkflowProcessingJobPresenter,
)


def _build(**overrides) -> WorkflowProcessingJob:
    base = {
        "uuid": uuid4(),
        "temporal_workflow_id": "CASE#abc_FILE#def",
        "tenant_id": uuid4(),
        "workflow_id": uuid4(),
        "workflow_case_id": uuid4(),
        "file_id": uuid4(),
        "status": WorkflowProcessingJobStatus.RUNNING,
        "current_step": "extract_text",
        "last_seq": 5,
        "attempts": 1,
        "error": None,
        "result_summary": {"docs": 3},
        "created_at": datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 30, 12, 5, tzinfo=UTC),
    }
    base.update(overrides)
    return WorkflowProcessingJob(**base)


def test_to_dict__returns_snake_case_keys():
    presenter = WorkflowProcessingJobPresenter(instance=_build())

    result = presenter.to_dict

    for key in (
        "set_id",
        "temporal_workflow_id",
        "tenant_id",
        "workflow_id",
        "workflow_case_id",
        "file_id",
        "status",
        "current_step",
        "last_seq",
        "attempts",
        "error",
        "result_summary",
        "created_at",
        "updated_at",
    ):
        expect(result).to(have_key(key))


def test_to_dict__serializes_uuids_as_strings():
    processing_job = _build()

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["set_id"]).to(equal(str(processing_job.uuid)))
    expect(result["workflow_id"]).to(equal(str(processing_job.workflow_id)))
    expect(result["file_id"]).to(equal(str(processing_job.file_id)))


def test_to_dict__workflow_case_id_is_none_for_standard_workflows():
    processing_job = _build(workflow_case_id=None)

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["workflow_case_id"]).to(be_none)


def test_to_dict__status_is_enum_value_string():
    processing_job = _build(status=WorkflowProcessingJobStatus.COMPLETED)

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["status"]).to(equal("COMPLETED"))


def test_to_dict__timestamps_serialize_as_iso_strings():
    processing_job = _build()

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["created_at"]).to(contain("2026-04-30T12:00:00"))
    expect(result["updated_at"]).to(contain("2026-04-30T12:05:00"))


def test_to_dict__handles_none_timestamps():
    processing_job = _build(created_at=None, updated_at=None)

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["created_at"]).to(be_none)
    expect(result["updated_at"]).to(be_none)


def test_to_dict__preserves_result_summary_dict():
    summary = {"docs": 3, "extractor": "lambda"}
    processing_job = _build(result_summary=summary)

    result = WorkflowProcessingJobPresenter(instance=processing_job).to_dict

    expect(result["result_summary"]).to(equal(summary))
