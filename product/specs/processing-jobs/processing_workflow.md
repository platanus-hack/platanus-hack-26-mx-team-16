---
feature: processing-jobs
type: spec
status: implemented
coverage: 95
audited: 2026-06-16
---

# Workflow de Procesamiento de Documentos

## Resumen

El sistema procesa documentos a traves de una cadena de Lambdas donde el output de cada paso
alimenta el input del siguiente. Existen dos flujos: el **pipeline principal** de procesamiento
de documentos y un **flujo independiente** para extraccion de cedulas de identidad.

Los pasos con varios documentos (`extract_fields`, `validate_extraction`) **hacen fan-out internamente**
con un `ThreadPoolExecutor(max_workers=10)`. El orquestador externo ya no necesita iterar por `document_index`;
una sola invocacion procesa todos los documentos del job.

## Pipeline Principal

```
                                    ┌───────────────────────────┐
                                    │      extract_text         │
                                    │  (OCR / extraccion texto) │
                                    └────────────┬──────────────┘
                                                 │
                                    source: s3://jobs/{job_id}/extract_text.json
                                                 │
                                                 ▼
                                    ┌───────────────────────────┐
                                    │     classify_pages        │
                                    │  (clasificacion con IA)   │
                                    └────────────┬──────────────┘
                                                 │
                                    source: s3://jobs/{job_id}/classify_pages.json
                                                 │
                                                 ▼
                                    ┌───────────────────────────┐
                                    │     extract_fields        │
                                    │ (fan-out interno, N docs) │
                                    └────────────┬──────────────┘
                                                 │
                                    source: s3://jobs/{job_id}/extract_fields.json
                                                 │
                                                 ▼
                                    ┌───────────────────────────┐
                                    │   validate_extraction     │
                                    │ (fan-out interno, N docs) │
                                    └────────────┬──────────────┘
                                                 │
                                    source: s3://jobs/{job_id}/validate_extraction.json
```

## Detalle de cada paso

### Paso 1: extract_text

Extrae texto de un documento usando OCR. El motor se selecciona con el campo `extractor`,
tipado por el enum `DocumentExtractorType` (en `src/domain/enums.py`).

- **Input**:
  - `object_key` (S3 key, `s3://` URI o URL HTTPS)
  - `extractor`: uno de `textract` (default: `textract_layout`), `textract_layout`, `documentai`, `documentai_layout`
  - `job_id`, `inline_response`, `bucket` opcionales
- **Output (S3)**: `{ pages: [LayoutPage] }` → persistido bajo `layouts` key; la respuesta retorna `source`

```
Mapeo al siguiente paso:
  extract_text.source  →  classify_pages.source
```

### Paso 2: classify_pages

Clasifica las paginas del documento por tipo usando un agente de IA (Gemini).
Agrupa paginas consecutivas del mismo tipo en un mismo `document`.

- **Input**: `layouts.pages` (inline) o `source` (desde extract_text en S3) + `document_types`
- **Output (S3)**: `{ documents: [{ document_type, pages }] }` → `classification` key

```
Mapeo al siguiente paso:
  classify_pages.source        →  extract_fields.source
  classify_pages.documents[]   →  extract_fields procesa todo el arreglo
```

### Paso 3: extract_fields (fan-out interno)

Extrae datos estructurados de **todos** los documentos identificados por `classify_pages`. Una sola
invocacion del Lambda procesa el arreglo completo en paralelo (`ThreadPoolExecutor(max_workers=10)`).
Si un documento falla, el resto continua y el error se reporta en `errors[]`.

- **Input**:
  - `documents: [{document_type, pages}, ...]` inline, **o**
  - `source` apuntando al resultado de `classify_pages`
- **Output**: `{ status, extractions: [...], errors: [...], metadata }` donde cada item de `extractions[]` trae `document_type`, `output`, `mapped_output` y `document_index`
- **S3**: la lista `extractions` se persiste en `extract_fields.json`; `errors` queda inline en la respuesta

