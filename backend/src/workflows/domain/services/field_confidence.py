"""Per-field confidence + clarification gate (F4 · M2 · A6).

A6 computes confidence in layers: (1) **legibility** from OCR bbox confidences —
shipped here; (2) **semantic** self-eval/consensus and (3) **cross-check vs a
reference** — future layers that set ``source`` accordingly. The value is
persisted on ``WorkflowDocument.field_confidence`` (computed once, not recomputed
in the webhook payload) and consumed by the ``extraction_gate`` phase (vía la
activity ``evaluate_activation_gate``), which only *labels* low-confidence fields
— it never fails the run.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

# Wired default from product/specs/extraction/extra-fields.md. El override por campo vive
# en ``ActivationPolicy.field_thresholds`` (policy version-level), no en la config de fase.
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


class ConfidenceSource(StrEnum):
    BBOX = "bbox"  # layer 1 — OCR legibility (active)
    LLM = "llm"  # layer 2 — semantic self-eval / consensus (future)
    REFERENCE = "reference"  # layer 3 — cross-check vs reference (future)
    NONE = "none"  # no signal available


def leaf_value(leaf: Any) -> Any:
    if isinstance(leaf, dict) and "value" in leaf:
        return leaf.get("value")
    return leaf


def leaf_confidence(leaf: Any) -> float | None:
    """Scalar confidence per field (§4.4): min of non-null bbox confidences.

    ``None`` when there is no bbox, all are null, or the leaf was inferred.
    """
    if not isinstance(leaf, dict) or leaf.get("inferred"):
        return None
    bbox = leaf.get("bbox") or []
    confidences = [
        hit.get("confidence") for hit in bbox if isinstance(hit, dict) and hit.get("confidence") is not None
    ]
    return min(confidences) if confidences else None


def compute_field_confidence(
    mapped_extraction: dict | None,
    extraction: dict | None = None,
) -> dict[str, dict]:
    """``{field: {value, confidence, source}}`` for every extracted field.

    Layer 1 (bbox) today; ``source`` is ``bbox`` when a confidence was derived,
    else ``none``. Returns ``{}`` when nothing was extracted.
    """
    if mapped_extraction:
        out: dict[str, dict] = {}
        for field, leaf in mapped_extraction.items():
            conf = leaf_confidence(leaf)
            out[field] = {
                "value": leaf_value(leaf),
                "confidence": conf,
                "source": ConfidenceSource.BBOX.value if conf is not None else ConfidenceSource.NONE.value,
            }
        return out
    if extraction:
        return {
            field: {"value": value, "confidence": None, "source": ConfidenceSource.NONE.value}
            for field, value in extraction.items()
        }
    return {}


def fields_needing_clarification(
    field_confidence: dict[str, dict] | None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[str]:
    """Field paths whose (known) confidence is below ``threshold``.

    Fields with ``confidence is None`` are *not* flagged — absence of a legibility
    signal is not the same as low legibility (a higher A6 layer may still score it).
    """
    if not field_confidence:
        return []
    flagged = []
    for field, entry in field_confidence.items():
        conf = entry.get("confidence") if isinstance(entry, dict) else None
        if conf is not None and conf < threshold:
            flagged.append(field)
    return flagged
