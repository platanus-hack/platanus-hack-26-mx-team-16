---
feature: extraction
type: spec
status: pending
coverage: 25
audited: 2026-06-16
backlog: true
---

# Extra fields

Convención: nombres de propiedades en `snake_case`. Las extensiones de JSON Schema mantienen el guión (`x-source-hint`) para alinearse con el estándar.

**Áreas de utilidad:** `extracción` · `clasificación` · `segmentación` · `validación` · `confianza` · `UI` · `interno` · `organización`.

## DocumentTypeField

| Prop | Tipo | JSON Schema | Categoría | Requerido | Ejemplo | Utilidad (1–10) | Estado |
|---|---|---|---|---|---|---|---|
| `name` | string | property key | identidad | sí | `"invoice_number"` | 10 — extracción | existente |
| `type` | enum | `type` | identidad | sí | `"text"` / `"number"` / `"date"` / `"object"` | 10 — extracción | existente |
| `format` | enum | `format` | identidad | no | `"date"` / `"email"` / `"uri"` | 7 — extracción | existente |
| `required` | bool | `required[]` raíz | identidad | no (default `false`) | `true` | 6 — validación | existente |
| `enabled` | bool | filtro de export | identidad | no (default `true`) | `true` | 3 — interno | existente |
| `children` | nested | `properties` / `items` | identidad | sí si `type` = `object`/`array` | `[{name:"line_total", type:"number"}]` | 9 — extracción | existente |
| `title` | string | `title` | semántico | no | `"Número de factura"` | 4 — UI | nuevo |
| `description` | string | `description` | semántico | recomendado | `"Folio único asignado por el emisor"` | 9 — extracción | existente |
| `examples` | string[] | `examples` | semántico | recomendado | `["F001-00012345", "B-2024-001"]` | 8 — extracción | existente |
| `alternatives` | string[] | `x-alternatives` | semántico | no | `["nro factura", "folio", "invoice no"]` | 8 — extracción | existente |
| `slug` | string | `x-slug` | semántico | no | `"invoice_no"` | 3 — interno | existente (sin UI) |
| `ai_prompt` | string | `x-ai-prompt` | semántico | no | `"Extrae el folio de la cabecera"` | 8 — extracción | existente (sin UI) |
| `location_hint` | string | `x-location-hint` | semántico | no | `"esquina superior derecha"` | 7 — extracción | existente (sin UI) |
| `negative_examples` | string[] | `x-negative-examples` | semántico | no | `["número de cliente", "número de orden"]` | 9 — extracción | nuevo |
| `source_hint` | enum | `x-source-hint` | semántico | no | `"header"` | 7 — extracción | nuevo |
| `extraction_strategy` | enum | `x-extraction-strategy` | semántico | no (default `verbatim`) | `"normalized"` | 6 — extracción | nuevo |
| `enum` | string[] | `enum` | restricción | no | `["pendiente", "pagado", "anulado"]` | 9 — extracción + validación | nuevo |
| `pattern` | regex | `pattern` | restricción | no | `"^F\\d{3}-\\d{8}$"` | 9 — validación | nuevo |
| `min_length` | int | `minLength` | restricción | no | `8` | 5 — validación | nuevo |
| `max_length` | int | `maxLength` | restricción | no | `20` | 5 — validación | nuevo |
| `minimum` | number | `minimum` | restricción | no | `0` | 7 — validación | nuevo |
| `maximum` | number | `maximum` | restricción | no | `999999.99` | 7 — validación | nuevo |
| `multiple_of` | number | `multipleOf` | restricción | no | `0.01` | 4 — validación | nuevo |
| `default` | any | `default` | restricción | no | `"pendiente"` / `0` | 4 — UI | nuevo |
| `unit` | string | `x-unit` | restricción | no | `"USD"` / `"%"` / `"kg"` | 8 — extracción | nuevo |
| `depends_on` | expr | `x-depends-on` | confianza | no | `"total == subtotal + tax"` | 8 — validación | nuevo |
| `confidence_threshold` | float | `x-confidence-threshold` | confianza | no | `0.85` | 7 — confianza | nuevo |
| `fallback_behavior` | enum | `x-fallback` | confianza | no (default `null`) | `"flag_review"` | 6 — confianza | nuevo |

> Eliminadas (vestigiales, no usadas en el pipeline): `icon`, `order`, `allow_multiple_values`, `no_rectangle`, `manual_entry_only`.

**Valores de los enums:**

- `source_hint`: `header` · `body` · `table` · `footer` · `barcode` · `stamp` · `handwritten`
- `extraction_strategy`: `verbatim` · `normalized` · `inferred` · `computed`
- `fallback_behavior`: `null` · `empty` · `last_known` · `flag_review`
- `unit` (ejemplos): `USD`, `MXN`, `kg`, `%`, `m²`

---

## DocumentType

