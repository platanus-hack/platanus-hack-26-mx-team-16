"""Recetas canónicas de pipeline (E1 · plan §7).

``standard@v1`` es el flujo de extracción que el motor legacy ejecutaba
hardcodeado: la receta que todo upload normal corre por el intérprete tras el
cutover D4. Vive en el dominio para que el onboarder, los tests y los fixtures
compartan UNA definición; la migración que la siembra lleva su propia copia
congelada (las migraciones no importan código de la app).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.enums.pipelines import PipelineKind
from src.common.domain.enums.processing import DocumentExtractorType

STANDARD_PIPELINE_SLUG = "standard-extraction"
STANDARD_PIPELINE_NAME = "Extracción estándar"

REEXTRACT_PIPELINE_SLUG = "field-re-extraction"
REEXTRACT_PIPELINE_NAME = "Re-extracción de campos"

ANALYSIS_PIPELINE_SLUG = "standard-analysis"
ANALYSIS_PIPELINE_NAME = "Extracción + análisis"

DATA_ANALYSIS_PIPELINE_SLUG = "data-analysis"
DATA_ANALYSIS_PIPELINE_NAME = "Análisis de datos (sin documento)"

EXTRACT_ASSESS_PIPELINE_SLUG = "extract-assess"
EXTRACT_ASSESS_PIPELINE_NAME = "Extracción + confianza capa-2"

STANDARD_CASE_PIPELINE_SLUG = "standard-case"
STANDARD_CASE_PIPELINE_NAME = "Expediente estándar"

# Activación seed de standard-case@v1 (E4 · diseño §6): el cliente duplica la
# receta y tunea umbrales/sampling (D5). La completitud va plegada en
# ``await_documents.config`` (D-A): el template la deja vacía (sin doc types
# requeridos, avance manual) para que el cliente la afine con SUS doc types.
STANDARD_CASE_ACTIVATION_POLICY: dict = {
    "field_thresholds": {"default": 0.75},
    "on_low_confidence": "clarify",
    "blocking_rule_severities": ["BLOCKER"],
    "sample_rate": 0,
    "mode": "mandatory",
}


def standard_extraction_phases() -> list[dict]:
    """Fases de ``standard@v1`` — paridad 1:1 con el legacy (golden E1)."""
    return [
        {"id": "ingest", "kind": "ingest", "config": {}},
        {
            "id": "extract_text",
            "kind": "extract_text",
            # Pin explícito del extractor: cambiarlo es publicar una versión
            # nueva de la receta, no un deploy (catálogo E1).
            "config": {"extractor": DocumentExtractorType.TEXTRACT_LAYOUT.value},
        },
        {"id": "classify_pages", "kind": "classify_pages", "config": {}},
        {"id": "extract_fields", "kind": "extract_fields", "config": {}},
        {"id": "validate_extraction", "kind": "validate_extraction", "config": {}},
        {"id": "finalize", "kind": "finalize", "config": {}},
    ]


def standard_analysis_phases() -> list[dict]:
    """Receta encadenada E2: extracción completa + analyze→output→deliver.

    Sembrada en el catálogo SIN auto-bind (decisión Vic 2026-06-10): activarla
    para un workflow = apuntar su ``workflows.pipeline_id`` a este pipeline.
    ``analyze`` skipea en uploads sin caso; ``output`` ejecuta el spec
    case-output (x-source + síntesis); ``deliver`` emite ``case.output.ready``.
    """
    return [
        *standard_extraction_phases(),
        {"id": "analyze", "kind": "analyze", "config": {}},
        {"id": "output", "kind": "output", "config": {}},
        {"id": "deliver", "kind": "deliver", "config": {}},
    ]


def data_analysis_phases() -> list[dict]:
    """Receta data-only (E3 · Caso 1B): el caso arranca al recibir
    ``POST /v1/cases/{id}/data`` — sin archivo, sin fases document-scope.
    En E3 corre sin document set (sin SSE); la observabilidad es
    ``GET /v1/cases/{id}`` + webhooks ``case.*``."""
    return [
        {"id": "analyze", "kind": "analyze", "config": {}},
        {"id": "output", "kind": "output", "config": {}},
        {"id": "deliver", "kind": "deliver", "config": {}},
    ]


def extract_assess_phases() -> list[dict]:
    """Extracción + capa-2 de confianza (E3 · Caso 1A): ``assess`` puntúa cada
    campo contra la evidencia (extract_confidence + signals + candidates)
    entre extract_fields y validate (plan §4.2)."""
    return [
        {"id": "ingest", "kind": "ingest", "config": {}},
        {
            "id": "extract_text",
            "kind": "extract_text",
            "config": {"extractor": DocumentExtractorType.TEXTRACT_LAYOUT.value},
        },
        {"id": "classify_pages", "kind": "classify_pages", "config": {}},
        {"id": "extract_fields", "kind": "extract_fields", "config": {}},
        {"id": "assess", "kind": "assess", "config": {}},
        {"id": "validate_extraction", "kind": "validate_extraction", "config": {}},
        {"id": "finalize", "kind": "finalize", "config": {}},
    ]


def standard_case_phases() -> list[dict]:
    """Receta canónica del expediente formal (E4 · diseño §6, decisión Vic:
    CON assess). Fases document-scope primero (corren por upload/llegada con
    ``scope="document"``); luego las case-scope (el run ``CASE#`` con
    ``scope="case"``): ``await_documents`` espera completitud,
    ``extraction_gate`` evalúa la ActivationPolicy y, ante baja confianza, enruta
    el caso (clarify | review) según ``on_low_confidence``, y ``approval`` pausa
    tras ``analyze`` según el modo de la policy (mandatory | by_exception)."""
    return [
        # document-scope
        {"id": "ingest", "kind": "ingest", "config": {}},
        {
            "id": "extract_text",
            "kind": "extract_text",
            "config": {"extractor": DocumentExtractorType.TEXTRACT_LAYOUT.value},
        },
        {"id": "classify_pages", "kind": "classify_pages", "config": {}},
        {"id": "extract_fields", "kind": "extract_fields", "config": {}},
        {"id": "assess", "kind": "assess", "config": {}},
        {"id": "validate_extraction", "kind": "validate_extraction", "config": {}},
        {"id": "finalize", "kind": "finalize", "config": {}},
        # case-scope
        {"id": "await_documents", "kind": "await_documents", "config": {}},
        {"id": "extraction_gate", "kind": "extraction_gate", "config": {"activation": dict(STANDARD_CASE_ACTIVATION_POLICY)}},
        {"id": "analyze", "kind": "analyze", "config": {}},
        {"id": "approval", "kind": "human_review", "config": {"kind": "approval"}},
        {"id": "output", "kind": "output", "config": {}},
        {"id": "deliver", "kind": "deliver", "config": {}},
    ]


@dataclass(frozen=True)
class PipelineTemplate:
    """Plantilla canónica copy-on-create (E7 · F2). ``workflow_type`` murió: el
    alta elige una PLANTILLA por slug y el creator clona sus fases + policies como
    el pipeline propio v1 del workflow (ADR 0002)."""

    slug: str
    kind: PipelineKind
    name: str
    phases: list[dict]
    # Sustantivo visible del caso que el alta siembra en el workflow (es/en ·
    # one/other). None ⇒ el workflow nace sin noun y la UI usa el default
    # «Caso/Casos» (product/specs/data-model/case-noun.md). Las plantillas genéricas se
    # quedan en None; las de dominio (expediente, data-analysis) traen el suyo.
    case_noun: dict | None = None


def _pipeline_templates() -> dict[str, PipelineTemplate]:
    return {
        STANDARD_PIPELINE_SLUG: PipelineTemplate(
            STANDARD_PIPELINE_SLUG, PipelineKind.EXTRACTION, STANDARD_PIPELINE_NAME,
            standard_extraction_phases(),
        ),
        ANALYSIS_PIPELINE_SLUG: PipelineTemplate(
            ANALYSIS_PIPELINE_SLUG, PipelineKind.ANALYSIS, ANALYSIS_PIPELINE_NAME,
            standard_analysis_phases(),
        ),
        EXTRACT_ASSESS_PIPELINE_SLUG: PipelineTemplate(
            EXTRACT_ASSESS_PIPELINE_SLUG, PipelineKind.EXTRACTION, EXTRACT_ASSESS_PIPELINE_NAME,
            extract_assess_phases(),
        ),
        STANDARD_CASE_PIPELINE_SLUG: PipelineTemplate(
            STANDARD_CASE_PIPELINE_SLUG, PipelineKind.ANALYSIS, STANDARD_CASE_PIPELINE_NAME,
            standard_case_phases(),
            case_noun={
                "es": {"one": "Expediente", "other": "Expedientes"},
                "en": {"one": "Dossier", "other": "Dossiers"},
            },
        ),
        DATA_ANALYSIS_PIPELINE_SLUG: PipelineTemplate(
            DATA_ANALYSIS_PIPELINE_SLUG, PipelineKind.ANALYSIS, DATA_ANALYSIS_PIPELINE_NAME,
            data_analysis_phases(),
            case_noun={
                "es": {"one": "Análisis", "other": "Análisis"},
                "en": {"one": "Analysis", "other": "Analyses"},
            },
        ),
    }


def pipeline_template_for_slug(slug: str | None) -> PipelineTemplate:
    """La plantilla copy-on-create elegida en el alta (E7 · F2). Sin slug (o uno
    desconocido) ⇒ extracción estándar — el default seguro del «alta en blanco»."""
    templates = _pipeline_templates()
    return templates.get(slug or STANDARD_PIPELINE_SLUG, templates[STANDARD_PIPELINE_SLUG])


def field_re_extraction_phases() -> list[dict]:
    """Run extract-only sobre artefactos existentes (E1, reemplaza
    ``ProcessingJobFieldReExtractionWorkflow``): el run arranca con
    ``classify_pages`` y ``persisted_docs`` sembrados vía
    ``PipelineRunInput.initial_artifacts`` — sin re-OCR ni re-clasificación,
    y sin webhook de finalize (la extracción original ya lo emitió)."""
    return [
        {"id": "extract_fields", "kind": "extract_fields", "config": {}},
        {"id": "validate_extraction", "kind": "validate_extraction", "config": {}},
        {"id": "finalize", "kind": "finalize", "config": {"dispatch_webhook": False}},
    ]
