"""Unit tests de la validación estructural de recetas (E1 · plan §4.2).

Ids duplicados, kinds sin handler y orden document/case son errores de
configuración que deben detectarse al sembrar/publicar la versión — nunca
ejecutarse en silencio (supuesto rígido #7).
"""

from __future__ import annotations

import pytest

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.services.pipeline_validation import (
    InvalidPipelinePhasesError,
    validate_phases,
)

_KNOWN_KINDS = {
    PhaseKind.INGEST.value,
    PhaseKind.EXTRACT_TEXT.value,
    PhaseKind.EXTRACT_FIELDS.value,
    PhaseKind.ENRICH.value,
    PhaseKind.FINALIZE.value,
}


# ─── validate_phases ─────────────────────────────────────────────────────────


def _phase(phase_id: str, kind: PhaseKind = PhaseKind.ENRICH) -> PhaseSpec:
    return PhaseSpec(id=phase_id, kind=kind)


def test_validate__well_formed_phases_pass():
    phases = [
        _phase("ingest", PhaseKind.INGEST),
        _phase("extract_fields", PhaseKind.EXTRACT_FIELDS),
        _phase("enrich", PhaseKind.ENRICH),
        _phase("finalize", PhaseKind.FINALIZE),
    ]

    validate_phases(phases, known_kinds=_KNOWN_KINDS)  # no raise


def test_validate__duplicate_phase_id_raises():
    phases = [_phase("dup", PhaseKind.INGEST), _phase("dup", PhaseKind.FINALIZE)]

    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases(phases, known_kinds=_KNOWN_KINDS)


def test_validate__empty_phase_id_raises():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases([_phase("")], known_kinds=_KNOWN_KINDS)


def test_validate__kind_without_handler_raises_when_known_kinds_given():
    # ANALYZE es un kind real (E2) pero NO está en el known_kinds de esta
    # validación: simula una receta que referencia un handler no registrado.
    phases = [_phase("analyze", PhaseKind.ANALYZE)]

    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases(phases, known_kinds=_KNOWN_KINDS)


def test_validate__kind_check_skipped_without_known_kinds():
    # El dominio no puede importar el runtime: sin known_kinds no se valida kind.
    validate_phases([_phase("analyze", PhaseKind.ANALYZE)])  # no raise