| Prop | Tipo | Categoría | Requerido | Ejemplo | Utilidad (1–10) | Beneficio | Estado |
|---|---|---|---|---|---|---|---|
| `uuid` | UUID | identidad | sí | `"a1b2c3d4-…"` | 10 — interno | — | existente |
| `tenant_id` | UUID | identidad | sí | `"f9e8…"` | 10 — interno | — | existente |
| `workflow_id` | UUID | identidad | sí | `"7c6b…"` | 10 — interno | — | existente |
| `name` | string | identidad | sí | `"Factura electrónica"` | 9 — clasificación | input al clasificador | existente |
| `slug` | string | identidad | no | `"factura_electronica"` | 4 — interno | — | existente |
| `is_shareable` | bool | identidad | no (default `false`) | `false` | 3 — interno | — | existente |
| `sample_file_id` | UUID | identidad | no | `"…"` | 7 — clasificación + extracción | Documento ejemplo que se embebe en el prompt como referencia visual/textual para guiar al LLM | existente |
| `created_at` | datetime | identidad | auto | `"2026-05-03T12:00:00Z"` | 2 — interno | — | existente |
| `updated_at` | datetime | identidad | auto | `"2026-05-03T12:00:00Z"` | 2 — interno | — | existente |
| `description` | string | contenido | recomendado | `"Comprobante fiscal emitido por proveedores autorizados"` | 9 — clasificación | Texto que el clasificador lee para diferenciar tipos parecidos (factura vs boleta vs nota de crédito) | existente |
| `fields` | JSON Schema | contenido | sí (para extracción) | `{type:"object", properties:{…}}` | 10 — extracción | Schema de salida que el extractor debe llenar; define qué datos se sacan y en qué formato | existente |
| `validation_rules` | dict[] | contenido | no | `[{name:"total>0", code:"…"}]` | 7 — validación | Reglas que corren tras la extracción para verificar consistencia (totales cuadran, fechas válidas, etc.) | existente |
| `anchor_phrases` | string[] | clasificación | recomendado | `["FACTURA ELECTRÓNICA", "RUC:"]` | 10 — clasificación | Frases canónicas casi siempre presentes en este tipo; su detección sube la probabilidad y reduce falsos negativos | nuevo |
| `exclusion_phrases` | string[] | clasificación | no | `["PROFORMA", "COTIZACIÓN"]` | 9 — clasificación | Frases que descalifican al tipo (una "factura" con "PROFORMA" no es factura); reducen falsos positivos | nuevo |
| `required_fields_for_classification` | string[] | clasificación | no | `["invoice_number", "tax_id", "total"]` | 8 — clasificación | Si el extractor encuentra todos estos campos, se confirma con alta certeza que el documento es de este tipo | nuevo |
| `sibling_doctypes` | UUID[] | clasificación | no | `["<uuid Boleta>", "<uuid Nota Crédito>"]` | 8 — clasificación | Tipos confundibles; cuando el clasificador duda, dispara un prompt binario dedicado para elegir entre los dos | nuevo |
| `document_layout` | enum | clasificación | no | `"receipt"` | 6 — clasificación + extracción | El extractor cambia heurísticas de OCR/parsing según el layout (tabla, formulario, recibo, ID, carta) | nuevo |
| `page_role` | enum | clasificación | no | `"body"` | 7 — segmentación | En PDFs multidocumento, distingue si una página es portada, cuerpo, anexo o firma para agruparla bien | nuevo |
| `typical_page_count` | int o `{min, max}` | clasificación | no | `1` o `{min:1, max:3}` | 6 — segmentación | Ayuda a decidir cuántas páginas consecutivas agrupar como una sola instancia del tipo | nuevo |
| `language_locale` | string | clasificación | no (default tenant) | `"es-PE"` | 7 — extracción | Controla el parser de números y fechas (`1.000,00` vs `1,000.00`; `dd/mm/yyyy` vs `mm/dd/yyyy`) | nuevo |
| `industry` | string | metadata | no | `"retail"` / `"healthcare"` | 4 — organización | Agrupa doctypes por rubro para filtros en UI y reúso entre tenants del mismo sector | nuevo |
| `category` | string | metadata | no | `"facturacion"` / `"identificacion"` | 4 — organización | Agrupación funcional (facturación, RRHH, salud) para navegación, permisos y dashboards | nuevo |
| `version` | int | metadata | no (default `1`) | `2` | 5 — interno | Permite saber con qué versión del schema se hizo cada extracción cuando el doctype evoluciona | nuevo |
| `reference_file_ids` | UUID[] | metadata | no | `["<uuid1>", "<uuid2>"]` | 7 — clasificación + extracción | El LLM ve varios ejemplos del tipo en lugar de uno solo; mejora generalización y few-shot | nuevo |

**Valores de los enums:**

- `document_layout`: `form` · `letter` · `table` · `receipt` · `id_card`
- `page_role`: `cover` · `body` · `annex` · `signature`
- `language_locale` (ejemplos): `es-MX`, `es-CO`, `es-CL`, `es-PE`, `en-US`

---

## Top picks por área

**Clasificación (lift más alto, primer PR):** `anchor_phrases` (10), `exclusion_phrases` (9), `required_fields_for_classification` (8), `sibling_doctypes` (8).

**Extracción (mayor reducción de errores):** `negative_examples` (9), `enum` (9), `pattern` (9), `unit` (8), `examples` (8), `alternatives` (8), `ai_prompt` (8).

**Validación post-extracción:** `pattern` (9), `depends_on` (8), `minimum`/`maximum` (7).
