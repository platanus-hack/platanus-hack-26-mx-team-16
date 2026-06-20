"""Macros «agregar capacidad» sobre la receta del pipeline (E7 · F3).

``derive_capabilities`` (F0) lee fases → capacidades; esto es la inversa: dada
una capacidad, inserta las fases + scaffolds de policy que la habilitan, en el
ORDEN CANÓNICO (document-scope antes que case-scope; ``await_documents`` primera
case-scope) para que ``validate_phases`` la acepte. Idempotente y puro: agregar
una capacidad ya presente no cambia nada. El editor de fases (ADR 0002) sigue
siendo la vista avanzada para afinar config/policies después.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.services.capabilities import Capability, derive_capabilities

# Orden canónico para insertar fases nuevas SIN romper el invariante de scope que
# valida ``validate_phases`` (todas las document-scope primero; ``await_documents``
# la primera case-scope). Una fase nueva se inserta antes de la primera existente
# con índice canónico mayor.
_CANONICAL_ORDER: tuple[PhaseKind, ...] = (
    PhaseKind.INGEST,
    PhaseKind.EXTRACT_TEXT,
    PhaseKind.CLASSIFY_PAGES,
    PhaseKind.EXTRACT_FIELDS,
    PhaseKind.ASSESS,
    PhaseKind.VALIDATE_EXTRACTION,
    PhaseKind.FINALIZE,
    PhaseKind.AWAIT_DOCUMENTS,
    PhaseKind.EXTRACTION_GATE,
    PhaseKind.AWAIT_CLARIFICATION,
    PhaseKind.ENRICH,
    PhaseKind.ANALYZE,
    PhaseKind.HUMAN_REVIEW,
    PhaseKind.OUTPUT,
    PhaseKind.DELIVER,
)
_ORDER_INDEX: dict[PhaseKind, int] = {kind: i for i, kind in enumerate(_CANONICAL_ORDER)}


class UnknownCapabilityMacroError(ValueError):
    """No hay macro para esa capacidad (p. ej. EXTRACTION, que es la base)."""


@dataclass(frozen=True)
class _PhaseDef:
    kind: PhaseKind
    config: dict = field(default_factory=dict)
    phase_id: str | None = None  # default = kind.value


@dataclass(frozen=True)
class _Macro:
    phases: tuple[_PhaseDef, ...] = ()
    activation_patch: dict | None = None
    # (kind objetivo, config a fusionar) — p. ej. fan_out sobre classify_pages.
    config_patch: tuple[PhaseKind, dict] | None = None


_MACROS: dict[Capability, _Macro] = {
    Capability.ANALYSIS: _Macro(phases=(_PhaseDef(PhaseKind.ANALYZE),)),
    Capability.STRUCTURED_OUTPUT: _Macro(
        phases=(_PhaseDef(PhaseKind.OUTPUT), _PhaseDef(PhaseKind.DELIVER)),
    ),
    Capability.LAYER2_CONFIDENCE: _Macro(phases=(_PhaseDef(PhaseKind.ASSESS),)),
    Capability.ENRICHMENT: _Macro(phases=(_PhaseDef(PhaseKind.ENRICH),)),
    Capability.CLARIFICATION: _Macro(phases=(_PhaseDef(PhaseKind.AWAIT_CLARIFICATION),)),
    # La completitud va plegada en ``await_documents.config`` (D-A): la fase nace
    # con config vacía (sin doc types requeridos, avance manual) y el editor la afina.
    Capability.MULTI_DOC_DOSSIER: _Macro(phases=(_PhaseDef(PhaseKind.AWAIT_DOCUMENTS),)),
    Capability.HUMAN_REVIEW: _Macro(
        phases=(_PhaseDef(PhaseKind.HUMAN_REVIEW, config={"kind": "approval"}, phase_id="approval"),),
        activation_patch={"stages": [{"stage": "review_l1", "mode": "mandatory"}]},
    ),
    Capability.FAN_OUT: _Macro(config_patch=(PhaseKind.CLASSIFY_PAGES, {"fan_out": "child_cases"})),
    Capability.QA: _Macro(activation_patch={"qa_sample_rate": 0.1}),
}

#: Capacidades que el wizard sabe agregar (EXTRACTION es la base, no se agrega).
ADDABLE_CAPABILITIES: frozenset[Capability] = frozenset(_MACROS)


def addable_capabilities(version: PipelineVersion | None) -> set[Capability]:
    """Las capacidades que el wizard puede agregar y aún NO están presentes."""
    present = derive_capabilities(version)
    return set(ADDABLE_CAPABILITIES) - present


@dataclass(frozen=True)
class MacroResult:
    phases: list[dict]


def apply_capability(phases: list[dict], capability: Capability) -> MacroResult:
    """Inserta las fases + scaffolds de policy de ``capability`` en la receta.

    Idempotente por kind: una fase que ya existe no se duplica. Las fases nuevas
    se insertan en orden canónico (preserva el invariante de scope). La activación
    (D-A · folded) se parchea DENTRO de ``extraction_gate.config.activation``: un
    macro con ``activation_patch`` (QA, HUMAN_REVIEW) garantiza que exista la fase
    ``extraction_gate`` (la inserta si falta) y fusiona el patch en su
    ``config.activation``. Devuelve la receta nueva como dicts.
    """
    macro = _MACROS.get(capability)
    if macro is None:
        raise UnknownCapabilityMacroError(str(capability))

    specs = [PhaseSpec.model_validate(p) for p in phases]
    existing_kinds = {spec.kind for spec in specs}
    existing_ids = {spec.id for spec in specs}

    if macro.config_patch is not None:
        target_kind, patch = macro.config_patch
        for spec in specs:
            if spec.kind is target_kind:
                spec.config = {**spec.config, **patch}

    # D-A · folded: el patch de activación se fusiona en extraction_gate.config.activation;
    # si no hay gate, se auto-añade (garantiza hogar para mode/stages/qa).
    if macro.activation_patch is not None:
        if PhaseKind.EXTRACTION_GATE not in existing_kinds:
            gate_id = _unique_id(PhaseKind.EXTRACTION_GATE.value, existing_ids)
            existing_ids.add(gate_id)
            _insert_by_canon(specs, PhaseSpec(id=gate_id, kind=PhaseKind.EXTRACTION_GATE, config={}))
            existing_kinds.add(PhaseKind.EXTRACTION_GATE)
        for spec in specs:
            if spec.kind is PhaseKind.EXTRACTION_GATE:
                current = (spec.config or {}).get("activation") or {}
                spec.config = {**spec.config, "activation": _merge(current, macro.activation_patch)}

    for pdef in macro.phases:
        if pdef.kind in existing_kinds:
            continue  # idempotente: la fase ya está
        new_id = _unique_id(pdef.phase_id or pdef.kind.value, existing_ids)
        existing_ids.add(new_id)
        _insert_by_canon(specs, PhaseSpec(id=new_id, kind=pdef.kind, config=dict(pdef.config)))
        existing_kinds.add(pdef.kind)

    return MacroResult(phases=[spec.model_dump(mode="json") for spec in specs])


def _insert_by_canon(specs: list[PhaseSpec], new_spec: PhaseSpec) -> None:
    idx = _ORDER_INDEX.get(new_spec.kind, len(_CANONICAL_ORDER))
    position = len(specs)
    for i, spec in enumerate(specs):
        if _ORDER_INDEX.get(spec.kind, len(_CANONICAL_ORDER)) > idx:
            position = i
            break
    specs.insert(position, new_spec)


def _unique_id(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    counter = 2
    while f"{base}_{counter}" in taken:
        counter += 1
    return f"{base}_{counter}"


def _merge(current: dict | None, patch: dict | None) -> dict | None:
    if patch is None:
        return current
    return {**(current or {}), **patch}
