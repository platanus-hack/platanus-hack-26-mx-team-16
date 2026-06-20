"""E7 · F3: macros «agregar capacidad» — la inversa de derive_capabilities.

Cada macro inserta las fases + scaffolds de policy de una capacidad en orden
canónico; el resultado DEBE pasar ``validate_phases`` y, al re-derivarse, exponer
la capacidad agregada. Idempotente.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import be_empty, contain, equal, expect

# Importar los módulos de fase puebla PHASE_LIBRARY/PHASE_SCOPES (side-effect).
from src.workflows.application.pipelines import (  # noqa: F401
    analysis_phases,
    assess_phases,
    enrich_phases,
    extraction_phases,
    pause_phases,
)
from src.workflows.application.pipelines.runtime import PHASE_LIBRARY, PHASE_SCOPES
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.recipes import standard_analysis_phases, standard_extraction_phases
from src.workflows.domain.services.capabilities import Capability, derive_capabilities
from src.workflows.domain.services.capability_macros import (
    ADDABLE_CAPABILITIES,
    UnknownCapabilityMacroError,
    addable_capabilities,
    apply_capability,
)
from src.workflows.domain.services.pipeline_validation import validate_phases


def _version(phases) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=uuid4(),
        version=1,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


def _assert_valid(result):
    specs = [PhaseSpec.model_validate(p) for p in result.phases]
    validate_phases(specs, known_kinds=set(PHASE_LIBRARY), phase_scopes=dict(PHASE_SCOPES))


@pytest.mark.parametrize("capability", sorted(ADDABLE_CAPABILITIES, key=lambda c: c.value))
def test_apply_capability__yields_valid_recipe_that_derives_the_capability(capability):
    result = apply_capability(standard_extraction_phases(),capability)

    _assert_valid(result)  # no raise: orden de scope correcto
    expect(capability in derive_capabilities(_version(result.phases))).to(equal(True))


def test_apply_capability__is_idempotent():
    once = apply_capability(standard_extraction_phases(), Capability.ANALYSIS)
    twice = apply_capability(once.phases, Capability.ANALYSIS)

    expect(twice.phases).to(equal(once.phases))


def test_apply_capability__inserts_await_documents_as_first_case_scope():
    # Agregar expediente a una receta que ya tiene clarificación: await_documents
    # debe quedar ANTES (primera case-scope) — la regla de validate_phases.
    with_clarify = apply_capability(
        standard_extraction_phases(), Capability.CLARIFICATION
    )
    with_dossier = apply_capability(
        with_clarify.phases,
        Capability.MULTI_DOC_DOSSIER,
    )

    _assert_valid(with_dossier)  # no raise
    kinds = [p["kind"] for p in with_dossier.phases]
    expect(kinds.index("await_documents")).to(equal(min(
        kinds.index("await_documents"), kinds.index("await_clarification")
    )))


def test_apply_capability__fan_out_patches_classify_pages():
    result = apply_capability(standard_extraction_phases(), Capability.FAN_OUT)

    classify = next(p for p in result.phases if p["kind"] == "classify_pages")
    expect(classify["config"].get("fan_out")).to(equal("child_cases"))


def test_apply_capability__qa_scaffolds_activation_in_gate():
    # QA parchea qa_sample_rate DENTRO de extraction_gate.config.activation, y auto-añade
    # el gate si la receta no lo tiene (standard_extraction no lo trae).
    result = apply_capability(standard_extraction_phases(), Capability.QA)

    gate = next(p for p in result.phases if p["kind"] == "extraction_gate")
    expect(gate["config"]["activation"]["qa_sample_rate"]).to(equal(0.1))


def test_apply_capability__rejects_extraction_base():
    with pytest.raises(UnknownCapabilityMacroError):
        apply_capability(standard_extraction_phases(), Capability.EXTRACTION)


def test_addable__standard_extraction_offers_every_macro():
    expect(addable_capabilities(_version(standard_extraction_phases()))).to(
        equal(set(ADDABLE_CAPABILITIES))
    )


def test_addable__excludes_already_present():
    addable = addable_capabilities(_version(standard_analysis_phases()))

    expect(Capability.ANALYSIS in addable).to(equal(False))
    expect(Capability.STRUCTURED_OUTPUT in addable).to(equal(False))
    # extract-assess no está en analysis ⇒ layer2 sí es agregable.
    expect(addable).to(contain(Capability.LAYER2_CONFIDENCE))


def test_addable__full_case_pipeline_offers_nothing_or_little():
    # standard_case tiene la mayoría; al menos no ofrece analysis ni dossier.
    addable = addable_capabilities(_version(_full_case_phases()))

    expect(Capability.ANALYSIS in addable).to(equal(False))
    expect(Capability.MULTI_DOC_DOSSIER in addable).to(equal(False))
    expect(Capability.HUMAN_REVIEW in addable).to(equal(False))


def _full_case_phases():
    from src.workflows.domain.recipes import standard_case_phases

    return standard_case_phases()


def test_addable__empty_when_everything_present():
    # Una receta que cubre las 9 capacidades agregables ⇒ addable vacío.
    phases = standard_extraction_phases()
    for capability in ADDABLE_CAPABILITIES:
        phases = apply_capability(phases, capability).phases

    _assert_valid(  # la receta acumulada sigue siendo válida
        apply_capability(phases, Capability.ANALYSIS)
    )
    expect(addable_capabilities(_version(phases))).to(be_empty)
