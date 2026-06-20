"""Unit tests de ``select_phases`` — sub-segmento por punto de entrada (ADR 0002 · §3.3).

Un workflow tiene UN pipeline con TODAS sus fases; cada ``EntryPoint`` corre un
sub-segmento de ese pipeline propio:

- ``ingest``/``None`` → todas las fases (run completo).
- ``reextract``     → solo la cola de extracción (extract_fields → validate → finalize),
  con ``finalize.config["dispatch_webhook"] = False`` forzado — paridad 1:1 con la
  receta histórica ``field_re_extraction_phases()``.
- ``data``          → desde la primera fase ``analyze`` en adelante (vacío si no hay).

``select_phases`` es PURA: tests sin DB, AAA + expects.
"""

from __future__ import annotations

from expects import be_empty, equal, expect

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines.entry_points import EntryPoint, select_phases
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import (
    data_analysis_phases,
    field_re_extraction_phases,
    standard_analysis_phases,
    standard_case_phases,
    standard_extraction_phases,
)


def _specs(raw_phases: list[dict]) -> list[PhaseSpec]:
    return [PhaseSpec.model_validate(p) for p in raw_phases]


def _signature(phase: PhaseSpec) -> tuple[str, PhaseKind, dict]:
    """(id, kind, config) — la identidad que comparamos contra las recetas."""
    return (phase.id, phase.kind, phase.config)


# ─── INGEST / None: todas las fases sin tocar ───────────────────────────────


def test_select_phases__ingest_returns_all_phases_unchanged():
    # Arrange
    phases = _specs(standard_extraction_phases())

    # Act
    result = select_phases(phases, EntryPoint.INGEST)

    # Assert — mismas fases, mismos ids, mismo orden.
    expect([p.id for p in result]).to(equal([p.id for p in phases]))
    expect([_signature(p) for p in result]).to(equal([_signature(p) for p in phases]))


def test_select_phases__ingest_accepts_plain_string():
    # Arrange
    phases = _specs(standard_extraction_phases())

    # Act — el caller puede pasar el StrEnum como string crudo.
    result = select_phases(phases, "ingest")

    # Assert
    expect([_signature(p) for p in result]).to(equal([_signature(p) for p in phases]))


def test_select_phases__none_entry_returns_all_phases():
    # Arrange
    phases = _specs(standard_extraction_phases())

    # Act — entry=None ⇒ run completo (mismo segmento que ingest).
    result = select_phases(phases, None)

    # Assert
    expect([_signature(p) for p in result]).to(equal([_signature(p) for p in phases]))


# ─── REEXTRACT: cola de extracción con webhook forzado a False ──────────────


def test_select_phases__reextract_on_standard_extraction_keeps_only_extraction_tail():
    # Arrange
    phases = _specs(standard_extraction_phases())

    # Act
    result = select_phases(phases, EntryPoint.REEXTRACT)

    # Assert — exactamente extract_fields → validate_extraction → finalize, en orden.
    expect([p.kind for p in result]).to(
        equal([PhaseKind.EXTRACT_FIELDS, PhaseKind.VALIDATE_EXTRACTION, PhaseKind.FINALIZE])
    )

    # El finalize fuerza dispatch_webhook=False (la extracción original ya emitió el webhook).
    finalize = result[-1]
    expect(finalize.kind).to(equal(PhaseKind.FINALIZE))
    expect(finalize.config.get("dispatch_webhook")).to(equal(False))


def test_select_phases__reextract_matches_field_re_extraction_recipe():
    # Arrange — la receta histórica field-re-extraction es el golden de paridad.
    phases = _specs(standard_extraction_phases())
    expected = _specs(field_re_extraction_phases())

    # Act
    result = select_phases(phases, EntryPoint.REEXTRACT)

    # Assert — (id, kind, config) del segmento == el de la receta legacy,
    # incluido finalize.config["dispatch_webhook"] == False.
    expect([_signature(p) for p in result]).to(equal([_signature(p) for p in expected]))


def test_select_phases__reextract_does_not_mutate_source_finalize():
    # Arrange — model_copy ⇒ el config original (vacío) no debe quedar tocado.
    phases = _specs(standard_extraction_phases())
    source_finalize = next(p for p in phases if p.kind is PhaseKind.FINALIZE)

    # Act
    select_phases(phases, EntryPoint.REEXTRACT)

    # Assert — el finalize de la lista original sigue sin dispatch_webhook.
    expect("dispatch_webhook" in source_finalize.config).to(equal(False))


def test_select_phases__reextract_on_standard_analysis_drops_case_tail():
    # Arrange — standard_analysis tiene analyze/output/deliver tras finalize.
    phases = _specs(standard_analysis_phases())

    # Act
    result = select_phases(phases, EntryPoint.REEXTRACT)

    # Assert — solo la cola de extracción; nada de analyze/output/deliver.
    expect([p.kind for p in result]).to(
        equal([PhaseKind.EXTRACT_FIELDS, PhaseKind.VALIDATE_EXTRACTION, PhaseKind.FINALIZE])
    )
    expect(result[-1].config.get("dispatch_webhook")).to(equal(False))


# ─── DATA: desde la primera fase analyze en adelante ────────────────────────


def test_select_phases__data_on_standard_analysis_returns_analyze_to_end():
    # Arrange
    phases = _specs(standard_analysis_phases())

    # Act
    result = select_phases(phases, EntryPoint.DATA)

    # Assert — analyze → output → deliver (la cola completa).
    expect([p.kind for p in result]).to(
        equal([PhaseKind.ANALYZE, PhaseKind.OUTPUT, PhaseKind.DELIVER])
    )
    # Es la cola "data-only" canónica.
    expect([_signature(p) for p in result]).to(
        equal([_signature(p) for p in _specs(data_analysis_phases())])
    )


def test_select_phases__data_on_standard_case_starts_at_first_analyze():
    # Arrange — standard_case tiene gates case-scope ANTES de analyze.
    phases = _specs(standard_case_phases())

    # Act
    result = select_phases(phases, EntryPoint.DATA)

    # Assert — desde analyze: analyze → approval → output → deliver.
    expect([p.kind for p in result]).to(
        equal(
            [
                PhaseKind.ANALYZE,
                PhaseKind.HUMAN_REVIEW,  # approval
                PhaseKind.OUTPUT,
                PhaseKind.DELIVER,
            ]
        )
    )
    expect([p.id for p in result]).to(equal(["analyze", "approval", "output", "deliver"]))

    # Assert — NO incluye los gates pre-analyze del expediente.
    result_ids = {p.id for p in result}
    for gate_id in ("extraction_gate", "await_clarification", "await_documents"):
        expect(gate_id in result_ids).to(equal(False))


def test_select_phases__data_on_standard_extraction_is_empty():
    # Arrange — extracción pura no tiene fase analyze.
    phases = _specs(standard_extraction_phases())

    # Act
    result = select_phases(phases, EntryPoint.DATA)

    # Assert — sin analyze ⇒ lista vacía (el caller responde 409).
    expect(result).to(be_empty)
