"""E4 · diseño §3: scopes de fase y filtrado por scope del intérprete."""

from __future__ import annotations

from expects import equal, expect

# Importar los módulos de fase puebla PHASE_LIBRARY/PHASE_SCOPES (side-effect).
from src.workflows.application.pipelines import (  # noqa: F401
    analysis_phases,
    assess_phases,
    enrich_phases,
    extraction_phases,
    pause_phases,
)
from src.workflows.application.pipelines.runtime import (
    PHASE_SCOPES,
    filter_phases_by_scope,
)
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import standard_case_phases

EXPECTED_SCOPES = {
    # document-scope
    "ingest": "document",
    "extract_text": "document",
    "classify_pages": "document",
    "extract_fields": "document",
    "assess": "document",
    "validate_extraction": "document",
    "finalize": "document",
    # case-scope
    "await_documents": "case",
    "extraction_gate": "case",
    "enrich": "case",
    "await_clarification": "case",
    "human_review": "case",
    "analyze": "case",
    "output": "case",
    "deliver": "case",
}


def test_phase_scopes__match_design_table():
    for kind, scope in EXPECTED_SCOPES.items():
        expect((kind, PHASE_SCOPES.get(kind))).to(equal((kind, scope)))


def _standard_case_specs() -> list[PhaseSpec]:
    return [PhaseSpec.model_validate(p) for p in standard_case_phases()]


def test_filter_phases_by_scope__none_is_full_recipe():
    phases = _standard_case_specs()

    filtered = filter_phases_by_scope(phases, None)

    expect([p.id for p in filtered]).to(equal([p.id for p in phases]))


def test_filter_phases_by_scope__document_only():
    filtered = filter_phases_by_scope(_standard_case_specs(), "document")

    expect([p.id for p in filtered]).to(
        equal(
            [
                "ingest",
                "extract_text",
                "classify_pages",
                "extract_fields",
                "assess",
                "validate_extraction",
                "finalize",
            ]
        )
    )


def test_filter_phases_by_scope__case_only():
    filtered = filter_phases_by_scope(_standard_case_specs(), "case")

    expect([p.id for p in filtered]).to(
        equal(
            [
                "await_documents",
                "extraction_gate",
                "analyze",
                "approval",
                "output",
                "deliver",
            ]
        )
    )
