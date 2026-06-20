---
feature: extraction
type: plan
status: partial
coverage: 80
audited: 2026-06-16
---

# Enriched Extraction Output — Páginas y Bounding Boxes (repo `doxiq`)

> Spec **accionable** para el refactor del backend (Temporal + persistencia + API + frontend).
> El contrato de salida de las lambdas (shapes, algoritmo de resolución de bbox) ya está en producción; vive en `product/specs/extraction/extract_fields_v2.md` y se asume como precondición.

## 1. Objetivo

Enriquecer la respuesta final de `DocumentProcessingWorkflow` y la persistencia en `workflow_documents` con dos piezas de información que hoy se pierden entre las lambdas y el backend:

1. **`pages: list[int]`** — páginas del PDF original de las que se compone cada documento clasificado (para el PDF viewer que muestra el PDF completo y necesita saber a qué páginas pertenece cada documento extraído).
2. **`mapped_output`** — árbol con la misma forma del schema de extracción, pero con cada hoja escalar envuelta como `{value, source_text, page_number, bbox, inferred}` para pintar overlays de bounding boxes en el PDF viewer.

Adicionalmente, aprovechar el refactor para **eliminar el loop por documento** en el workflow (las lambdas ya son batch) y reducir 2·N invocaciones a solo 2.

## 2. Contrato vigente de las lambdas (precondición — NO se toca)

Verificado contra código en `vnext-tools/src/presentation/{extract_fields,validate_extraction,classify_pages}/app.py`.

### 2.1 Invocación

Todas las lambdas aceptan:
- `{job_id, inline_response: bool, source?, <inline_payload>?}` — si `source` está y el payload inline no, se lee el payload de S3.
- Responden **directo** si `inline_response=True`, o escriben el contenido a S3 y devuelven `{status, ..., source: "s3://..."}` si `inline_response=False` (default `False`).

### 2.2 `classify_pages`

Return al caller (cuando `inline_response=False`):
```jsonc
{"status": "success", "metadata": {"total": N, "job_id": "..."}, "source": "s3://bucket/jobs/<job>/classify_pages.json"}
```
Contenido del archivo S3 (en `source`):
```jsonc
{
  "documents": [
    {
      "document_type": {"uuid": "...", "name": "...", "fields": {...}, "validation_rules": [...]},
      "pages": [{"page_number": 1, "text": "...", "width": N, "height": N, "blocks": [...]}, ...]
    },
    ...
  ]
}
```

### 2.3 `extract_fields` (batch)

Payload de invocación:
```jsonc
{"job_id": "...", "source": "<classify_pages S3 source>", "inline_response": false}
```
(**no** lleva `document_index`; el payload viejo con `document_index` ya no se usa en el lambda.)

Return al caller:
```jsonc
{
  "status": "success|partial|error",
  "errors": [{"document_index": int, "error": str, "error_type": str}, ...],
  "metadata": {"process_time": float, "total": N, "succeeded": N, "failed": N, "job_id": "..."},
  "source": "s3://bucket/jobs/<job>/extract_fields.json"
}
```
Contenido del archivo S3 (es una **lista** — `persist_result` escribe solo `extractions`, no el wrapper):
```jsonc
[
  {
    "document_type": {...},
    "output": {"nombres": "LAURA VERONICA", "numero_cedula": "13021132", "sexo": null},
    "mapped_output": {
      "nombres": {
        "value": "LAURA VERONICA",
        "source_text": "LAURA VERONICA",
        "page_number": 1,
        "bbox": [{
          "page_number": 1,
          "polygon": [{"x":0.255,"y":0.778},{"x":0.406,"y":0.778},{"x":0.406,"y":0.788},{"x":0.255,"y":0.788}],
          "matched_text": "LAURA VERONICA",
          "confidence": 0.997
        }],
        "inferred": false
      },
      "sexo": {"value": null, "source_text": null, "page_number": null, "bbox": [], "inferred": false}
    },
    "document_index": 0
  },
  ...
]
```

### 2.4 `validate_extraction` (batch)

Payload:
```jsonc
{"job_id": "...", "source": "<extract_fields S3 source>", "inline_response": false}
```

