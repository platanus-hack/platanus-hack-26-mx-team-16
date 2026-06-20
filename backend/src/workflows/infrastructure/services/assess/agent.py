"""AssessAgent — capa-2 de confianza por campo (fase ``assess``, E3).

Clona el patrón ``SynthesizerAgent`` + ``llm_check``: una llamada LLM
constrained-JSON por documento que compara cada campo extraído contra el
texto fuente y emite, por campo:

- ``extract_confidence`` ∈ [0, 1] — confianza semántica (capa-2; la capa-1
  *parse confidence* viene del bbox/OCR y no se toca aquí).
- ``signals`` ⊆ {multiple_possible_answers, answer_may_be_incomplete,
  illegible}.
- ``explanation`` — corta y EN ESPAÑOL (alimenta la pregunta de aclaración
  al cliente, plan §4.5).
- ``candidates`` — máx 3, SOLO cuando hay ``multiple_possible_answers``.

La respuesta del LLM se valida y clampa defensivamente: un payload
malformado ⇒ resultado vacío + warning, nunca una excepción — assess es
label-only y jamás puede tumbar un run (espíritu B1/confidence_gate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.application.logging import get_logger
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    LLMRunner,
    StaticLLMRunner,
    default_llm_runner,
)

logger = get_logger(__name__)

ASSESS_SIGNALS: tuple[str, ...] = (
    "multiple_possible_answers",
    "answer_may_be_incomplete",
    "illegible",
)

MAX_CANDIDATES = 3

# Guard del prompt: el texto OCR de un documento grande puede ser enorme;
# el slice viaja truncado para mantener la llamada dentro de límites sanos.
MAX_DOCUMENT_TEXT_CHARS = 60_000

MAX_EXPLANATION_CHARS = 400

ASSESS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["fields"],
    "properties": {
        "fields": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["extract_confidence"],
                "properties": {
                    "extract_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "signals": {
                        "type": "array",
                        "items": {"enum": list(ASSESS_SIGNALS)},
                    },
                    "explanation": {"type": "string"},
                    "candidates": {"type": "array", "maxItems": MAX_CANDIDATES},
                },
            },
        }
    },
}

_SYSTEM_PROMPT = (
    "Eres un auditor de extracción de datos de documentos. Recibes los campos "
    "extraídos de UN documento y el texto fuente (OCR) del que provienen. Tu "
    "trabajo es puntuar, campo por campo, cuán confiable es el valor extraído "
    "comparándolo con la evidencia del texto.\n\n"
    "Para CADA campo recibido emite:\n"
    "- extract_confidence: número entre 0 y 1 (1 = el valor está claramente "
    "respaldado por el texto; 0 = no hay evidencia o la contradice).\n"
    "- signals: subconjunto de [multiple_possible_answers, "
    "answer_may_be_incomplete, illegible]. Omite la lista o déjala vacía si "
    "no aplica ninguna señal.\n"
    "- explanation: SOLO si hay señales — una frase corta EN ESPAÑOL que un "
    "humano pueda leer para decidir (se usa para preguntar al cliente).\n"
    "- candidates: SOLO si incluyes multiple_possible_answers — los valores "
    "alternativos plausibles encontrados en el texto, máximo 3.\n\n"
    "REGLAS ESTRICTAS:\n"
    "- Evalúa únicamente los campos recibidos; no inventes campos nuevos.\n"
    "- No corrijas ni reescribas los valores extraídos.\n"
    "- Responde exclusivamente con el objeto JSON que pide el schema."
)


@dataclass
class AssessInput:
    """Campos extraídos (compactos, ``{campo: valor}``) + texto fuente."""

    fields: dict[str, Any]
    document_text: str
    document_type_name: str | None = None


@dataclass
class AssessFieldResult:
    extract_confidence: float
    signals: list[str] = field(default_factory=list)
    explanation: str = ""
    candidates: list[Any] = field(default_factory=list)


@dataclass
class AssessOutput:
    """Resultado por campo. ``fields`` vacío ⇒ el documento queda sin assess."""

    fields: dict[str, AssessFieldResult] = field(default_factory=dict)

    @property
    def extract_confidence(self) -> dict[str, float]:
        return {name: r.extract_confidence for name, r in self.fields.items()}

    @property
    def signals(self) -> dict[str, dict[str, Any]]:
        """Solo campos con señales — `{campo: {signals, explanation, candidates}}`."""
        out: dict[str, dict[str, Any]] = {}
        for name, r in self.fields.items():
            if not r.signals:
                continue
            meta: dict[str, Any] = {"signals": r.signals, "explanation": r.explanation}
            if r.candidates:
                meta["candidates"] = r.candidates
            out[name] = meta
        return out

    @property
    def flagged_fields(self) -> list[str]:
        return [name for name, r in self.fields.items() if r.signals]


@dataclass
class AssessAgent:
    """Agente LLM constrained que puntúa campos extraídos contra la evidencia."""

    # Default seguro (tests/offline); producción inyecta el runner Agno
    # vía `build_assess_agent()`.
    llm_runner: LLMRunner = field(default_factory=lambda: StaticLLMRunner(payload={"fields": {}}))
    model: str | None = None
    provider: str | None = None

    async def assess(self, inputs: AssessInput) -> AssessOutput:
        if not inputs.fields:
            return AssessOutput()
        user = _build_user_prompt(inputs)
        try:
            payload = await self.llm_runner.run(
                system=_SYSTEM_PROMPT,
                user=user,
                output_schema=ASSESS_OUTPUT_SCHEMA,
            )
        except Exception as exc:
            logger.warning(f"assess_agent.llm_failed error={exc}")
            return AssessOutput()
        return parse_assessment(payload, expected_fields=list(inputs.fields))


def parse_assessment(payload: Any, *, expected_fields: list[str]) -> AssessOutput:
    """Valida/clampa la respuesta del LLM. Malformada ⇒ resultado vacío + warning.

    - Solo conserva campos pedidos (los alucinados se descartan).
    - ``extract_confidence`` se clampa a [0, 1]; no numérico ⇒ campo fuera.
    - ``signals`` se filtra al subset permitido.
    - ``candidates`` solo sobrevive con ``multiple_possible_answers`` y se
      trunca a ``MAX_CANDIDATES``.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), dict):
        logger.warning("assess_agent.malformed_payload root='fields' missing or not an object")
        return AssessOutput()

    expected = set(expected_fields)
    out: dict[str, AssessFieldResult] = {}
    for name, meta in payload["fields"].items():
        if name not in expected or not isinstance(meta, dict):
            continue
        confidence = _clamp_confidence(meta.get("extract_confidence"))
        if confidence is None:
            logger.warning(f"assess_agent.invalid_confidence field={name!r}")
            continue
        signals = [s for s in meta.get("signals") or [] if s in ASSESS_SIGNALS]
        # dedupe preservando orden
        signals = list(dict.fromkeys(signals))
        explanation = str(meta.get("explanation") or "")[:MAX_EXPLANATION_CHARS] if signals else ""
        candidates: list[Any] = []
        if "multiple_possible_answers" in signals:
            raw = meta.get("candidates")
            if isinstance(raw, list):
                candidates = raw[:MAX_CANDIDATES]
        out[name] = AssessFieldResult(
            extract_confidence=confidence,
            signals=signals,
            explanation=explanation,
            candidates=candidates,
        )
    return AssessOutput(fields=out)


def _clamp_confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(0.0, min(1.0, float(value)))


def _build_user_prompt(inputs: AssessInput) -> str:
    import json  # noqa: PLC0415

    text = inputs.document_text or ""
    if len(text) > MAX_DOCUMENT_TEXT_CHARS:
        text = text[:MAX_DOCUMENT_TEXT_CHARS] + "\n\n[... texto truncado ...]"
    body = {
        "document_type": inputs.document_type_name,
        "extracted_fields": inputs.fields,
        "document_text": text,
    }
    return json.dumps(body, ensure_ascii=False, default=str)


def build_assess_agent(provider: str | None = None) -> AssessAgent:
    """Factory de producción (Agno-backed) — espejo de `build_synthesizer_agent`.

    ``provider`` (phases-config · assess.provider) sobreescribe el provider del
    rol; ``None`` ⇒ env ``ANALYSIS_ASSESS_PROVIDER`` (comportamiento de hoy)."""
    runner = default_llm_runner("assess", override=provider)
    return AssessAgent(
        llm_runner=runner,
        model=getattr(runner, "model_id", None),
        provider=(getattr(runner, "model_id", "") or "").split(":", 1)[0] or None,
    )
