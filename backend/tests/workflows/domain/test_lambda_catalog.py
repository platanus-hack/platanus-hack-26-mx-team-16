"""Unit tests del catálogo ``phase_kind → Lambda`` (E1 · plan §4.2).

La resolución es en call time contra el catálogo ``vnext-tools-<step>-<stage>``.
"""

from __future__ import annotations

from expects import equal, expect

from src.common.domain.enums.processing import DocumentExtractorType
from src.workflows.domain.lambda_catalog import (
    DEFAULT_EXTRACTOR,
    LAMBDA_PREFIX,
    LAMBDA_STEP_BY_PHASE_KIND,
    current_stage,
    default_function_name,
    resolve_lambda_function,
)


def test_default_function_name__embeds_prefix_step_and_stage():
    expect(default_function_name("extract_text", "prod")).to(equal("vnext-tools-extract_text-prod"))


def test_default_function_name__uses_current_stage_when_omitted():
    expect(default_function_name("classify_pages")).to(
        equal(f"{LAMBDA_PREFIX}-classify_pages-{current_stage()}")
    )


def test_resolve__returns_catalog_default():
    name = resolve_lambda_function("extract_fields")

    expect(name).to(equal(f"{LAMBDA_PREFIX}-extract_fields-{current_stage()}"))


def test_resolve__unmapped_kind_falls_back_to_kind_as_step():
    # Un kind nuevo sin entrada en el mapa apunta a la Lambda homónima.
    name = resolve_lambda_function("brand_new_kind")

    expect(name).to(equal(f"{LAMBDA_PREFIX}-brand_new_kind-{current_stage()}"))


def test_catalog__maps_the_four_compute_kinds_one_to_one():
    expect(LAMBDA_STEP_BY_PHASE_KIND).to(
        equal(
            {
                "extract_text": "extract_text",
                "classify_pages": "classify_pages",
                "extract_fields": "extract_fields",
                "validate_extraction": "validate_extraction",
            }
        )
    )


def test_default_extractor__is_textract_layout():
    expect(DEFAULT_EXTRACTOR).to(equal(DocumentExtractorType.TEXTRACT_LAYOUT.value))
