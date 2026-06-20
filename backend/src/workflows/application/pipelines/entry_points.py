"""Selección del sub-segmento de fases por punto de entrada (ADR 0002 · §3.3).

Un workflow tiene UN pipeline con TODAS sus fases; cada punto de entrada corre un
sub-segmento de ese pipeline propio en vez de resolver una receta distinta:

- ``ingest``    → todas las fases (upload / ingesta normal; run completo).
- ``reextract`` → solo la cola de extracción (``extract_fields`` →
  ``validate_extraction`` → ``finalize``): sin re-OCR ni re-clasificación y SIN
  webhook de ``finalize`` — paridad 1:1 con la receta ``field-re-extraction``
  histórica (que la extracción original ya emitió el webhook).
- ``data``      → desde la primera fase ``analyze`` en adelante (datos virtuales
  por ``POST /v1/cases/{id}/data``; incluye los gates post-analyze del pipeline
  propio). Sin ``analyze`` ⇒ lista vacía ⇒ el caller responde 409.

``select_phases`` es PURA y determinista: la importan tanto el intérprete (dentro
del sandbox de Temporal) como el dispatch en la capa de aplicación (para validar
el 409 del entry ``data`` antes de arrancar el run).
"""

from __future__ import annotations

from enum import StrEnum

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.domain.models.pipeline import PhaseSpec


class EntryPoint(StrEnum):
    INGEST = "ingest"
    REEXTRACT = "reextract"
    DATA = "data"


# La cola de extracción que re-corre «Extraer Campos»: espejo exacto de
# ``field_re_extraction_phases()`` (sin OCR/clasify ni assess).
_REEXTRACT_KINDS = frozenset(
    {PhaseKind.EXTRACT_FIELDS, PhaseKind.VALIDATE_EXTRACTION, PhaseKind.FINALIZE}
)


def select_phases(phases: list[PhaseSpec], entry: EntryPoint | str | None) -> list[PhaseSpec]:
    """Sub-segmento de ``phases`` para el punto de entrada ``entry``."""
    if entry is None:
        return list(phases)
    entry = EntryPoint(entry)
    if entry is EntryPoint.INGEST:
        return list(phases)
    if entry is EntryPoint.REEXTRACT:
        return _reextract_segment(phases)
    return _data_segment(phases)


def _reextract_segment(phases: list[PhaseSpec]) -> list[PhaseSpec]:
    segment: list[PhaseSpec] = []
    for phase in phases:
        if phase.kind not in _REEXTRACT_KINDS:
            continue
        if phase.kind is PhaseKind.FINALIZE and phase.config.get("dispatch_webhook", True):
            # La extracción original ya emitió el webhook (paridad field-re-extraction).
            phase = phase.model_copy(update={"config": {**phase.config, "dispatch_webhook": False}})
        segment.append(phase)
    return segment


def _data_segment(phases: list[PhaseSpec]) -> list[PhaseSpec]:
    for idx, phase in enumerate(phases):
        if phase.kind is PhaseKind.ANALYZE:
            return list(phases[idx:])
    return []
