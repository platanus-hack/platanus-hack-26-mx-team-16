"""Unit tests de los helpers puros sobre payloads de las Lambdas.

Reemplaza a ``test_document_processing.py`` (E1, cutover D4): los helpers
estáticos del workflow legacy (`_extract_classified_refs`, `_count_pages`)
sobreviven como funciones puras en
``src/workflows/presentation/workflows/payload_helpers.py`` y
``src/workflows/domain/utils.py`` — esta suite conserva la misma cobertura
sobre sus nuevos hogares. La orquestación end-to-end del intérprete está
cubierta por ``tests/workflows/application/pipelines/test_standard_v1_regression.py``.
"""

from types import SimpleNamespace

from expects import be_none, equal, expect

from src.workflows.domain.utils import count_pages
from src.workflows.presentation.workflows.payload_helpers import (
    build_page_text_map,
    extract_classified_refs,
    slice_document_text,
)

_DT1 = "11111111-1111-1111-1111-111111111111"
_DT2 = "22222222-2222-2222-2222-222222222222"


# ─── extract_classified_refs ─────────────────────────────────────────────────


def test_extract_classified_refs__derives_page_range_from_pages():
    classify = {
        "documents": [
            {
                "document_type": {"uuid": _DT1, "name": "Cedula"},
                "pages": [{"page_number": 1}, {"page_number": 2}],
            },
            {
                "document_type": {"uuid": _DT2, "name": "Licencia"},
                "pages": [{"page_number": 3}],
            },
        ]
    }

    refs = extract_classified_refs(classify)

    expect(refs[0].page_range).to(equal({"from": 1, "to": 2}))
    expect(refs[1].page_range).to(equal({"from": 3, "to": 3}))


def test_extract_classified_refs__unwraps_classification_envelope():
    # classify_pages persiste {status, classification: {documents: [...]}, metadata}.
    classify = {
        "status": "success",
        "classification": {
            "documents": [
                {
                    "document_type": {"uuid": _DT1, "name": "Cedula"},
                    "pages": [{"page_number": 1}],
                }
            ]
        },
        "metadata": {},
    }

    refs = extract_classified_refs(classify)

    expect(len(refs)).to(equal(1))
    expect(refs[0].document_type_name).to(equal("Cedula"))


def test_extract_classified_refs__page_range_is_none_when_pages_missing():
    classify = {
        "documents": [
            {"document_type": {"uuid": _DT1}},  # no `pages`
            {"document_type": {"uuid": _DT2}, "pages": []},  # empty
        ]
    }

    refs = extract_classified_refs(classify)

    expect(refs[0].page_range).to(be_none)
    expect(refs[1].page_range).to(be_none)


def test_extract_classified_refs__handles_unsorted_and_duplicate_page_numbers():
    classify = {
        "documents": [
            {
                "document_type": {"uuid": _DT1},
                "pages": [
                    {"page_number": 7},
                    {"page_number": 3},
                    {"page_number": 7},
                    {"page_number": 5},
                ],
            }
        ]
    }

    refs = extract_classified_refs(classify)

    expect(refs[0].page_range).to(equal({"from": 3, "to": 7}))


def test_extract_classified_refs__parses_valid_uuid_type_id():
    classify = {
        "documents": [
            {
                "document_type": {"uuid": _DT1, "name": "Cedula"},
                "pages": [{"page_number": 1}],
            }
        ]
    }

    refs = extract_classified_refs(classify)

    expect(str(refs[0].document_type_id)).to(equal(_DT1))
    expect(refs[0].document_type_name).to(equal("Cedula"))


def test_extract_classified_refs__non_uuid_type_id_degrades_to_untyped():
    # classify_pages echoes the LLM's id verbatim when it matches no catalog
    # entry (e.g. "unknown" or a slug) — must never crash the workflow task.
    classify = {
        "documents": [
            {
                "document_type": {"uuid": "unknown", "name": "Otro"},
                "pages": [{"page_number": 1}],
            },
            {
                "document_type": {"id": "invoice-slug"},
                "pages": [{"page_number": 2}],
            },
        ]
    }

    refs = extract_classified_refs(classify)

    expect(refs[0].document_type_id).to(be_none)
    expect(refs[0].document_type_name).to(equal("Otro"))
    expect(refs[1].document_type_id).to(be_none)
    expect(refs[1].page_range).to(equal({"from": 2, "to": 2}))


# ─── build_page_text_map / slice_document_text ───────────────────────────────


def test_build_page_text_map__prefers_formatted_text_with_text_fallback():
    extract = {
        "layouts": {
            "pages": [
                {"page_number": 1, "formatted_text": "# Página 1"},
                {"page_number": 2, "text": "plano 2"},
                {"page_number": None, "text": "huérfana"},
            ]
        }
    }

    page_map = build_page_text_map(extract)

    expect(page_map).to(equal({1: "# Página 1", 2: "plano 2"}))


def test_slice_document_text__joins_page_range_with_page_markers():
    page_map = {1: "uno", 2: "dos", 3: "tres"}

    text = slice_document_text(page_map, {"from": 2, "to": 3})

    expect(text).to(equal("<!-- PAGE: 2 -->\n\ndos\n\n<!-- PAGE: 3 -->\n\ntres"))


def test_slice_document_text__falls_back_to_whole_file_without_range():
    page_map = {1: "uno", 2: "dos"}

    text = slice_document_text(page_map, None)

    expect(text).to(equal("<!-- PAGE: 1 -->\n\nuno\n\n<!-- PAGE: 2 -->\n\ndos"))


# ─── count_pages (src/workflows/domain/utils.py) ─────────────────────────────


def test_count_pages__sums_all_ranges():
    docs = [
        SimpleNamespace(page_range={"from": 1, "to": 3}),
        SimpleNamespace(page_range={"from": 4, "to": 5}),
    ]
    expect(count_pages(docs)).to(equal(5))


def test_count_pages__single_page():
    docs = [SimpleNamespace(page_range={"from": 3, "to": 3})]
    expect(count_pages(docs)).to(equal(1))


def test_count_pages__skips_none_page_range():
    docs = [
        SimpleNamespace(page_range={"from": 1, "to": 2}),
        SimpleNamespace(page_range=None),
    ]
    expect(count_pages(docs)).to(equal(2))


def test_count_pages__empty_list():
    expect(count_pages([])).to(equal(0))