Return al caller:
```jsonc
{
  "status": "success|partial|error",
  "errors": [...],
  "metadata": {...},
  "source": "s3://bucket/jobs/<job>/validate_extraction.json"
}
```
Contenido S3 (lista de validations — **sin `mapped_output`**):
```jsonc
[
  {
    "document_type": {...},
    "output": {...},
    "document_index": 0,
    "validation_results": [{"rule_id": "...", "field": "...", "status": "passed|failed", "severity": "info|warning|error", "value_analyzed": "...", "reason": "..."}, ...]
  },
  ...
]
```

### 2.5 Hecho crítico

`validate_extraction` **no propaga `mapped_output`**. El workflow tiene que leer los dos S3 (extract_fields + validate_extraction) y hacer merge por `document_index`.

## 3. Shape objetivo del `DocumentProcessingOutput`

Cada elemento de `documents[]`:

```jsonc
{
  "document_index": 0,
  "document_type": {...},
  "pages": [1, 2],                                   // ← NUEVO — páginas del PDF original
  "output": {"nombres": "...", ...},                 // ← RENAME desde `extraction` — dict plano
  "mapped_output": {"nombres": {...bbox...}, ...},   // ← NUEVO — árbol enriquecido
  "validation": [{"rule_id": ...}, ...],             // igual que hoy
  "error": null                                       // ← NUEVO opcional — copia del entry errors[] si el doc falló extract o validate
}
```

El campo `extraction` desaparece de `DocumentResult`. Consumidores actuales deben leer `output`.

## 4. Archivos a tocar (checklist)

### 4.1 Entidades Pydantic — `backend/src/common/domain/entities/workflows/document_processing.py`

**Antes** (líneas 46-62):
```python
class PersistExtractionInput(BaseModel):
    document_id: str
    tenant_id: str
    extraction: dict = Field(default_factory=dict)
    validation: list = Field(default_factory=list)


class DocumentResult(BaseModel):
    document_index: int
    document_type: dict
    extraction: dict = Field(default_factory=dict)
    validation: list[dict] = Field(default_factory=list)


class DocumentProcessingOutput(BaseModel):
    job_id: str
    documents: list[DocumentResult] = Field(default_factory=list)
```

**Después**:
```python
class BBoxHit(BaseModel):
    page_number: int
    polygon: list[dict]                                   # [{x,y}, {x,y}, {x,y}, {x,y}]
    matched_text: str
    confidence: float | None = None


class MappedLeaf(BaseModel):
    value: str | int | float | bool | None = None
    source_text: str | None = None
    page_number: int | None = None
    bbox: list[BBoxHit] = Field(default_factory=list)
    inferred: bool = False


class PersistExtractionInput(BaseModel):
    document_id: str
    tenant_id: str
    pages: list[int] = Field(default_factory=list)                    # NUEVO
    output: dict = Field(default_factory=dict)                        # renombrado desde `extraction`
    mapped_output: dict = Field(default_factory=dict)                 # NUEVO
    validation: list = Field(default_factory=list)


class DocumentResult(BaseModel):
    document_index: int
    document_type: dict
    pages: list[int] = Field(default_factory=list)                    # NUEVO
    output: dict = Field(default_factory=dict)                        # renombrado desde `extraction`
    mapped_output: dict = Field(default_factory=dict)                 # NUEVO
    validation: list[dict] = Field(default_factory=list)
    error: dict | None = None                                         # NUEVO — populated si la lambda falló el doc
```

> `mapped_output` se tipa como `dict`, no como `dict[str, MappedLeaf]`, porque el árbol puede tener objetos anidados y arrays. `MappedLeaf` y `BBoxHit` existen como contratos documentales y de tipado para tests/frontend.

### 4.2 Workflow — `backend/src/workflows/presentation/workflows/document_processing.py`

Sustituir el loop `for doc_index in range(total_documents)` (líneas 124-159) por 2 invocaciones batch + merge:

