from expects import be_empty, be_false, be_none, equal, expect

from src.common.domain.entities.workflows.document_processing import (
    BBoxHit,
    DocumentProcessingInput,
    DocumentProcessingOutput,
    MappedLeaf,
)


SAMPLE_POLYGON = [
    {"x": 0.255, "y": 0.778},
    {"x": 0.406, "y": 0.778},
    {"x": 0.406, "y": 0.788},
    {"x": 0.255, "y": 0.788},
]


def test_bbox_hit__accepts_required_fields():
    bbox = BBoxHit(
        page_number=1,
        polygon=SAMPLE_POLYGON,
        matched_text="LAURA VERONICA",
        confidence=0.997,
    )

    expect(bbox.page_number).to(equal(1))
    expect(bbox.matched_text).to(equal("LAURA VERONICA"))


def test_bbox_hit__confidence_defaults_to_none():
    bbox = BBoxHit(
        page_number=1,
        polygon=SAMPLE_POLYGON,
        matched_text="x",
    )

    expect(bbox.confidence).to(be_none)


def test_mapped_leaf__defaults_for_empty_match():
    leaf = MappedLeaf()

    expect(leaf.value).to(be_none)
    expect(leaf.source_text).to(be_none)
    expect(leaf.page_number).to(be_none)
    expect(leaf.bbox).to(be_empty)
    expect(leaf.inferred).to(be_false)


def test_mapped_leaf__accepts_full_payload():
    bbox = BBoxHit(page_number=1, polygon=SAMPLE_POLYGON, matched_text="x")

    leaf = MappedLeaf(
        value="LAURA VERONICA",
        source_text="LAURA VERONICA",
        page_number=1,
        bbox=[bbox],
        inferred=False,
    )

    expect(leaf.value).to(equal("LAURA VERONICA"))
    expect(leaf.bbox).to(equal([bbox]))


def test_document_processing_input__requires_only_three_fields():
    payload = DocumentProcessingInput(
        object_key="s3://bucket/file.pdf",
        document_types=[{"uuid": "dt-1", "name": "Cedula"}],
        job_id="job-1",
    )

    expect(payload.object_key).to(equal("s3://bucket/file.pdf"))
    expect(payload.document_types).to(equal([{"uuid": "dt-1", "name": "Cedula"}]))
    expect(payload.job_id).to(equal("job-1"))


def test_document_processing_input__document_types_defaults_to_empty():
    payload = DocumentProcessingInput(object_key="key", job_id="job-1")

    expect(payload.document_types).to(be_empty)


def test_document_processing_output__combines_sources_and_inline_results():
    extract_fields_response = {
        "status": "success",
        "extractions": [{"document_index": 0, "output": {"nombres": "LAURA"}}],
        "errors": [],
        "metadata": {"total": 1, "succeeded": 1, "failed": 0},
    }
    validate_response = {
        "status": "success",
        "validations": [{"document_index": 0, "validation_results": []}],
        "errors": [],
        "metadata": {"total": 1, "succeeded": 1, "failed": 0},
    }

    output = DocumentProcessingOutput(
        job_id="job-1",
        extract_text_source="s3://bucket/jobs/job-1/extract_text.json",
        classify_pages_source="s3://bucket/jobs/job-1/classify_pages.json",
        extract_fields=extract_fields_response,
        validate_extraction=validate_response,
    )

    expect(output.job_id).to(equal("job-1"))
    expect(output.extract_text_source).to(equal("s3://bucket/jobs/job-1/extract_text.json"))
    expect(output.classify_pages_source).to(equal("s3://bucket/jobs/job-1/classify_pages.json"))
    expect(output.extract_fields).to(equal(extract_fields_response))
    expect(output.validate_extraction).to(equal(validate_response))


def test_document_processing_output__defaults_for_empty_responses():
    output = DocumentProcessingOutput(
        job_id="job-1",
        extract_text_source="s3://a",
        classify_pages_source="s3://b",
    )

    expect(output.extract_fields).to(equal({}))
    expect(output.validate_extraction).to(equal({}))
