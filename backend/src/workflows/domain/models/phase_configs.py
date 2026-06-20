"""Config tipada por ``kind`` de fase (propuesta phases-config · F0).

Hoy ``PhaseSpec.config`` es un ``dict`` libre que cada handler lee con
``phase.config.get("clave", default)`` disperso. Esto introduce **un modelo
Pydantic por ``kind``** que es la **única fuente de verdad** del schema de
config: de él se generan (a) el ``phase_catalog`` que consume el editor y (b) la
validación ``validate-on-write`` al publicar/importar una versión, y con él
parsean los handlers (``validate-on-read``) en vez de leer claves sueltas.

Contrato de determinismo (ADR 0002): la config se **sella con la versión** como
JSON dentro de ``pipeline_versions.phases``. Estos modelos NO cambian la forma
sellada — ``PhaseSpec.config`` sigue siendo un ``dict`` y el publish persiste el
JSON entrante tal cual (sin re-serializar ⇒ sin materializar defaults), condición
del golden byte-idéntico. Los modelos solo **validan** y **tipan la lectura**.

Los defaults de cada campo == el default *efectivo de hoy* cuando la clave está
ausente (lo que devolvía ``config.get(clave, default)``), de modo que una versión
ya sellada **sin** la clave reproduce su comportamiento al parsearse.

Viven en ``domain/models`` (no en ``application``) junto a ``policies.py`` y
``pipeline.py``: son modelos de dominio puros, sin dependencias de framework ni
de infraestructura — así ``domain/services/phase_catalog.py`` puede derivar el
catálogo de ellos sin violar la regla de dependencias (domain ← application).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode
from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.enums.processing import DocumentExtractorType
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.models.policies import ActivationPolicy
from src.workflows.domain.services.pipeline_validation import DEFAULT_FAN_OUT_MAX_CHILDREN

# ── Duration ISO-8601 (forma de wire estable para el sellado) ─────────────────
# Los timeouts se sellan como string ISO-8601 ("PT90S", "PT5M") — NO como
# timedelta serializado — para que el golden/sellado sea estable y legible. Se
# validan al publicar (formato) y se parsean a timedelta en el handler.
_DURATION_ADAPTER = TypeAdapter(timedelta)


def _validate_iso_duration(value: str) -> str:
    """Acepta solo strings ISO-8601 de duración (p. ej. ``PT90S``); deja el
    string intacto (el sellado guarda la forma de wire, no un timedelta)."""
    _DURATION_ADAPTER.validate_python(value)  # lanza si el formato es inválido
    return value


#: Campo de duración sellado como string ISO-8601, validado al publicar.
Duration = Annotated[str, AfterValidator(_validate_iso_duration)]


def parse_duration(value: str | None, default: timedelta | None = None) -> timedelta | None:
    """``Duration`` (ISO-8601) → ``timedelta``; ``None`` ⇒ el default del handler
    (que puede ser ``None`` para representar «sin tope», p. ej. el child workflow)."""
    if value is None:
        return default
    return _DURATION_ADAPTER.validate_python(value)


class PhaseConfig(BaseModel):
    """Base de la que heredan todos los modelos de config por ``kind``.

    ``extra="forbid"`` ⇒ publish/import rechaza claves desconocidas (422).
    """

    model_config = ConfigDict(extra="forbid")


# ── document scope ───────────────────────────────────────────────────────────


class IngestConfig(PhaseConfig):
    """``ingest`` no lee config."""


class ExtractTextConfig(PhaseConfig):
    # Default == DEFAULT_EXTRACTOR de hoy (textract_layout): una versión sellada
    # sin la clave reproduce su comportamiento. ``BaseEnum`` NO es str-subclass ⇒
    # el handler pasa ``cfg.extractor.value`` (string crudo) al payload de la
    # Lambda para preservar el fingerprint byte-idéntico del golden.
    extractor: DocumentExtractorType = DocumentExtractorType.TEXTRACT_LAYOUT
    timeout_seconds: int | None = None
    # F1 · extractor distinto por document_type (doc_type_slug → extractor). Como
    # extract_text corre ANTES de classify_pages, solo surte efecto cuando el tipo
    # viene dado en el upload (un único document_type); el resto usa ``extractor``.
    per_type_overrides: dict[str, DocumentExtractorType] = Field(default_factory=dict)


class ClassifyPagesConfig(PhaseConfig):
    # F3 · D-C: "default" (lambda base de hoy — byte-idéntico) | "<slug>" del
    # registry de clasificadores tenant-scoped, resuelto en resolve_classifier.
    classifier: str = "default"
    fan_out: Literal["child_cases"] | None = None
    fan_out_types: list[str] | None = None
    fan_out_max_children: int = DEFAULT_FAN_OUT_MAX_CHILDREN


class FieldEmitConfig(BaseModel):
    """Filtro de PROYECCIÓN a eventos (F2). No borra nada del artifact ni cambia
    qué se calcula — solo qué metadatos viajan en el evento de extracción."""

    model_config = ConfigDict(extra="forbid")

    include_ocr_confidence: bool = False  # proyecta field_confidence ya derivada
    include_bounding_boxes: bool = False
    fields: Literal["all"] | list[str] = "all"


class ExtractFieldsConfig(PhaseConfig):
    # F2: subconjunto de tipos a extraer (None ⇒ todos) + proyección a eventos.
    document_types: list[str] | None = None
    emit: FieldEmitConfig = Field(default_factory=FieldEmitConfig)


class AssessConfig(PhaseConfig):
    # provider/min_confidence: declarados+validados; consumo en la activity
    # (default_llm_runner) es trabajo escalonado (semánticas abiertas §6.7).
    provider: str | None = None  # "provider:model"; None ⇒ env ANALYSIS_ASSESS_PROVIDER
    min_confidence: float | None = None
    timeout: Duration | None = "PT90S"  # = _ASSESS_TIMEOUT (90s) — wired
    max_attempts: int = 2  # = _ASSESS_RETRY_POLICY — wired


class ValidateExtractionConfig(PhaseConfig):
    timeout: Duration | None = "PT5M"  # = timedelta(minutes=5) actual — wired
    # rule_severities: declarado+validado; el gating por severidad es semántica
    # abierta (§6.8). [] ⇒ hoy (nada bloquea salvo error de lambda).
    rule_severities: list[str] = Field(default_factory=list)


class FinalizeConfig(PhaseConfig):
    dispatch_webhook: bool = True
    # F2: subconjunto de campos en el webhook `document.extracted`. None ⇒
    # envelope estándar (hoy). Debe ser ⊆ de extract_fields.emit.fields (422).
    webhook_projection: list[str] | None = None


# ── case scope ───────────────────────────────────────────────────────────────


class ExtractionGateConfig(PhaseConfig):
    """Compuerta de extracción consolidada (pre-analyze): evalúa la ActivationPolicy
    sellada y, ante baja confianza, enruta el caso a clarify O review (mutuamente
    excluyente) según ``on_low_confidence`` — la rama vive DENTRO de la fase, sin
    acoplar por ``scratch["gate"]``. Fusiona el config de clarify (gate) + audiencia
    de review. Reemplaza confidence_gate + await_clarification(gate) + review_gate.
    """

    # Rama clarify (== AwaitClarificationConfig, camino gate).
    expires_in_hours: int | None = None
    audience: str | None = None
    resolution_timeout: Duration | None = None
    on_timeout: Literal["escalate", "auto_resolve", "fail"] | None = None
    # Rama review (audiencia de la cola de staff).
    review_audience: str | None = None
    # D-A · folded: política de activación/revisión del caso (umbrales, on_low_confidence,
    # mode/severities/sample/stages/qa). La consumen el gate + approval + QA vía el seed de
    # ``scratch["policies"]["activation"]``. None ⇒ defaults de ActivationPolicy.
    activation: ActivationPolicy | None = None


class EnrichConfig(PhaseConfig):
    # Binding single-tool inline (paridad 1:1 con enrich_phases hoy). La lista
    # multi-tool (``tools: [...]``) es trabajo posterior (rework de enrich).
    tool: str | None = None
    on_failure: Literal["review", "continue", "fail"] = "review"
    output_key: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    output_doc_type_slug: str | None = None
    persist_degraded: bool = False


class AwaitDocumentsConfig(PhaseConfig):
    """Completitud del expediente plegada en la fase (D-A) — única fuente de verdad.

    ``required_types``/``advance`` ausentes ⇒ caso sin doc types requeridos y avance
    manual. No hay completitud version-level (la columna se dropeó). El editor escribe aquí.
    """

    # doc_type_slug → cardinalidad mínima (== CompletenessPolicy.required_types).
    required_types: dict[str, int] | None = None
    # "auto" == CompletenessPolicy.auto_ready True; default operativo = manual.
    advance: Literal["auto", "manual"] | None = None


class AwaitClarificationConfig(PhaseConfig):
    expires_in_hours: int | None = None
    audience: str | None = None
    # Solo la ruta fallback (``_open_and_wait``) consume estos dos.
    assignee_mode: HumanTaskAssigneeMode | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    # Escalamiento por timeout: declarado+validado; el timer/escalamiento es
    # net-new (hoy espera indefinida) — semántica abierta §6.9. None ⇒ hoy.
    resolution_timeout: Duration | None = None
    on_timeout: Literal["escalate", "auto_resolve", "fail"] | None = None


class ApproverSpec(BaseModel):
    """Quién puede aprobar (F4). Vacío ⇒ sin restricción (= hoy)."""

    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(default_factory=list)  # matriz rol×acción (E5)
    users: list[str] = Field(default_factory=list)  # user_ids específicos
    audience: str | None = None  # audience RBAC (= hoy)


class HumanReviewConfig(PhaseConfig):
    kind: Literal["review", "approval"] | None = None
    audience: str | None = None
    # Solo la ruta fallback (``_open_and_wait``) consume estos dos.
    assignee_mode: HumanTaskAssigneeMode | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    # F4 · quórum N-de-M (solo kind="approval"). Default (1, distinct) == el gate
    # single de hoy. ``timeout`` None ⇒ espera indefinida; al expirar auto-rechaza
    # (fail-safe, D-I). Un rechazo descuenta del quórum (D-I).
    approvers: ApproverSpec = Field(default_factory=ApproverSpec)
    approvals_required: int = Field(default=1, ge=1)
    distinct_approvers: bool = True
    timeout: Duration | None = None

    @model_validator(mode="after")
    def _quorum_only_for_approval(self) -> HumanReviewConfig:
        # El quórum aplica al gate de aprobación; con kind="review" debe quedar
        # en su default (las etapas L1/L2 viven en ActivationPolicy.stages).
        if self.kind == "review" and self.approvals_required != 1:
            raise ValueError("approvals_required>1 only applies to kind='approval'")
        return self


class AnalyzeConfig(PhaseConfig):
    # Overrides de provider + rule_set: declarados+validados; su resolución vive
    # en las activities del child (default_llm_runner) ⇒ consumo escalonado
    # (§6.10). None ⇒ env-global de hoy (no-op).
    parser_provider: str | None = None
    reviewer_provider: str | None = None  # rol "evaluator"
    critic_provider: str | None = None  # rol declarado pero inerte hoy
    synthesizer_provider: str | None = None
    rule_set: str | None = None
    child_workflow_timeout: Duration | None = None  # None ⇒ sin tope (hoy) — wired
    active_run_wait_timeout: Duration | None = "PT15M"  # = ACTIVE_RUN_WAIT_TIMEOUT — wired


class OutputConfig(PhaseConfig):
    # synthesizer_provider: declarado+validado; consumo en build_case_output es
    # escalonado (§6.11). output_schema/synthesis_* siguen version-level.
    synthesizer_provider: str | None = None
    synthesis_timeout: Duration | None = "PT5M"  # = timedelta(minutes=5) — wired


class DeliverConfig(PhaseConfig):
    # channels: allowlist de destinos (uuid|name); None ⇒ todos los suscritos.
    channels: list[str] | None = None
    # payload_projection: subconjunto de campos del ``output`` en case.output.ready
    # (espejo de finalize.webhook_projection). None ⇒ envelope estándar completo.
    payload_projection: list[str] | None = None
    qa_sample_rate: float | None = None  # override de ActivationPolicy.qa_sample_rate — wired
    dispatch_timeout: Duration | None = "PT60S"  # = 60s — wired
    qa_audit_timeout: Duration | None = "PT30S"  # = 30s — wired


#: Registro ``kind.value`` → modelo de config. Cubre las 15 fases: las sin knobs
#: hoy mapean a un modelo vacío para que validate-on-write rechace igualmente
#: claves desconocidas en cualquier fase.
PHASE_CONFIG_MODELS: dict[str, type[PhaseConfig]] = {
    PhaseKind.INGEST.value: IngestConfig,
    PhaseKind.EXTRACT_TEXT.value: ExtractTextConfig,
    PhaseKind.CLASSIFY_PAGES.value: ClassifyPagesConfig,
    PhaseKind.EXTRACT_FIELDS.value: ExtractFieldsConfig,
    PhaseKind.ASSESS.value: AssessConfig,
    PhaseKind.VALIDATE_EXTRACTION.value: ValidateExtractionConfig,
    PhaseKind.FINALIZE.value: FinalizeConfig,
    PhaseKind.EXTRACTION_GATE.value: ExtractionGateConfig,
    PhaseKind.ENRICH.value: EnrichConfig,
    PhaseKind.AWAIT_DOCUMENTS.value: AwaitDocumentsConfig,
    PhaseKind.AWAIT_CLARIFICATION.value: AwaitClarificationConfig,
    PhaseKind.HUMAN_REVIEW.value: HumanReviewConfig,
    PhaseKind.ANALYZE.value: AnalyzeConfig,
    PhaseKind.OUTPUT.value: OutputConfig,
    PhaseKind.DELIVER.value: DeliverConfig,
}


def config_model_for(kind: str) -> type[PhaseConfig] | None:
    """El modelo de config de un ``kind`` (``None`` si el kind no está registrado)."""
    return PHASE_CONFIG_MODELS.get(kind)


def parse_phase_config(phase: PhaseSpec) -> PhaseConfig:
    """Parsea ``phase.config`` con su modelo tipado (validate-on-read del handler).

    Un ``kind`` sin modelo registrado devuelve un ``PhaseConfig`` vacío — nunca
    explota: el handler que no necesita config no llama a esto.
    """
    model = PHASE_CONFIG_MODELS.get(phase.kind.value, PhaseConfig)
    return model.model_validate(phase.config or {})


class InvalidPhaseConfigError(ValueError):
    """La ``config`` de una fase no valida contra su modelo tipado (publish 422).

    Subclase de ``ValueError`` ⇒ el importer la captura y reporta como el resto
    de errores de validación de bundle.
    """

    def __init__(self, phase_id: str, kind: str, detail: str) -> None:
        self.phase_id = phase_id
        self.kind = kind
        self.detail = detail
        super().__init__(f"phase '{phase_id}' ({kind}): {detail}")


def validate_phase_configs(phases: list[PhaseSpec]) -> None:
    """Valida cada ``phase.config`` contra su modelo (validate-on-write).

    NO re-serializa ni muta ``phase.config`` — solo valida. Lanza
    :class:`InvalidPhaseConfigError` en la primera fase inválida.
    """
    for phase in phases:
        model = PHASE_CONFIG_MODELS.get(phase.kind.value)
        if model is None:
            continue
        try:
            model.model_validate(phase.config or {})
        except ValidationError as exc:
            raise InvalidPhaseConfigError(phase.id, phase.kind.value, str(exc)) from exc
    _validate_webhook_projection_subset(phases)


def _validate_webhook_projection_subset(phases: list[PhaseSpec]) -> None:
    """F2 · §6.3: ``finalize.webhook_projection`` debe referenciar solo campos
    que ``extract_fields.emit`` proyecta (cuando emit fija una lista explícita).
    Una referencia a un campo no proyectado es error de publish (422), no un
    no-op silencioso."""
    emit_fields: list[str] | None = None
    for phase in phases:
        if phase.kind is PhaseKind.EXTRACT_FIELDS:
            emit = ExtractFieldsConfig.model_validate(phase.config or {}).emit
            if isinstance(emit.fields, list):
                emit_fields = emit.fields
            break
    if emit_fields is None:
        return  # emit.fields == "all" (o sin extract_fields) ⇒ todo proyectable
    for phase in phases:
        if phase.kind is PhaseKind.FINALIZE:
            projection = FinalizeConfig.model_validate(phase.config or {}).webhook_projection
            if projection:
                missing = [f for f in projection if f not in emit_fields]
                if missing:
                    raise InvalidPhaseConfigError(
                        phase.id,
                        phase.kind.value,
                        f"webhook_projection references fields not emitted by extract_fields.emit: {missing}",
                    )


def project_emit_fields(
    mapped_output: dict | None,
    field_confidence: dict | None,
    emit: FieldEmitConfig,
) -> dict | None:
    """Proyección F2 de campos a un evento, gobernada por ``emit``.

    Devuelve ``None`` cuando no hay nada extra que emitir (``fields == "all"`` y
    sin metadatos) ⇒ el payload del evento queda byte-idéntico al de hoy. Si
    ``emit`` pide subset/bbox/confianza, devuelve ``{campo: {value, bbox?,
    confidence?}}`` filtrado. NO muta ``mapped_output`` ni borra nada.
    """
    if emit.fields == "all" and not emit.include_bounding_boxes and not emit.include_ocr_confidence:
        return None
    mapped = mapped_output or {}
    names = list(mapped.keys()) if emit.fields == "all" else [f for f in emit.fields if f in mapped]
    confidence = field_confidence if isinstance(field_confidence, dict) else {}
    projected: dict[str, dict] = {}
    for name in names:
        leaf = mapped.get(name)
        entry: dict[str, Any] = {}
        entry["value"] = leaf["value"] if isinstance(leaf, dict) and "value" in leaf else leaf
        if emit.include_bounding_boxes and isinstance(leaf, dict) and leaf.get("bbox") is not None:
            entry["bbox"] = leaf["bbox"]
        if emit.include_ocr_confidence and confidence.get(name) is not None:
            entry["confidence"] = confidence[name]
        projected[name] = entry
    return projected


def completeness_dict_from_version(version: PipelineVersion) -> dict | None:
    """Completitud efectiva de una versión (D-A): plegada en ``await_documents``.

    Si la fase ``await_documents`` fija ``required_types``/``advance`` en su config,
    devuelve la forma dict ``{required_types, auto_ready}`` que esperan la
    ``CompletenessPolicy`` y el seed de ``state.scratch["policies"]``; sin esos
    campos (o sin fase ``await_documents``) ⇒ ``None``. ``version.phases`` puede venir
    como ``PhaseSpec`` (dominio) o como dicts crudos (``LoadPipelineVersionOutput``).
    """
    for raw in version.phases:
        spec = raw if isinstance(raw, PhaseSpec) else PhaseSpec.model_validate(raw)
        if spec.kind is PhaseKind.AWAIT_DOCUMENTS:
            cfg = AwaitDocumentsConfig.model_validate(spec.config or {})
            if cfg.required_types is not None or cfg.advance is not None:
                return {
                    "required_types": cfg.required_types or {},
                    "auto_ready": cfg.advance == "auto",
                }
            return None
    return None


def activation_dict_from_version(version: PipelineVersion) -> dict | None:
    """Activación efectiva de una versión (D-A): plegada en ``extraction_gate.config.activation``.

    Si la fase ``extraction_gate`` fija ``activation`` en su config, ese dict snake_case es la
    fuente del seed ``state.scratch["policies"]["activation"]`` (lo consumen el gate, approval y
    QA); sin fase ``extraction_gate`` (o sin ``activation``) devuelve ``None`` ⇒ el intérprete
    siembra ``ActivationPolicy()`` por defecto. ``version.phases`` puede venir como ``PhaseSpec``
    (dominio) o como dicts crudos (``LoadPipelineVersionOutput``).
    """
    for raw in version.phases:
        spec = raw if isinstance(raw, PhaseSpec) else PhaseSpec.model_validate(raw)
        if spec.kind is PhaseKind.EXTRACTION_GATE:
            # Dict sellado crudo (read path): los consumidores lo ``model_validate``
            # ellos mismos y ``derive_capabilities`` normaliza camelCase — no revalidamos
            # aquí (la validación estricta ocurre al publicar, vía validate_phase_configs).
            activation = (spec.config or {}).get("activation")
            return activation if isinstance(activation, dict) else None
    return None