```python
@workflow.run
async def run(self, payload: DocumentProcessingInput) -> DocumentProcessingOutput:
    data = DocumentProcessingInput.model_validate(payload)
    job_id = data.job_id or workflow.uuid4().hex

    # 1. Extract text (OCR)
    extract_text_result = await self._invoke_lambda(
        EXTRACT_TEXT_FUNCTION_NAME,
        {"object_key": data.object_key, "extractor": data.extractor, "job_id": job_id, "inline_response": False},
        timedelta(minutes=5),
        label="extract_text",
    )
    await self._checkpoint()

    # 2. Classify pages
    classify_result = await self._invoke_lambda(
        CLASSIFY_PAGES_FUNCTION_NAME,
        {"source": extract_text_result["source"], "document_types": data.document_types, "job_id": job_id, "inline_response": False},
        timedelta(minutes=3),
        label="classify_pages",
    )
    await self._checkpoint()

    # 3. Extract fields — batch, 1 invocación
    extract_fields_result = await self._invoke_lambda(
        EXTRACT_FIELDS_FUNCTION_NAME,
        {"source": classify_result["source"], "job_id": job_id, "inline_response": False},
        timedelta(minutes=5),
        label="extract_fields",
    )
    if extract_fields_result.get("status") == "error":
        raise ApplicationError("extract_fields batch failed", non_retryable=True)
    await self._checkpoint()

    # 4. Validate extraction — batch, 1 invocación
    validate_result = await self._invoke_lambda(
        VALIDATE_EXTRACTION_FUNCTION_NAME,
        {"source": extract_fields_result["source"], "job_id": job_id, "inline_response": False},
        timedelta(minutes=5),
        label="validate_extraction",
    )
    if validate_result.get("status") == "error":
        raise ApplicationError("validate_extraction batch failed", non_retryable=True)
    await self._checkpoint()

    # 5. Leer los 3 artefactos S3 para el merge
    classify_data   = await self._read_s3_json(classify_result["source"],        label="read_classify")
    extractions     = await self._read_s3_json(extract_fields_result["source"],  label="read_extractions")      # list[dict]
    validations     = await self._read_s3_json(validate_result["source"],        label="read_validations")       # list[dict]

    # 6. Merge por document_index
    classify_docs   = classify_data.get("documents", [])
    pages_per_doc: dict[int, list[int]] = {
        i: sorted({p["page_number"] for p in d.get("pages", [])})
        for i, d in enumerate(classify_docs)
    }
    extractions_by_idx = {e["document_index"]: e for e in extractions}
    validations_by_idx = {v["document_index"]: v for v in validations}
    extract_errors_by_idx = {
        e["document_index"]: e for e in extract_fields_result.get("errors", [])
    }

    documents: list[DocumentResult] = []
    for i in sorted(pages_per_doc.keys()):
        extraction_entry = extractions_by_idx.get(i)
        validation_entry = validations_by_idx.get(i, {})
        if extraction_entry:
            doc_type = extraction_entry["document_type"]
            output = extraction_entry.get("output", {})
            mapped_output = extraction_entry.get("mapped_output", {})
            error = None
        else:
            doc_type = classify_docs[i].get("document_type", {})
            output = {}
            mapped_output = {}
            error = extract_errors_by_idx.get(i)
        documents.append(
            DocumentResult(
                document_index=i,
                document_type=doc_type,
                pages=pages_per_doc[i],
                output=output,
                mapped_output=mapped_output,
                validation=validation_entry.get("validation_results", []),
                error=error,
            )
        )

    # 7. Persist first doc (opcional, como hoy)
    if data.persist_target_document_id and data.persist_target_tenant_id and documents:
        first = documents[0]
        await workflow.execute_activity(
            PERSIST_EXTRACTION_ACTIVITY,
            PersistExtractionInput(
                document_id=data.persist_target_document_id,
                tenant_id=data.persist_target_tenant_id,
                pages=first.pages,
                output=first.output,
                mapped_output=first.mapped_output,
                validation=first.validation,
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
            activity_id="persist_extraction",
            summary="persist_extraction",
        )

    return DocumentProcessingOutput(job_id=job_id, documents=documents)
```

Lo que se elimina del workflow actual:
- `total_documents = int(classify_result["metadata"]["total"])` y el `for doc_index in range(...)` wrapper.
- El shim legacy `validation_data.get("extracted_values") or validation_data.get("extraction")` (el nuevo contrato solo emite `output`).
- El campo `document_index` en el payload de `extract_fields`.

### 4.3 Activity `persist_extraction` — `backend/src/workflows/presentation/workflows/activities/persist_extraction.py`

**Antes** (líneas 29-44):
```python
document.extraction = data.extraction
document.validation = data.validation
document.status = WorkflowDocumentStatus.EXTRACTED
```

**Después**:
```python
document.extraction = data.output
document.mapped_extraction = data.mapped_output
document.extraction_pages = data.pages
document.validation = data.validation
document.status = WorkflowDocumentStatus.EXTRACTED
```

### 4.4 Modelo ORM — `backend/src/common/database/models/workspace_document.py`