```
Mapeo al siguiente paso:
  extract_fields.source        →  validate_extraction.source
  extract_fields.extractions[] →  validate_extraction procesa todo el arreglo
```

Estados posibles: `success` (todos ok), `partial` (al menos uno fallo, hay parciales), `error`
(lista vacia o todos fallaron — la respuesta incluye `error_code` y `message`).

### Paso 4: validate_extraction (fan-out interno)

Valida **todas** las extracciones producidas por `extract_fields` contra las `validation_rules` de cada
`document_type`. El fan-out es interno con el mismo patron (max 10 concurrentes, resultados parciales).

- **Input**:
  - `extractions: [...]` inline, **o**
  - `source` apuntando al resultado de `extract_fields`
- **Output**: `{ status, validations: [...], errors: [...], metadata }` donde cada item de `validations[]` trae `document_type`, `output`, `document_index` y `validation_results`
- **S3**: la lista `validations` se persiste en `validate_extraction.json`

Las reglas usan templates tipo `{{field_name}}` que se renderizan con valores de `output`. Cada regla
pasa por el equipo coordinado de agentes (Agno + Gemini).

Mismos estados que `extract_fields`: `success` / `partial` / `error`.

## Resultados intermedios via S3

Cada Lambda del pipeline escribe su payload principal a S3 y retorna una referencia (`source`).
El siguiente Lambda puede recibir esa referencia en lugar de datos inline, leyendo el contenido desde S3.

```
s3://vnext-assets-{stage}/jobs/{job_id}/
  extract_text.json          # { pages: [LayoutPage] }
  classify_pages.json        # { documents: [{ document_type, pages }] }
  extract_fields.json        # [ { document_type, output, mapped_output, document_index }, ... ]
  validate_extraction.json   # [ { document_type, output, document_index, validation_results }, ... ]
```

Nota: `extract_fields.json` y `validate_extraction.json` guardan directamente la lista (no un dict wrapper),
porque `persist_result(..., content_key="extractions" | "validations")` extrae la lista del response.
Los `errors[]` del fan-out permanecen en la respuesta inline para que el orquestador pueda inspeccionarlos
sin leer S3.

El flag `inline_response: true` retorna el payload completo en la respuesta en lugar de escribirlo a S3.

## Flujo Independiente: parse_ci

Pipeline standalone para extraccion de datos de Cedulas de Identidad.
No se conecta con el pipeline principal.

```
  PDF en S3 → Textract (OCR) → IA (Gemini) → PersonCI (datos estructurados)
```

- **Input**: URI del documento en S3 (`documentUri`)
- **Output**: Datos personales extraidos (nombre, apellido, cedula, etc.)

## Notas de Integracion

- La orquestacion entre Lambdas se realiza externamente (Temporal, Step Functions o cliente). El orquestador solo encadena `source` entre pasos; **no itera** sobre `documents[]`.
- Los pasos 3 y 4 hacen fan-out internamente con un limite de 10 documentos concurrentes. Para ajustar,
  modificar `MAX_CONCURRENT_DOCUMENTS` / `MAX_CONCURRENT_EXTRACTIONS` en cada `app.py`.
- Manejo de errores por lote:
  - `status: "success"` — todo ok, `errors: []`
  - `status: "partial"` — algunos fallaron; los exitosos van en `extractions` / `validations`, los fallidos en `errors[]`. El orquestador debe decidir si continuar o abortar.
  - `status: "error"` — ningun documento exitoso; la respuesta incluye `error_code` (ej. `extract_fields.all_failed`) y `message` con contexto.
- Cada entrada en `errors[]` tiene la forma `{document_index, error, error_type}`.
- El `document_type` completo (con `validation_rules`) se propaga automaticamente entre pasos via S3.
- Cada ejecucion del pipeline se agrupa bajo un `job_id` unico en S3.
