"""Catálogo ``phase_kind → Lambda`` (E1 · plan §4.2).

Las fases de cómputo del intérprete se resuelven contra las Lambdas de
procesamiento ``vnext-tools-<step>-<stage>``. La resolución ocurre **en call
time** (no en import time, como hacían las constantes legacy) para que
``settings.STAGE`` se lea durante la ejecución del run.

La Lambda de cada paso se deriva del catálogo por ``phase_kind`` + stage: no hay
override por ``config``, así que cambiar de destino es un cambio de stage/deploy
—no requiere re-sellar la versión.
"""

from __future__ import annotations

from src.common.domain.enums.processing import DocumentExtractorType

# Import a nivel de módulo (no diferido): este módulo entra al sandbox de
# Temporal vía imports_passed_through, así que settings queda cacheado antes
# de que un handler de fase llame a current_stage() durante la ejecución.
from src.common.settings import settings

LAMBDA_PREFIX = "vnext-tools"

DEFAULT_EXTRACTOR: str = DocumentExtractorType.TEXTRACT_LAYOUT.value

# phase kind → nombre del paso Lambda. Hoy coinciden 1:1; el mapa existe para
# que un kind nuevo pueda apuntar a una Lambda existente (o viceversa) sin
# renombrar nada.
LAMBDA_STEP_BY_PHASE_KIND: dict[str, str] = {
    "extract_text": "extract_text",
    "classify_pages": "classify_pages",
    "extract_fields": "extract_fields",
    "validate_extraction": "validate_extraction",
}


def current_stage() -> str:
    return str(settings.STAGE.value) if hasattr(settings.STAGE, "value") else str(settings.STAGE)


def default_function_name(step: str, stage: str | None = None) -> str:
    return f"{LAMBDA_PREFIX}-{step}-{stage or current_stage()}"


def resolve_lambda_function(phase_kind: str) -> str:
    """Nombre de la Lambda de catálogo para una fase: ``vnext-tools-<step>-<stage>``."""
    step = LAMBDA_STEP_BY_PHASE_KIND.get(phase_kind, phase_kind)
    return default_function_name(step)
