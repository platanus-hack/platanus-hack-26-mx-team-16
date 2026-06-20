"""E7 · F0: derive_capabilities — capacidades como función pura del pipeline.

Generaliza el patrón vivo en m2m (`select_phases(…, DATA)` vacío ⇒ no acepta
datos): cada capacidad se deriva de las fases + policies de la versión vigente,
sin flags ni columnas nuevas.
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_empty, contain, equal, expect

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.services.capabilities import Capability, derive_capabilities

_STANDARD_EXTRACTION = [
    (PhaseKind.INGEST, {}),
    (PhaseKind.EXTRACT_TEXT, {}),
    (PhaseKind.CLASSIFY_PAGES, {}),
    (PhaseKind.EXTRACT_FIELDS, {}),
    (PhaseKind.VALIDATE_EXTRACTION, {}),
    (PhaseKind.FINALIZE, {}),
]


def _version(
    phases: list[tuple[PhaseKind, dict]],
    *,
    activation: dict | None = None,
) -> PipelineVersion:
    specs = [
        PhaseSpec(id=f"{kind.value}_{i}", kind=kind, config=dict(config))
        for i, (kind, config) in enumerate(phases)
    ]
    # D-A: la activación va plegada en extraction_gate.config.activation. Si el test
    # pasa una y no hay gate en las fases, lo añadimos para alojarla.
    if activation is not None:
        gate = next((s for s in specs if s.kind is PhaseKind.EXTRACTION_GATE), None)
        if gate is None:
            gate = PhaseSpec(id="extraction_gate", kind=PhaseKind.EXTRACTION_GATE, config={})
            specs.append(gate)
        gate.config = {**gate.config, "activation": activation}
    return PipelineVersion(uuid=uuid4(), pipeline_id=uuid4(), version=1, phases=specs)


def test_derive__none_version_yields_empty():
    expect(derive_capabilities(None)).to(be_empty)


def test_derive__empty_pipeline_has_no_capabilities():
    # Un pipeline sin fases no extrae nada ⇒ ni siquiera EXTRACTION.
    expect(derive_capabilities(_version([]))).to(be_empty)


def test_derive__standard_extraction_is_just_extraction():
    caps = derive_capabilities(_version(_STANDARD_EXTRACTION))

    expect(caps).to(equal({Capability.EXTRACTION}))


def test_derive__analyze_phase_unlocks_analysis():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.ANALYZE, {})]))

    expect(caps).to(contain(Capability.ANALYSIS))


def test_derive__assess_phase_unlocks_layer2_confidence():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.ASSESS, {})]))

    expect(caps).to(contain(Capability.LAYER2_CONFIDENCE))


def test_derive__enrich_phase_unlocks_enrichment():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.ENRICH, {"tool": "x"})]))

    expect(caps).to(contain(Capability.ENRICHMENT))


def test_derive__await_clarification_unlocks_clarification():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.AWAIT_CLARIFICATION, {})]))

    expect(caps).to(contain(Capability.CLARIFICATION))


def test_derive__output_and_deliver_unlock_structured_output():
    caps = derive_capabilities(
        _version([*_STANDARD_EXTRACTION, (PhaseKind.OUTPUT, {}), (PhaseKind.DELIVER, {})])
    )

    expect(caps).to(contain(Capability.STRUCTURED_OUTPUT))


def test_derive__output_without_deliver_does_not_unlock_structured_output():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.OUTPUT, {})]))

    expect(Capability.STRUCTURED_OUTPUT in caps).to(equal(False))


def test_derive__await_documents_unlocks_dossier_even_without_required_types():
    # E7 · F3: la fase await_documents ES el mecanismo del expediente; la
    # completeness (required_types) puede arrancar vacía y tunearse luego.
    with_types = derive_capabilities(
        _version(
            [*_STANDARD_EXTRACTION, (PhaseKind.AWAIT_DOCUMENTS, {"required_types": {"anexo": 1}})],
        )
    )
    without_types = derive_capabilities(
        _version(
            [*_STANDARD_EXTRACTION, (PhaseKind.AWAIT_DOCUMENTS, {})],
        )
    )

    expect(with_types).to(contain(Capability.MULTI_DOC_DOSSIER))
    expect(without_types).to(contain(Capability.MULTI_DOC_DOSSIER))


def test_derive__classify_pages_child_cases_unlocks_fan_out():
    phases = [
        (PhaseKind.INGEST, {}),
        (PhaseKind.EXTRACT_TEXT, {}),
        (PhaseKind.CLASSIFY_PAGES, {"fan_out": "child_cases", "fan_out_types": ["factura"]}),
        (PhaseKind.EXTRACT_FIELDS, {}),
    ]
    caps = derive_capabilities(_version(phases))

    expect(caps).to(contain(Capability.FAN_OUT))


def test_derive__classify_pages_without_fan_out_does_not_unlock_fan_out():
    caps = derive_capabilities(_version(_STANDARD_EXTRACTION))

    expect(Capability.FAN_OUT in caps).to(equal(False))


def test_derive__human_review_phase_unlocks_human_review():
    caps = derive_capabilities(_version([*_STANDARD_EXTRACTION, (PhaseKind.HUMAN_REVIEW, {})]))

    expect(caps).to(contain(Capability.HUMAN_REVIEW))


def test_derive__activation_stages_unlock_human_review():
    caps = derive_capabilities(
        _version(
            _STANDARD_EXTRACTION,
            activation={"stages": [{"stage": "review_l1", "mode": "mandatory"}]},
        )
    )

    expect(caps).to(contain(Capability.HUMAN_REVIEW))


def test_derive__qa_sample_rate_unlocks_qa():
    caps = derive_capabilities(_version(_STANDARD_EXTRACTION, activation={"qa_sample_rate": 0.25}))

    expect(caps).to(contain(Capability.QA))


def test_derive__qa_gate_without_await_clarification_does_not_leak_clarification():
    # Regresión: el macro QA/HUMAN_REVIEW auto-añade un extraction_gate SOLO para
    # alojar la activación. Su mera presencia NO debe reportar CLARIFICATION — esa
    # capacidad la habilita await_clarification (inversa del macro), no el gate.
    caps = derive_capabilities(_version(_STANDARD_EXTRACTION, activation={"qa_sample_rate": 0.25}))

    expect(caps).to(contain(Capability.QA))
    expect(Capability.CLARIFICATION in caps).to(equal(False))


def test_derive__zero_qa_sample_rate_does_not_unlock_qa():
    caps = derive_capabilities(_version(_STANDARD_EXTRACTION, activation={"qa_sample_rate": 0.0}))

    expect(Capability.QA in caps).to(equal(False))


def test_derive__tolerates_camel_case_policy_keys():
    # Defensa: una versión legacy podría traer las policies en camelCase.
    caps = derive_capabilities(
        _version(
            [*_STANDARD_EXTRACTION, (PhaseKind.AWAIT_DOCUMENTS, {})],
            activation={"qaSampleRate": 0.5},
        )
    )

    expect(caps).to(contain(Capability.QA))
    expect(caps).to(contain(Capability.MULTI_DOC_DOSSIER))


def test_derive__full_case_pipeline_unlocks_the_expected_set():
    phases = [
        (PhaseKind.INGEST, {}),
        (PhaseKind.EXTRACT_TEXT, {}),
        (PhaseKind.CLASSIFY_PAGES, {"fan_out": "child_cases", "fan_out_types": ["factura"]}),
        (PhaseKind.EXTRACT_FIELDS, {}),
        (PhaseKind.ASSESS, {}),
        (PhaseKind.VALIDATE_EXTRACTION, {}),
        (PhaseKind.FINALIZE, {}),
        (PhaseKind.AWAIT_DOCUMENTS, {}),
        (PhaseKind.EXTRACTION_GATE, {}),
        (PhaseKind.AWAIT_CLARIFICATION, {}),
        (PhaseKind.HUMAN_REVIEW, {}),
        (PhaseKind.ENRICH, {"tool": "x"}),
        (PhaseKind.ANALYZE, {}),
        (PhaseKind.OUTPUT, {}),
        (PhaseKind.DELIVER, {}),
    ]
    caps = derive_capabilities(
        _version(
            phases,
            activation={"qa_sample_rate": 0.1, "stages": [{"stage": "review_l1", "mode": "mandatory"}]},
        )
    )

    expect(caps).to(
        equal(
            {
                Capability.EXTRACTION,
                Capability.MULTI_DOC_DOSSIER,
                Capability.ANALYSIS,
                Capability.LAYER2_CONFIDENCE,
                Capability.ENRICHMENT,
                Capability.CLARIFICATION,
                Capability.HUMAN_REVIEW,
                Capability.STRUCTURED_OUTPUT,
                Capability.FAN_OUT,
                Capability.QA,
            }
        )
    )
