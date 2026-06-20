"""Capacidades derivadas del pipeline (E7 · F0 · propuesta unified-workflow).

Lo que un workflow «puede hacer» no lo declara un enum (`workflow_type`): lo
**deriva su pipeline** — las fases y las policies de la versión vigente. Esta
función generaliza el patrón que ya debutó en m2m (`select_phases(version.phases,
EntryPoint.DATA)` vacío ⇒ 409 «el pipeline no acepta datos»): cada capacidad es
una función pura de la versión sellada, sin columnas nuevas ni drift flag↔receta.

Es un servicio de dominio puro y testeable: no toca repos ni I/O. La capa de
aplicación resuelve la versión vigente del workflow y se la pasa; el presenter
expone el resultado para que el FE gatee tabs/acciones.
"""

from __future__ import annotations

from enum import StrEnum

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.domain.models.phase_configs import activation_dict_from_version
from src.workflows.domain.models.pipeline import PipelineVersion
from src.workflows.domain.models.policies import policy_keys_to_snake

# Fases document-scope: la base de extracción de todo pipeline. Se hardcodean
# aquí (son valores del enum de dominio) para no importar PHASE_SCOPES, que vive
# en la capa de aplicación (runtime) — un dominio no depende de application.
_DOCUMENT_SCOPE_KINDS: frozenset[PhaseKind] = frozenset(
    {
        PhaseKind.INGEST,
        PhaseKind.EXTRACT_TEXT,
        PhaseKind.CLASSIFY_PAGES,
        PhaseKind.EXTRACT_FIELDS,
        PhaseKind.ASSESS,
        PhaseKind.VALIDATE_EXTRACTION,
        PhaseKind.FINALIZE,
    }
)

# Valor de ``classify_pages.config['fan_out']`` que abre fan-out a child cases.
_FAN_OUT_CHILD_CASES = "child_cases"


class Capability(StrEnum):
    """Capacidades de un workflow, derivadas de su pipeline vigente.

    El valor (snake_case) es el contrato con el FE: viaja en el array
    ``capabilities`` del workflow y el FE gatea tabs/acciones contra él.
    """

    EXTRACTION = "extraction"  # fases document-scope (base)
    MULTI_DOC_DOSSIER = "multi_doc_dossier"  # await_documents + completeness
    ANALYSIS = "analysis"  # fase analyze (reglas)
    LAYER2_CONFIDENCE = "layer2_confidence"  # fase assess (confianza capa-2)
    ENRICHMENT = "enrichment"  # fase enrich (tools firmadas, docs TOOL)
    CLARIFICATION = "clarification"  # fase await_clarification
    HUMAN_REVIEW = "human_review"  # human_review / ActivationPolicy.stages
    STRUCTURED_OUTPUT = "structured_output"  # fases output + deliver
    FAN_OUT = "fan_out"  # classify_pages.fan_out == child_cases
    QA = "qa"  # ActivationPolicy.qa_sample_rate > 0


def derive_capabilities(version: PipelineVersion | None) -> set[Capability]:
    """Las capacidades que una versión sellada de pipeline habilita.

    Sin versión utilizable (workflow sin pipeline o sin ``current_version``)
    devuelve el conjunto vacío: el FE no muestra ninguna tab derivada.
    """
    if version is None:
        return set()

    kinds = {phase.kind for phase in version.phases}
    capabilities: set[Capability] = set()

    if kinds & _DOCUMENT_SCOPE_KINDS:
        capabilities.add(Capability.EXTRACTION)
    if PhaseKind.ANALYZE in kinds:
        capabilities.add(Capability.ANALYSIS)
    if PhaseKind.ASSESS in kinds:
        capabilities.add(Capability.LAYER2_CONFIDENCE)
    if PhaseKind.ENRICH in kinds:
        capabilities.add(Capability.ENRICHMENT)
    # CLARIFICATION es la inversa de su macro (que añade await_clarification): la
    # habilita esa fase standalone, NO la mera presencia de extraction_gate — el gate
    # se auto-añade para QA/human_review (solo aloja la activación) y su rama clarify
    # es config interna, no una capacidad agregable por separado.
    if PhaseKind.AWAIT_CLARIFICATION in kinds:
        capabilities.add(Capability.CLARIFICATION)
    if PhaseKind.OUTPUT in kinds and PhaseKind.DELIVER in kinds:
        capabilities.add(Capability.STRUCTURED_OUTPUT)
    # Expediente multi-doc: la fase await_documents ES el mecanismo (espera
    # completitud). La completeness policy (required_types) es su afinación — puede
    # arrancar vacía (sin tipos requeridos) y el cliente la tunea (E7 · F3 wizard).
    if PhaseKind.AWAIT_DOCUMENTS in kinds:
        capabilities.add(Capability.MULTI_DOC_DOSSIER)
    if _has_child_case_fan_out(version):
        capabilities.add(Capability.FAN_OUT)

    # Revisión humana: la fase human_review en la receta, o stages multinivel
    # en la activation policy (E5). Cualquiera de las dos abre las colas L1/L2.
    activation = _activation_dict(version)
    if PhaseKind.HUMAN_REVIEW in kinds or activation.get("stages"):
        capabilities.add(Capability.HUMAN_REVIEW)
    if _as_float(activation.get("qa_sample_rate")) > 0:
        capabilities.add(Capability.QA)

    return capabilities


def _activation_dict(version: PipelineVersion) -> dict:
    """La activation policy normalizada a snake_case (dict crudo, sin pydantic).

    Las policies se sellan ya en snake_case, pero normalizamos por defensa (una
    versión legacy podría traer camelCase) y para no arriesgar un ``ValidationError``
    en un *read path* — derivar capacidades nunca debe lanzar 500.
    """
    raw = activation_dict_from_version(version) or {}
    normalized = policy_keys_to_snake(raw)
    return normalized if isinstance(normalized, dict) else {}


def _has_child_case_fan_out(version: PipelineVersion) -> bool:
    for phase in version.phases:
        if phase.kind is PhaseKind.CLASSIFY_PAGES and phase.config.get("fan_out") == _FAN_OUT_CHILD_CASES:
            return True
    return False


def _as_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