Agregar dos columnas (y mantener `extraction` y `validation` existentes sin cambios estructurales):

```python
mapped_extraction: Mapped[dict | None] = mapped_column(
    JSONB,
    nullable=True,
    default=None,
)

extraction_pages: Mapped[list[int] | None] = mapped_column(
    ARRAY(Integer),
    nullable=True,
    default=None,
)
```
Imports: `from sqlalchemy import Integer`, `from sqlalchemy.dialects.postgresql import ARRAY` (ya se importa `JSONB`).

### 4.5 Entidad de dominio — `backend/src/extraction/domain/entities/document.py`

Agregar los campos en `WorkflowDocument` (comprobar el nombre exacto de la clase ahí):

```python
mapped_extraction: dict | None = None
extraction_pages: list[int] | None = None
```

Y propagar en el constructor / en el repo SQL (mapear del ORM).

### 4.6 Repositorio SQL — `backend/src/extraction/infrastructure/repositories/sql_document_repository.py`

Al hidratar/persistir `WorkflowDocument` ↔ `WorkflowDocumentORM`, copiar `mapped_extraction` y `extraction_pages`.

### 4.7 Presenter — `backend/src/extraction/presentation/presenters/document_presenter.py`

Agregar al `to_dict` (camelCase):
```python
"mappedExtraction": self.instance.mapped_extraction,
"extractionPages": self.instance.extraction_pages,
```

### 4.8 Use case `ExtractFileIntoCaseDocuments` — `backend/src/workflows/application/use_cases/extract_file_into_case_documents.py`

**Antes** (líneas 125-137):
```python
new_doc = WorkflowDocument(
    ...
    extraction=result.extraction or {},
    validation=result.validation or [],
)
```

**Después**:
```python
new_doc = WorkflowDocument(
    ...
    extraction=result.output or {},
    mapped_extraction=result.mapped_output or None,
    extraction_pages=result.pages or None,
    validation=result.validation or [],
)
```

### 4.9 Migration Alembic

Nueva revisión Alembic al final del chain (down_revision = `c4f6dc29412f`). Archivo `backend/src/common/database/versions/<timestamp>_<rev>_workflow_documents_mapped_extraction.py`:

```python
"""workflow_documents: add mapped_extraction + extraction_pages"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "<nuevo_rev>"
down_revision: Union[str, None] = "c4f6dc29412f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_documents",
        sa.Column("mapped_extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "workflow_documents",
        sa.Column("extraction_pages", postgresql.ARRAY(sa.Integer()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_documents", "extraction_pages")
    op.drop_column("workflow_documents", "mapped_extraction")
```

Generar con `just migrate-backend-new "workflow_documents_mapped_extraction"` y sobrescribir el `upgrade/downgrade` con lo anterior.

### 4.10 Frontend — `frontend/src/domain/entities/extraction/*`

Tipos nuevos (TypeScript):
```ts
export interface BBoxHit {
  page_number: number;
  polygon: { x: number; y: number }[];  // len 4
  matched_text: string;
  confidence: number | null;
}

export interface MappedLeaf {
  value: string | number | boolean | null;
  source_text: string | null;
  page_number: number | null;
  bbox: BBoxHit[];
  inferred: boolean;
}

export interface WorkflowDocumentResponse {
  extraction: Record<string, unknown>;        // output plano (value → any primitive)
  mappedExtraction: Record<string, any> | null;  // árbol con MappedLeaf en las hojas (puede ser null para filas viejas)
  extractionPages: number[] | null;
  validation: ValidationResult[];
  // ...otros campos existentes
}
```

PDF viewer:
- Si `mappedExtraction == null` → render sin overlays.
- Recorrer el árbol; para cada hoja con `bbox.length > 0`: convertir los 4 puntos normalizados a canvas:
  `pixelX = point.x * renderedPageWidth; pixelY = point.y * renderedPageHeight`.
- Indicador visual (badge o ícono) cuando `inferred === true`.
- Hover/click sync entre fila de la tabla y overlay del viewer.

## 5. Migración de datos

- No hay backfill automático. Filas ya persistidas tienen `mapped_extraction = NULL` y `extraction_pages = NULL`. El frontend las renderiza sin overlays.
- El contenido de `workflow_documents.extraction` (JSONB existente) sigue siendo un dict `{campo: valor}` — solo cambia el origen (antes `extracted_values`, ahora `output`). Sin data migration.

## 6. Criterios de aceptación

