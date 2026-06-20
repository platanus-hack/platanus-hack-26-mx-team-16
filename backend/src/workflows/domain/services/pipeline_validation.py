"""Validación estructural de recetas de pipeline (E1 · plan §4.2, runtime).

Detecta errores de configuración al publicar/sembrar una versión — ids
duplicados, kinds sin handler, ``fan_out`` mal ubicado, orden document/case —
nunca en silencio durante el run. Puro (sin imports de framework) para usarse
desde el seed, el endpoint de publish y el runtime del intérprete por igual.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping


class InvalidPipelinePhasesError(ValueError):
    """La lista de fases de la versión es inválida (ids duplicados, kind sin handler…)."""


# E5 · fan-out (diseño §2.1): solo classify_pages puede partir el caso.
FAN_OUT_PHASE_KIND = "classify_pages"
FAN_OUT_MODES = frozenset({"child_cases"})
DEFAULT_FAN_OUT_MAX_CHILDREN = 500


def _validate_fan_out_config(phase, kind: str) -> None:
    """``fan_out``/``fan_out_max_children`` — error de configuración al publicar."""
    config = getattr(phase, "config", None) or {}
    fan_out = config.get("fan_out")
    max_children = config.get("fan_out_max_children")
    fan_out_types = config.get("fan_out_types")
    if fan_out is None and max_children is None and fan_out_types is None:
        return
    if kind != FAN_OUT_PHASE_KIND:
        raise InvalidPipelinePhasesError(
            f"Fase {phase.id!r}: 'fan_out'/'fan_out_max_children'/'fan_out_types' solo son "
            f"válidos en {FAN_OUT_PHASE_KIND!r} (kind actual: {kind!r})"
        )
    if fan_out_types is not None and (
        fan_out is None
        or not isinstance(fan_out_types, list)
        or not fan_out_types
        or not all(isinstance(t, str) and t for t in fan_out_types)
    ):
        raise InvalidPipelinePhasesError(
            f"Fase {phase.id!r}: fan_out_types debe ser una lista no vacía de strings "
            f"y requiere fan_out (recibido: {fan_out_types!r})"
        )
    if fan_out is not None and fan_out not in FAN_OUT_MODES:
        raise InvalidPipelinePhasesError(
            f"Fase {phase.id!r}: fan_out inválido: {fan_out!r} (soportado: 'child_cases')"
        )
    if max_children is not None and (
        isinstance(max_children, bool) or not isinstance(max_children, int) or max_children <= 0
    ):
        raise InvalidPipelinePhasesError(
            f"Fase {phase.id!r}: fan_out_max_children debe ser un entero > 0 "
            f"(recibido: {max_children!r})"
        )


def validate_phases(
    phases: list,
    known_kinds: Collection[str] | None = None,
    phase_scopes: Mapping[str, str] | None = None,
) -> None:
    """Valida una lista de :class:`PhaseSpec` antes de sellarla en una versión.

    ``known_kinds`` (los kinds registrados en ``PHASE_LIBRARY``) es opcional
    porque el dominio no puede importar el runtime; el llamador que lo conozca
    debe pasarlo. ``phase_scopes`` (el ``PHASE_SCOPES`` del runtime, E4) activa
    la regla estructural: todas las fases document-scope deben preceder a la
    primera case-scope, y si hay ``await_documents`` debe ser la PRIMERA fase
    case-scope.
    """
    seen_ids: set[str] = set()
    case_scope_kinds: list[str] = []
    for phase in phases:
        if not phase.id:
            raise InvalidPipelinePhasesError("Fase sin id")
        if phase.id in seen_ids:
            raise InvalidPipelinePhasesError(f"Id de fase duplicado: {phase.id!r}")
        seen_ids.add(phase.id)
        kind = phase.kind.value if hasattr(phase.kind, "value") else str(phase.kind)
        if known_kinds is not None and kind not in known_kinds:
            raise InvalidPipelinePhasesError(f"Fase {phase.id!r}: kind sin handler registrado: {kind!r}")
        _validate_fan_out_config(phase, kind)
        if phase_scopes is not None:
            scope = phase_scopes.get(kind, "document")
            if scope == "case":
                case_scope_kinds.append(kind)
            elif case_scope_kinds:
                raise InvalidPipelinePhasesError(
                    f"Fase {phase.id!r} (document-scope) aparece después de una fase "
                    "case-scope — todas las document-scope deben ir primero (E4)"
                )
    if phase_scopes is not None and "await_documents" in case_scope_kinds and case_scope_kinds[0] != "await_documents":
        raise InvalidPipelinePhasesError(
            "await_documents debe ser la PRIMERA fase case-scope de la receta (E4)"
        )
