"""Evaluación pura de la ActivationPolicy sobre los docs del caso (E4 · §4).

Confianza **fusionada** por campo: ``extract_confidence[campo]`` (capa-2,
fase assess E3) si existe; si no, ``field_confidence[campo].confidence``
(capa-1 bbox/OCR). Umbral por campo con precedencia
``"<doctype_slug>.<campo>"`` → ``"<campo>"`` → ``"default"``; sin match el
campo NO se evalúa. Cada breach produce un item camelCase listo para el
clarification request (§4.5) / la cola de revisión.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.models.policies import ActivationPolicy

MAX_GATE_ITEMS = 100  # refs compactos — límite 2 MiB de Temporal
MAX_CANDIDATES = 3


def _threshold_for(
    thresholds: dict[str, float], doc_type_slug: str | None, field_path: str
) -> float | None:
    if doc_type_slug:
        key = f"{doc_type_slug}.{field_path}"
        if key in thresholds:
            return thresholds[key]
    if field_path in thresholds:
        return thresholds[field_path]
    return thresholds.get("default")


def _fused_confidences(doc: WorkflowDocument) -> dict[str, dict[str, float | None]]:
    """``{campo: {confidence, parse_confidence, extract_confidence}}``.

    ``confidence`` es la fusionada (capa-2 si existe, si no capa-1). Campos sin
    señal en ninguna capa no aparecen.
    """
    parse_conf: dict[str, float | None] = {}
    for field, entry in (doc.field_confidence or {}).items():
        if isinstance(entry, dict):
            parse_conf[field] = entry.get("confidence")
    extract_conf: dict[str, float | None] = {}
    for field, value in (doc.extract_confidence or {}).items():
        extract_conf[field] = value if isinstance(value, (int, float)) else None

    out: dict[str, dict[str, float | None]] = {}
    for field in set(parse_conf) | set(extract_conf):
        fused = extract_conf.get(field)
        if fused is None:
            fused = parse_conf.get(field)
        if fused is None:
            continue
        out[field] = {
            "confidence": fused,
            "parse_confidence": parse_conf.get(field),
            "extract_confidence": extract_conf.get(field),
        }
    return out


def evaluate_activation_gate(
    documents: list[WorkflowDocument],
    slug_by_type_id: dict[UUID, str],
    policy: ActivationPolicy,
) -> list[dict[str, Any]]:
    """Items de breach (≤ ``MAX_GATE_ITEMS``) ordenados por doc/campo."""
    items: list[dict[str, Any]] = []
    for doc in documents:
        if doc.status != WorkflowDocumentStatus.EXTRACTED:
            continue
        slug = slug_by_type_id.get(doc.document_type_id) if doc.document_type_id else None
        confidences = _fused_confidences(doc)
        for field_path in sorted(confidences):
            entry = confidences[field_path]
            threshold = _threshold_for(policy.field_thresholds, slug, field_path)
            if threshold is None:
                continue  # sin umbral aplicable ⇒ campo no evaluado
            confidence = entry["confidence"]
            if confidence is None or confidence >= threshold:
                continue
            signal_entry = (doc.signals or {}).get(field_path) or {}
            leaf = (doc.mapped_extraction or {}).get(field_path)
            page = leaf.get("page_number") if isinstance(leaf, dict) else None
            bbox_hits = leaf.get("bbox") if isinstance(leaf, dict) else None
            bbox = bbox_hits[0] if isinstance(bbox_hits, list) and bbox_hits else None
            items.append(
                {
                    "documentId": str(doc.uuid),
                    "documentType": slug,
                    "fieldPath": field_path,
                    "confidence": confidence,
                    "threshold": threshold,
                    "parseConfidence": entry["parse_confidence"],
                    "extractConfidence": entry["extract_confidence"],
                    "signals": signal_entry.get("signals") or [],
                    "candidates": (signal_entry.get("candidates") or [])[:MAX_CANDIDATES],
                    "page": page,
                    "bbox": bbox,
                }
            )
            if len(items) >= MAX_GATE_ITEMS:
                return items
    return items


def flagged_fields_by_document(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    """``{documentId: [fieldPath…]}`` para etiquetar ``needs_clarification``."""
    flagged: dict[str, list[str]] = {}
    for item in items:
        flagged.setdefault(item["documentId"], []).append(item["fieldPath"])
    return flagged


def exclude_verified_items(
    items: list[dict[str, Any]],
    verification_by_document: dict[str, dict[str, Any]],
    min_level: int,
) -> list[dict[str, Any]]:
    """Filtro Rossum (E5 · §3.1): excluye los gate items cuyo fieldPath ya
    tiene ``verification.level >= min_level`` en su documento.

    ``min_level=1`` para el stage L2: lo verificado por L1 (o superior) no se
    re-presenta; ``external`` (level 0) NO cuenta como verificación L1.
    """
    filtered: list[dict[str, Any]] = []
    for item in items:
        verification = verification_by_document.get(item.get("documentId") or "") or {}
        entry = verification.get(item.get("fieldPath") or "")
        if isinstance(entry, dict) and int(entry.get("level") or 0) >= min_level:
            continue
        filtered.append(item)
    return filtered
