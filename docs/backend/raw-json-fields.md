# RawJson fields

## Why this exists

API responses are emitted in camelCase by `CamelCaseJSONResponse` (registered as the FastAPI `default_response_class`). It walks the response payload and runs `to_camel(...)` on every dict key recursively.

Some fields stored in the database are JSONB blobs whose **keys are domain data** — slugs, user-defined field names, JSON-schema property names, LLM output. Recursively camelCasing those keys would mangle the wire payload (e.g. `loan_contract` → `loanContract`, breaking lookups against `selectedDocTypes`).

`RawJson` is a sentinel that wraps a value in the presenter `to_dict` and disables key conversion for that subtree:

```python
from src.common.application.helpers.json_encoder import RawJson

return {
    "per_doc_schema": RawJson(self.instance.per_doc_schema),
    ...
}
```

The wrapped value is passed through `convert_to_camel_case` untouched. Only the key under which it sits (`perDocSchema` after conversion) is camelCased; everything inside is verbatim.

See `src/common/application/helpers/json_encoder.py` for the implementation, and `tests/common/infrastructure/responses/test_api_json_raw_json.py` for the end-to-end behavior.

## Wrapped fields by presenter

Listed by file path → field → why.

### `src/workflows/presentation/presenters/workflow.py`

| Field | Why |
|---|---|
| `per_doc_schema` | Outer keys are doctype slugs (`loan_contract`, `id_card`). Inner content is a JSON Schema whose `properties` keys are user-defined extraction fields. Both layers are domain data. |
| `per_doc_kb_ids` | Outer keys are doctype slugs; values are lists of KB document UUIDs (no inner keys). |

### `src/workflows/presentation/presenters/analysis_rule.py`

| Field | Why |
|---|---|
| `output_schema` | User-authored JSON Schema. The `properties` sub-dict has user-defined property names; camelCasing would corrupt them. |

### `src/workflows/presentation/presenters/analysis_rule_result.py`

| Field | Why |
|---|---|
| `document_refs` | Outer keys are doctype slugs. Inner sub-dict has presenter-defined keys (`document_id`, `document_type_name`) — these are **pre-written camelCase** in the presenter so the entire subtree can ride `RawJson` without further transformation. |
| `preliminary_checks` | LLM-emitted intermediate check results; arbitrary keys produced by the model. |
| `structured_output` | LLM-emitted structured output following the user's `output_schema`; arbitrary keys. |

### `src/workflows/presentation/presenters/workflow_document.py`

| Field | Why |
|---|---|
| `extraction` | LLM extraction output keyed by user-defined extraction fields. Inner values are primitives. |
| `mapped_extraction` | Outer keys are user-defined fields; inner values are `MappedField` dicts emitted by the `extract_fields` lambda with snake_case keys (`source_text`, `page_number`, `bbox`, `inferred`) — left as-is so storage, wire, and frontend types stay aligned. The frontend `MappedField`/`MappedBbox` interfaces declare those keys snake_case. |

### `src/workflows/presentation/presenters/document_type.py`

| Field | Why |
|---|---|
| `fields` | User-authored field schema for the document type; keys are user-defined extraction field names. |

## Fields explicitly NOT wrapped (and why)

These are JSONB columns at the storage layer but the **keys are presenter/developer-controlled** (no domain data). Letting them flow through normal camelCase conversion is correct.

| Presenter | Field | Why not wrapped |
|---|---|---|
| `analysis_rule.py` | `parsed_checks`, `previous_parsed_checks` | Parser output. Keys are emitted by our parser (e.g. `expr_type`, `operands`) and should be camelCased like everything else. |
| `workflow_document_set.py` | `result_summary` | Stats dict produced by the workflow runner with developer-defined keys (e.g. `docs`, `extractor`). |
| `workflow_document.py` | `extraction_metadata` | OCR/extraction metadata with developer-defined keys (`provider`, `model`, `pages`, etc.). |
| `workflow_document.py` | `validation` | List of validation results with structured keys. |
| `workflow_document.py` | `page_range` | Small dict with `start` / `end` integer bounds. |
| `document_type.py` | `validation_rules` | List of validation rule definitions with structured keys (`name`, `expression`, `severity`). |
| `analysis_rule_result.py` | `citations`, `consensus` | Hand-serialized in the presenter via `_serialize_citation` / `_serialize_consensus`, which whitelist a small set of presenter-defined keys (`claim`, `document_id`, `field_path`, `n_samples`, `agreement_ratio`, `verdicts`). |

If any of these later starts storing domain-keyed data (e.g. `result_summary` ends up keyed by tenant or doctype slug), wrap it in `RawJson` — the rule is **the keys, not the type**.

## Decision rule

When adding a JSONB-typed field to a presenter, ask: **who chose these keys?**

- **Developer / presenter chose them** (literals like `"document_id"`, `"name"`, `"expression"`): leave it alone, let `CamelCaseJSONResponse` convert.
- **End user, document author, or the LLM chose them** (slugs, schema field names, OCR output keys): wrap in `RawJson(...)`.

If both layers are present (developer-keyed sub-dict under a domain-keyed outer dict, like `document_refs`): wrap the whole thing in `RawJson` and **pre-write the inner keys camelCase** in the presenter.

## How it interacts with FastAPI's `jsonable_encoder`

FastAPI calls `jsonable_encoder` on the route's return value before instantiating the response class. Without help, that call falls through to `vars(obj)` and crashes on `RawJson` (it uses `__slots__`). The fix is registered once at module import:

```python
ENCODERS_BY_TYPE[RawJson] = lambda raw: raw
```

This makes `jsonable_encoder` treat `RawJson` as a passthrough; the marker stays alive until `convert_to_camel_case` strips it during render.

## Frontend implications

The frontend (`/frontend`) consumes these wire payloads. Anything inside a `RawJson` arrives **verbatim from storage** — the camelCase normalization that the rest of the response enjoys does not apply.

Conventions to follow:

- **Iterate, don't index by hardcoded literal**. Most consumers already do this — `Object.entries(extraction)`, `Object.keys(perDocSchema)`, `Object.entries(documentRefs)`. The keys are domain data and they should not be assumed to match any particular casing rule.
- **Cross-references stay consistent**. `selectedDocTypes` items and `perDocSchema` keys are both unwrapped slugs (snake_case in storage), so `perDocSchema[selectedDocTypes[i]]` works without any pre-conversion. Don't reintroduce a `to_camel`/`to_snake` step on the frontend; both sides already align.
- **Type the inner shape to match storage** when the JSONB has a stable schema (not free-form domain keys). For example, `MappedField` / `MappedBbox` (in `src/infrastructure/repositories/http-workflow-document.ts`) declare snake_case fields (`source_text`, `page_number`, `matched_text`, `bbox`) because the `extract_fields` lambda emits them snake_case and `RawJson` keeps them so end-to-end.
- **The `document_refs` exception**. Because the presenter writes its inner keys camelCase explicitly (see the table above), the frontend `DocumentRef` type stays camelCase (`documentId`, `documentTypeName`). This is the one place where the inner shape *does* depart from storage — the deviation is hardcoded in the presenter, not enforced by `RawJson`.
- **`formatDoctypeSlug`** in `analysis-rule-results.tsx` is the reference helper for displaying a slug to humans (it replaces underscores/hyphens with spaces). Use it whenever you need a legible label from a `RawJson`-preserved slug instead of inventing a new transform.

When adding a new RawJson field, ask the same question as the backend rule, plus one more: does the frontend need to display these keys to a human? If so, decide whether to surface them raw (as IDs in `data-*` attributes, in dev tools, etc.) or run them through a slug formatter for display.
