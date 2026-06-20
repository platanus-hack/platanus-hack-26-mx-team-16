"""Policies de PipelineVersion (E4 · D5 · diseño §2 · D-A folded).

Ambas policies viajan PLEGADAS en la config de la fase que las usa (ya NO son
version-level): ``CompletenessPolicy`` gobierna ``await_documents`` (qué doc types
y cuántos hacen al caso «completo») y vive en ``await_documents.config``;
``ActivationPolicy`` gobierna ``extraction_gate`` y ``human_review`` (umbrales por
campo, ruta clarify/review, sampling y modo de aprobación) y vive en
``extraction_gate.config.activation``. Se validan al publicar como parte de
``validate_phase_configs`` (cada una dentro de su ``*Config`` de fase).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

REVIEW_STAGE_ORDER: dict[str, int] = {"review_l1": 1, "review_l2": 2}


class CompletenessPolicy(BaseModel):
    # doc_type_slug -> count >= 1
    required_types: dict[str, int] = Field(default_factory=dict)
    auto_ready: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("required_types")
    @classmethod
    def _counts_at_least_one(cls, value: dict[str, int]) -> dict[str, int]:
        for slug, count in value.items():
            if count < 1:
                raise ValueError(f"required_types[{slug!r}] must be >= 1 (got {count})")
        return value


class ReviewStage(BaseModel):
    """Stage de revisión multinivel (E5 · diseño §3.1)."""

    stage: Literal["review_l1", "review_l2"]
    mode: Literal["mandatory", "by_exception"]

    model_config = ConfigDict(extra="forbid")


class ActivationPolicy(BaseModel):
    # "default" | "<campo>" | "<doctype>.<campo>" → umbral ∈ [0,1]
    field_thresholds: dict[str, float] = Field(default_factory=dict)
    on_low_confidence: Literal["clarify", "review"] = "clarify"
    blocking_rule_severities: list[str] = Field(default_factory=lambda: ["BLOCKER"])
    sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # E6 · §3: auditoría QA POST-aprobación (% de casos AUTO-aprobados que se
    # mandan a una cola staff de QA tras COMPLETED). Distinto de ``sample_rate``
    # (que es PRE-aprobación: decide si un humano ve el caso antes de entregar).
    qa_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    mode: Literal["mandatory", "by_exception"] = "mandatory"
    # E5 · §3.1: revisión multinivel. None/ausente ⇒ comportamiento E4 intacto
    # (un solo gate con ``mode`` top-level). Orden de la lista = secuencia.
    stages: list[ReviewStage] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("stages")
    @classmethod
    def _stages_unique_and_ordered(cls, value: list[ReviewStage] | None) -> list[ReviewStage] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("stages must not be empty when present (omit it for the E4 single gate)")
        seen: set[str] = set()
        last_order = 0
        for review_stage in value:
            if review_stage.stage in seen:
                raise ValueError(f"duplicate review stage {review_stage.stage!r}")
            seen.add(review_stage.stage)
            order = REVIEW_STAGE_ORDER[review_stage.stage]
            if order < last_order:
                raise ValueError("review stages must be ordered review_l1 < review_l2")
            last_order = order
        return value

    @field_validator("field_thresholds")
    @classmethod
    def _thresholds_in_unit_interval(cls, value: dict[str, float]) -> dict[str, float]:
        for key, threshold in value.items():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"field_thresholds[{key!r}] must be within [0, 1] (got {threshold})")
        return value


def _camel_to_snake_key(key: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(key):
        if ch.isupper() and i > 0 and not key[i - 1].isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def policy_keys_to_snake(value: object) -> object:
    """Normaliza claves dict camelCase→snake_case recursivamente.

    El editor de pipelines y el bundle export emiten las policies en camelCase
    (``fieldThresholds``…) porque el presenter las serializa así para el wire,
    pero los modelos de dominio y el motor (pause_phases, activation_gate) las
    leen en snake_case. El middleware camel→snake de requests es no-op, así que
    normalizamos en el borde de validación/almacenamiento.
    """
    if isinstance(value, dict):
        return {_camel_to_snake_key(k): policy_keys_to_snake(v) for k, v in value.items()}
    if isinstance(value, list):
        return [policy_keys_to_snake(v) for v in value]
    return value


# D-A: la ActivationPolicy ya NO es version-level — viaja plegada en
# ``extraction_gate.config.activation`` (validada por ``validate_phase_configs`` al
# publicar, como parte de ``ExtractionGateConfig``). Las antiguas ``validate_policies`` /
# ``normalize_policies`` version-level se eliminaron; ``policy_keys_to_snake`` se conserva
# (lo usa ``derive_capabilities`` para normalizar la activation leída de la fase).
