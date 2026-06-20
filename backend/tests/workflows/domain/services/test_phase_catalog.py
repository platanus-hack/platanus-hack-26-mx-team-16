"""Catálogo de fases para el editor visual (E6 · diseño §2).

El FE no hardcodea kinds: ``build_phase_catalog`` deriva kind+scope del registry
real y el ``configSchema`` de una tabla declarativa. El enum de ``extractor`` sale
del propio ``DocumentExtractorType`` ⇒ ``asr``/``auto`` (E6) aparecen sin tocar el
catálogo.
"""

from __future__ import annotations

from expects import be_empty, contain, equal, expect, have_keys

from src.common.domain.enums.processing import DocumentExtractorType
from src.workflows.domain.services.phase_catalog import build_phase_catalog


def _catalog(known_kinds=None, scopes=None):
    known_kinds = known_kinds or {"extract_text", "classify_pages", "enrich", "analyze", "ingest"}
    scopes = scopes or {
        "extract_text": "document",
        "classify_pages": "document",
        "ingest": "document",
        "enrich": "case",
        "analyze": "case",
    }
    return build_phase_catalog(known_kinds=known_kinds, phase_scopes=scopes)


def _by_kind(catalog: list[dict], kind: str) -> dict:
    return next(entry for entry in catalog if entry["kind"] == kind)


def test_catalog__every_known_kind_present_sorted():
    catalog = _catalog()

    kinds = [entry["kind"] for entry in catalog]
    expect(kinds).to(equal(sorted(kinds)))
    expect(set(kinds)).to(equal({"analyze", "classify_pages", "enrich", "extract_text", "ingest"}))


def test_catalog__entry_shape_has_scope_config_and_description():
    entry = _by_kind(_catalog(), "extract_text")

    expect(entry).to(have_keys("kind", "scope", "configSchema", "description"))
    expect(entry["scope"]).to(equal("document"))
    expect(entry["description"]).not_to(be_empty)


def test_catalog__case_scope_propagated_from_phase_scopes():
    expect(_by_kind(_catalog(), "enrich")["scope"]).to(equal("case"))


def test_catalog__extractor_enum_includes_asr_and_auto():
    schema = _by_kind(_catalog(), "extract_text")["configSchema"]

    extractor = schema["extractor"]
    expect(extractor["type"]).to(equal("string"))
    # El enum se deriva en vivo de DocumentExtractorType ⇒ asr/auto de E6 están.
    expect(extractor["enum"]).to(contain("asr"))
    expect(extractor["enum"]).to(contain("auto"))
    expect(extractor["enum"]).to(equal([e.value for e in DocumentExtractorType]))


def test_catalog__extractor_default_is_textract_layout():
    schema = _by_kind(_catalog(), "extract_text")["configSchema"]

    expect(schema["extractor"]["default"]).to(equal("textract_layout"))


def test_catalog__classify_pages_exposes_fan_out_fields():
    schema = _by_kind(_catalog(), "classify_pages")["configSchema"]

    expect(schema).to(have_keys("fan_out", "fan_out_types", "fan_out_max_children"))
    expect(schema["fan_out"]["enum"]).to(equal(["child_cases"]))
    expect(schema["fan_out_max_children"]["default"]).to(equal(500))


def test_catalog__enrich_exposes_tool_and_on_failure():
    schema = _by_kind(_catalog(), "enrich")["configSchema"]

    expect(schema).to(have_keys("tool", "on_failure", "args", "persist_degraded"))
    expect(schema["on_failure"]["enum"]).to(equal(["review", "continue", "fail"]))
    expect(schema["on_failure"]["default"]).to(equal("review"))


def test_catalog__configless_kind_has_empty_schema():
    # ``ingest`` es la única fase sin knobs tras F0–F1b (las demás los exponen).
    catalog = _catalog(known_kinds={"ingest"}, scopes={"ingest": "document"})

    expect(_by_kind(catalog, "ingest")["configSchema"]).to(equal({}))


def test_catalog__analyze_exposes_provider_and_timeout_knobs():
    schema = _by_kind(
        build_phase_catalog(known_kinds={"analyze"}, phase_scopes={"analyze": "case"}),
        "analyze",
    )["configSchema"]

    expect(schema).to(have_keys("parser_provider", "rule_set", "active_run_wait_timeout"))
    expect(schema["active_run_wait_timeout"]["default"]).to(equal("PT15M"))


def test_catalog__unknown_kind_defaults_to_document_scope():
    catalog = build_phase_catalog(known_kinds={"mystery"}, phase_scopes={})

    expect(catalog[0]["scope"]).to(equal("document"))
