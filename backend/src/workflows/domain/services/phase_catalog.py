"""Catálogo de fases para el editor visual de pipelines (E6 · diseño §2).

El frontend NO debe hardcodear los ``kind``/``scope``/config de las fases: se
desincronizaría con el registry Python en cuanto cambie una fase. Este módulo es
la **única fuente de verdad** del catálogo y deriva:

- ``kind`` + ``scope`` de ``PHASE_LIBRARY``/``PHASE_SCOPES`` (poblados al importar
  los módulos de fase — el mismo side-effect que usa ``_validate_recipe``);
- el ``configSchema`` por kind **introspeccionando los modelos tipados**
  ``PhaseConfig`` (``domain/models/phase_configs.py``) — la MISMA fuente que
  valida el publish/import y que parsean los handlers. Así el formulario del
  editor y la validación del backend nunca divergen (propuesta phases-config
  §4.2). El enum de ``extractor`` sale de ``DocumentExtractorType`` ⇒ ``asr``/
  ``auto`` aparecen sin tocar este módulo.

El endpoint ``GET /v1/pipelines/phase-catalog`` serializa ``build_phase_catalog``
a camelCase para el editor.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from src.workflows.domain.models.phase_configs import PhaseConfig, config_model_for


def _unwrap_optional(annotation: Any) -> Any:
    """``X | None`` → ``X``; deja cualquier otra cosa intacta."""
    if get_origin(annotation) is Union:
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _json_type_and_enum(annotation: Any) -> tuple[str, list[Any] | None]:
    """Tipo JSON + enum (si aplica) de una anotación de campo Pydantic."""
    ann = _unwrap_optional(annotation)
    origin = get_origin(ann)
    if origin is Literal:
        return "string", list(get_args(ann))
    if isinstance(ann, type) and issubclass(ann, Enum):
        return "string", [member.value for member in ann]
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        return "object", None  # sub-objeto anidado (p. ej. emit) → JSON
    if ann is bool:  # antes que int: bool es subclase de int
        return "boolean", None
    if ann is int:
        return "integer", None
    if ann is float:
        return "number", None
    if ann is str:
        return "string", None
    if origin in (list, tuple, set) or ann in (list, tuple, set):
        return "array", None
    if origin is dict or ann is dict:
        return "object", None
    return "string", None


def _field_default(field: FieldInfo) -> Any:
    """Default efectivo del campo, o ``None`` si es requerido / default ``None``."""
    if field.default_factory is not None:
        return field.default_factory()  # type: ignore[call-arg]
    if field.default is PydanticUndefined:
        return None
    return field.default


def _schema_from_model(model: type[PhaseConfig]) -> dict[str, dict[str, Any]]:
    """``configSchema`` ``{campo(alias): {type, enum?, default?}}`` desde el modelo.

    Emite ``default`` solo cuando el campo tiene un default significativo (no
    ``None`` ni requerido) ⇒ espeja la tabla declarativa original byte a byte
    para los campos que el editor ya consumía.
    """
    schema: dict[str, dict[str, Any]] = {}
    for name, field in model.model_fields.items():
        key = field.alias or name
        json_type, enum = _json_type_and_enum(field.annotation)
        entry: dict[str, Any] = {"type": json_type}
        if enum is not None:
            entry["enum"] = enum
        default = _field_default(field)
        if default is not None:
            if isinstance(default, Enum):
                entry["default"] = default.value
            elif isinstance(default, BaseModel):
                entry["default"] = default.model_dump(mode="json")
            else:
                entry["default"] = default
        schema[key] = entry
    return schema


def _phase_config_schema(kind: str) -> dict[str, dict[str, Any]]:
    """``configSchema`` del ``kind`` desde su modelo tipado (``{}`` si no hay)."""
    model = config_model_for(kind)
    return _schema_from_model(model) if model is not None else {}


# Descripción legible por kind para el picker del editor.
_PHASE_DESCRIPTIONS: dict[str, str] = {
    "ingest": "Sella el input del run y deja el checkpoint DISPATCHED.",
    "extract_text": "OCR/transcripción del documento (Lambda extract_text).",
    "classify_pages": "Particiona y clasifica páginas; opcionalmente fan-out a casos hijos.",
    "extract_fields": "Extracción de campos por documento (Lambda extract_fields).",
    "assess": "Capa-2 de confianza: un LLM puntúa los campos contra la evidencia.",
    "validate_extraction": "Validación por documento (Lambda validate_extraction).",
    "finalize": "Persiste textos, marca documentos terminales y emite webhooks.",
    "extraction_gate": "Compuerta de extracción: evalúa confianza y enruta a aclaración o revisión.",
    "enrich": "Invoca una tool externa firmada para enriquecer el caso.",
    "analyze": "Lanza el WorkflowAnalysisRun hijo (reglas) y espera su resultado.",
    "output": "Proyecta la salida x-source y la sintetiza contra el output_schema.",
    "deliver": "Emite los eventos de salida del caso al outbox (destinos).",
    "await_clarification": "Pausa durable esperando datos faltantes de un humano/sistema.",
    "human_review": "Pausa durable para revisión/aprobación humana (multinivel L1/L2).",
    "await_documents": "Pausa durable hasta que el expediente esté completo (CompletenessPolicy).",
}


def build_phase_catalog(*, known_kinds: set[str], phase_scopes: dict[str, str]) -> list[dict[str, Any]]:
    """Construye el catálogo a partir del registry real + los modelos de config.

    ``known_kinds``/``phase_scopes`` los pasa el endpoint tras importar los
    módulos de fase (igual que ``_validate_recipe``). El orden es estable
    (alfabético por kind) para que el wire sea determinista.
    """
    catalog: list[dict[str, Any]] = []
    for kind in sorted(known_kinds):
        catalog.append(
            {
                "kind": kind,
                "scope": phase_scopes.get(kind, "document"),
                "configSchema": _phase_config_schema(kind),
                "description": _PHASE_DESCRIPTIONS.get(kind, ""),
            }
        )
    return catalog