1. `workflow_documents` tiene columnas `mapped_extraction JSONB NULL` y `extraction_pages INT[] NULL`. `just migrate-backend` aplica la nueva revisión.
2. `DocumentProcessingWorkflow.run` ya no tiene loop por documento; invoca `extract_fields` y `validate_extraction` una sola vez cada una.
3. Cada `DocumentResult` tiene `pages` no-vacío, `output` plano, `mapped_output` con hojas enriquecidas (o `{}` si el doc falló), `validation`, y opcional `error`.
4. Cuando `extract_fields_result.status == "partial"`: documentos fallados aparecen en `documents[]` con `output={}, mapped_output={}, error=<entry>`. El workflow termina OK (no raises).
5. Cuando `extract_fields_result.status == "error"` o `validate_result.status == "error"`: workflow raises `ApplicationError` y no persiste nada.
6. `persist_extraction` activity escribe los 4 campos (`extraction`, `mapped_extraction`, `extraction_pages`, `validation`) en la fila `workflow_documents` apuntada por `persist_target_document_id`.
7. `DocumentPresenter.to_dict` expone `mappedExtraction` y `extractionPages` en camelCase.
8. `ExtractFileIntoCaseDocuments._persist_results` crea `WorkflowDocument` con los 4 campos poblados.
9. Frontend tolera `mappedExtraction == null` en filas viejas y renderiza sin overlays sin crashear.
10. Frontend pinta los 4 puntos del `polygon` normalizados al tamaño del viewer para cada leaf con `bbox.length > 0`.

## 7. Tests

- **Unit (workflow merge)**: mock de `invoke_lambda` y `read_s3_json` con fixtures tomadas de `vnext-tools/events/`. Verificar:
  - Caso 2 documentos OK: `documents[].pages`, `.output`, `.mapped_output`, `.validation` correctos.
  - Caso partial: 1 OK + 1 en `errors[]` → `DocumentResult.error` presente en el fallado.
  - Caso status=error → raises ApplicationError.
- **Unit (persist activity)**: setear las 4 columnas, firar pg_notify.
- **Integration (migration)**: correr `upgrade` → `downgrade` → `upgrade`, verificar columnas.
- **E2E (workflow run local)**: un PDF con 2 cédulas → `pages` separa páginas correctas, `bbox` no vacío en campos literales, `inferred=true` en `fecha_nacimiento` normalizada.

## 8. Orden sugerido de implementación

1. Migration Alembic (columna nueva con backfill `NULL` — no bloquea runtime).
2. Modelo ORM + entidad de dominio + repo SQL (propagar los 2 campos).
3. Entidades Pydantic (`DocumentResult`, `PersistExtractionInput`, `BBoxHit`, `MappedLeaf`).
4. Activity `persist_extraction` (setear 4 campos).
5. Use case `ExtractFileIntoCaseDocuments._persist_results` (pasar 4 campos al crear).
6. Refactor del workflow (loop → 2 invocaciones batch + merge).
7. Presenter (camelCase nuevo).
8. Frontend types + viewer overlay + indicador `inferred`.
9. Tests unit/integration/E2E.

## 9. Riesgos

- **`mapped_output` se pierde si el workflow olvida leer el S3 de extract_fields en paralelo al de validate_extraction**. `validate_extraction` no lo propaga. La nueva estructura del workflow (leer los 3 JSONs antes del merge) hace esta operación explícita.
- **Partial failures**: `MAX_CONCURRENT_DOCUMENTS=10` en la lambda; un doc puede fallar mientras otros pasan. El workflow continúa con lo que salió OK y marca los fallados con `DocumentResult.error`. Si la política del negocio quiere abortar en cualquier falla, basta con revisar `status != "success"` y hacer raise.
- **Fuzzy hit incorrecto** (lambda side): umbral `0.85` puede dar matches espurios en documentos con texto repetitivo. Mitigado en la lambda con desambiguación por label. Telemetría: logs INFO del fallback fuzzy.
- **Versión desincronizada lambda↔backend**: si se despliega una versión anterior de la lambda sin post-procesado de bbox, las hojas vendrían sin `bbox`/`inferred`. Mitigación: defaults (`bbox=[]`, `inferred=False`) en `MappedLeaf`. El frontend degrada a vista sin overlays.
- **Textract `width=0, height=0`**: las coordenadas ya están normalizadas 0..1; nunca dividir por width/height del OCR.
