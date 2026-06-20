"""Helpers sobre los payloads de las Lambdas de procesamiento.

Movidos desde ``processing_job_processing`` (E1, cutover D4) porque los usan las
activities (``read_s3_json``, ``persist_document_texts``) y los handlers de fase
del intérprete — sobreviven al borrado del workflow legacy. Son funciones puras
sobre los JSON que persisten ``extract_text`` y ``classify_pages``.
"""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    ClassifiedDocumentRef,
)


def _safe_uuid(value: object) -> UUID | None:
    """Best-effort UUID parse.

    classify_pages echoes the LLM's `document_type_id` verbatim when it
    matches no catalog entry (e.g. "unknown", a slug, or a hallucinated id).
    That must degrade to an untyped document — never crash the workflow task,
    which would loop the activation forever.
    """
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def extract_classified_refs(classify_data: dict) -> list[ClassifiedDocumentRef]:
    # classify_pages persists {status, classification: {documents: [...]}, metadata}.
    # Fall back to the root for callers that pass an already-unwrapped payload.
    classification = classify_data.get("classification") or classify_data
    out: list[ClassifiedDocumentRef] = []
    for entry in classification.get("documents") or []:
        doctype = entry.get("document_type") or {}
        type_id = doctype.get("uuid") or doctype.get("id")
        page_numbers = sorted(
            {
                int(p["page_number"])
                for p in (entry.get("pages") or [])
                if isinstance(p, dict) and p.get("page_number") is not None
            }
        )
        page_range: dict | None = {"from": page_numbers[0], "to": page_numbers[-1]} if page_numbers else None
        out.append(
            ClassifiedDocumentRef(
                document_type_id=_safe_uuid(type_id),
                document_type_name=doctype.get("name"),
                document_index=int(entry.get("document_index", len(out))),
                page_range=page_range,
            )
        )
    return out


def build_page_text_map(extract_text_data: dict) -> dict[int, str]:
    """Map ``page_number → formatted_text`` from an ``extract_text.json`` payload.

    extract_text persists ``{status, layouts: {pages: [...]}, metadata}``; each
    page carries ``formatted_text`` (Markdown-ish OCR). Fall back to the raw
    ``text`` when a page has no formatted variant, and to the root when the
    payload was already unwrapped from its ``layouts`` envelope.
    """
    layouts = extract_text_data.get("layouts") or extract_text_data
    page_map: dict[int, str] = {}
    for page in layouts.get("pages") or []:
        if not isinstance(page, dict):
            continue
        number = page.get("page_number")
        if number is None:
            continue
        page_map[int(number)] = page.get("formatted_text") or page.get("text") or ""
    return page_map


def slice_document_text(page_text_map: dict[int, str], page_range: dict | None) -> str:
    """Join the OCR text of the pages a single document spans, one block per
    page.

    Each block is prefixed with an ``<!-- PAGE: n -->`` marker so the ``Plain``
    view (and any downstream consumer) can tell pages apart; ``n`` is the source
    page number, preserving provenance back to the original file::

        <!-- PAGE: 1 -->

        ...page 1 text...

        <!-- PAGE: 2 -->

        ...page 2 text...

    ``page_range`` is the contiguous ``{from, to}`` span assigned by
    classify_pages (1-based, matching extract_text page numbers). When absent
    (e.g. single-document uploads) we fall back to the whole file so the
    ``Plain`` view is never empty for a one-document set.
    """
    start, end = (page_range or {}).get("from"), (page_range or {}).get("to")
    if start and end:
        numbers: Iterable[int] = range(int(start), int(end) + 1)
    else:
        numbers = sorted(page_text_map)
    blocks = [
        f"<!-- PAGE: {n} -->\n\n{page_text_map[n]}"
        for n in numbers
        if page_text_map.get(n)
    ]
    return "\n\n".join(blocks)
