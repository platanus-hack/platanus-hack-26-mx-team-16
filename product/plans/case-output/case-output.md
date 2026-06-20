---
feature: case-output
type: plan
status: partial
coverage: 80
audited: 2026-06-16
---

# Spec: Salida estructurada del Case (`case-output`)

Estado: **diseño cerrado — pendiente detalle de implementación por archivo** (§7)

---

## 1. Objetivo

Después de que un case (conjunto de documentos cargados) pasa por el pipeline de
procesamiento (OCR → extracción → `mapped_extraction`) y por la ejecución de las
`analysis_rules` (que produce los `analysis_results`), queremos generar una
**salida estructurada enriquecida final** cuyo esquema está definido en el
workflow (`output_schema`).

Esa salida debe combinar **dos fuentes**:
1. Los datos extraídos de cada documento (`WorkflowDocument.mapped_extraction`).
2. Los resultados del análisis (`WorkflowRuleResult` + verdict agregado).

Hoy esto está **parcialmente implementado**: la capa de síntesis existe y persiste
una salida, pero **solo consume los resultados de reglas, no los datos extraídos
de los documentos**. Este spec define cómo cerrar ese gap.

---

## 2. Contexto del codebase actual (qué EXISTE)

> Nota de nomenclatura: los specs previos usan `AnalysisRule` / `WorkflowCase`;
> el código vigente usa `WorkflowRule` / `WorkflowDocument` / `WorkflowAnalysisRun`.
> Aquí referencio los símbolos reales del código.

### 2.1 Esquema de salida en el Workflow
`src/common/domain/models/processing/workflow.py`

| Campo | Tipo | Notas |
|---|---|---|
| `output_schema` | `dict \| None` (JSONB) | JSON Schema de la salida estructurada |
| `synthesis_template` | `str \| None` | prompt/plantilla de síntesis |
| `synthesis_enabled` | `bool` | gate: si false, no se sintetiza |

### 2.2 Datos extraídos por documento
`src/common/domain/models/processing/workflow_document.py`

| Campo | Tipo | Notas |
|---|---|---|
| `extraction` | `dict` | extracción cruda |
| `mapped_extraction` | `dict \| None` | mapeada a `document_type.fields` |
| `validation` | `list` | resultados de validación por campo |
| `document_type_id` | `UUID \| None` | tipo de documento (o "Otros") |

### 2.3 Resultados de análisis
`src/common/domain/models/processing/workflow_rule_result.py`

| Campo | Tipo | Notas |
|---|---|---|
| `output` | `dict \| None` | respuesta estructurada de la regla |
| `reasoning` | `str \| None` | razonamiento del LLM |
| `citations` | `list[Citation]` | citas |
| `document_refs` | `dict` | qué documentos evaluó la regla |
| `status` / `kind` | enum / str | estado y tipo de regla |

### 2.4 Resumen del run (donde vive la salida final)
`src/common/domain/models/processing/workflow_analysis_run_summary.py`

| Campo | Tipo | Notas |
|---|---|---|
| `verdict` / `signals` / `confidence_score` | — | capa **determinística** (agregada de las reglas) |
| `blocking_failures` | `list[UUID]` | |
| `output` | `dict \| None` | **la salida estructurada final** |
| `output_schema_snapshot` | `dict \| None` | schema usado (snapshot) |
| `synthesis_template_snapshot` | `str \| None` | |
| `narrative_status` | enum | `PENDING / RUNNING / COMPLETED / FAILED / SKIPPED` |
| `input_hash` | str | idempotencia de la síntesis |

### 2.5 Flujo de síntesis (ya cableado)
1. `complete_run` (`application/analysis_run_summary/complete_run.py`) marca el run COMPLETED.
2. `VerdictAggregator` (`.../verdict_aggregator.py`) calcula la capa determinística y
   crea el summary con `narrative_status = PENDING` (si `synthesis_enabled`) o `SKIPPED`.
3. `SynthesisRunner` (`.../synthesis_runner.py`) → `SynthesizerAgent`
   (`infrastructure/services/run_summary/synthesizer.py`): llama al LLM constreñido por
   `output_schema`, valida con `jsonschema`, persiste `summary.output`.
4. Soporte adicional: `resynthesizer`, `regenerate_on_run_complete`, `webhook_dispatcher`,
   idempotencia por `input_hash`, re-síntesis con `force`.

### 2.6 Infra de tokens reutilizable (clave para `x-source`)
`infrastructure/services/rules/kinds/_shared/`

- `refs.py` — `parse_doc_refs(prompt) -> [DocRef]`, `parse_kb_refs`, `parse_tokens`.
  Gramática (regex ya implementada):
  - **Doc ref:** `@slug` / `@slug.path` / `@slug.items[].subtotal` (canónico) — `@{slug}.path` alias.
    `DocRefKind = scalar | array | collection`.
  - **KB ref:** `#kb_slug` / `#{kb_slug}`.
  - **Token:** `{{name}}` (name = `[A-Za-z_][\w.]*`).
- `path_resolver.py` — `resolve(DocRef, documents, required) -> [ResolvedValue]`
  camina `EvalDocumentInput.extracted_fields` (= `mapped_extraction`). Soporta
  `.key`, `[i]`, `[]`. **`ResolvedValue` lleva traza**: `document_id`,
  `document_type_slug`, `field_path`, `value` → reutilizable para citaciones (§5.7).
- `substitution.py` — sustitución full-string de `{{token}}` y `@{slug}.path` en un dict.

`EvalDocumentInput` (`domain/rules/kind_protocol.py`): `document_id`,
`document_type_slug`, `extracted_fields`.

### 2.7 Vínculo resultado ↔ documento
`WorkflowRuleResult.document_refs` tiene forma **`{slug: [document_id, ...]}`**
(ver `scope_resolver._refs_for_documents`). Permite, para un `WorkflowDocument` dado,
filtrar los `rule_results` que lo referencian → base del enriquecimiento por documento.

---

## 3. Lo que FALTA (gaps)

1. **🔴 El synthesizer no ve los documentos.**
   `synthesizer._build_user_prompt` solo arma el prompt con
   `verdict + blocking_failures + rule_results` (agrupados por `kind`).
   **No incluye `mapped_extraction` / `extraction`.** La salida "enriquecida" hoy
   no tiene acceso a los datos extraídos de cada documento. **(gap principal)**
2. **🔴 `input_hash` no considera `mapped_extraction`** (`synthesis_runner.py`).
   Si cambia la extracción pero no los rule_results, la caché no se invalida.
3. **🟡 Sin proyección determinística.** Todo se delega al LLM, incluso campos que
   son copia directa de un campo extraído (`@doctype.field`) → costo y alucinación
   innecesarios.
4. **🟡 `output_schema` no se deriva de `document_types.fields`**; si no está definido
   se usa `DEFAULT_OUTPUT_SCHEMA` genérico.
5. **🟡 `StaticLLMRunner` es el default del agente** (`synthesizer.py`). Confirmar que
   producción inyecta `build_synthesizer_agent()` (Agno) vía `bootstrap.py` y no el stub.
6. **🟡 Trazabilidad:** `document_refs` / `citations` no se proyectan dentro de
   `summary.output` para enlazar cada valor con su documento fuente.

---

## 4. Diseño propuesto

> **Decisiones tomadas** (ver §5): salida en **dos niveles** (por documento +
> agregada del case) con estrategia **híbrida** (determinística + LLM).

### 4.0 Dos niveles de salida

```
┌─────────────────────────────────────────────────────────────┐
│ CASE OUTPUT (agregado)   → WorkflowAnalysisRunSummary.output  │
│   conforma  workflow.output_schema                            │
│   combina: [doc outputs] + rule_results + verdict/signals     │
└─────────────────────────────────────────────────────────────┘
        ▲ agrega
┌───────┴──────────────────────────────────────────────────────┐
│ DOCUMENT OUTPUT (por documento) → WorkflowDocument.output(new) │
│   conforma  document_type.output_schema (o fields como base)   │
│   combina: mapped_extraction + rule_results con document_ref   │
└────────────────────────────────────────────────────────────────┘
```

- **Nivel documento:** un output estructurado por cada `WorkflowDocument`, que conforma
  un **schema propio del tipo de documento** (`DocumentType.output_schema`, campo nuevo —
  decisión §5.4) y enriquece `mapped_extraction` con los `WorkflowRuleResult` que lo
  referencian (`document_refs`). Se persiste en **campos nuevos** en `workflow_documents`:
  `output` (JSONB), `output_provenance` (JSONB, §4.5), `output_schema_version` (int, §4.6)
  — decisión §5.3.
- **Nivel case (agregado):** un único objeto que conforma `workflow.output_schema`,
  agregando los document outputs + verdict + signals. Se persiste en el ya existente
  `WorkflowAnalysisRunSummary.output`.
- **Disparo:** ambos niveles se generan en `complete_run` (decisión §5.8), cuando ya
  existen `mapped_extraction` **y** `rule_results`. Primero el output por documento,
  luego el agregado del case que lo consume.

### 4.1 Estrategia híbrida (determinística + LLM)

Cada propiedad del schema declara su **fuente** mediante una anotación
(`x-source`, JSON Schema extension keyword), que **reutiliza la sintaxis y el
resolutor de tokens que ya existen** para las reglas (ver §2.6):

```jsonc
{
  "type": "object",
  "properties": {
    "total":        { "type": "number", "x-source": "@invoice.total" },        // doc field
    "lines":        { "type": "array",  "x-source": "@invoice.items[].amount" },// array path
    "client_name":  { "type": "string", "x-source": "@invoice.client" },
    "decision":     { "type": "string", "x-source": "{{verdict}}" },            // system token
    "risk_summary": { "type": "string" }                                        // LLM (sin x-source)
  }
}
```

- **Paso 1 — proyección determinística:** los campos con `x-source` se resuelven
  con la infra existente (§2.6): `parse_doc_refs` → `DocRef` → `path_resolver.resolve`
  sobre `mapped_extraction`; tokens `{{...}}` contra un registry de sistema. Sin LLM.
- **Paso 2 — síntesis LLM:** solo los campos **sin** `x-source` (narrativos/derivados)
  se piden al LLM, pasándole los campos ya resueltos como contexto fijo.
- **Validación:** el objeto final (proyectado + LLM) se valida con `jsonschema`.
- Beneficio: valores anclados a la extracción real, menor costo, menos alucinación.

> ⚠️ **Sintaxis real (corrige supuestos previos):** la forma canónica es `@slug.path`
> (el `slug` es el del **DocumentType**; la forma con llaves `@{slug}.path` es alias).
> `path` admite anidación: `.key`, `[i]`, `[]` (itera). KB: `#kb_slug`. Tokens: `{{name}}`.

### 4.1.1 Referenciar outputs de reglas — `@rule.<slug>.field`
**Decisión (§5.5):** añadimos `WorkflowRule.slug` (único por workflow). Eso habilita una
4ª notación en `x-source`: `@rule.<rule_slug>.path`, que resuelve contra el `output` del
`WorkflowRuleResult` de esa regla en el run.

```jsonc
"approved": { "type": "boolean", "x-source": "@rule.credit-check.passed" }
```

- Requiere extender la gramática/resolutor (§2.6) con el prefijo `@rule.`; el resto de
  notaciones (`@slug.path`, `#kb`, `{{token}}`) se reutilizan tal cual.
- `slug` necesita: generación desde `name`, unicidad por `workflow_id`, backfill de
  reglas existentes (migración), y edición/validación en backoffice.
- Si una regla referenciada quedó `SKIPPED/FAILED` → el campo se resuelve a `null`
  (o se delega al LLM); ver edge cases §6.

### 4.2 Enriquecer la entrada del synthesizer
Cargar los `WorkflowDocument` del run (filtrados por tenant) y pasarlos al
`SynthesizerInput` como un bloque `documents`:

```
documents: [
  { document_id, document_type, mapped_extraction, validation, output }
]
```

- Cambios: `SynthesizerInput` (+ `documents`), `_build_user_prompt`,
  `SynthesisRunner.execute()` (cargar documentos), repos.

### 4.3 Invalidación de caché
Incluir un hash de `mapped_extraction` (y validation) en `compute_input_hash`,
tanto para el output de documento como para el agregado.

### 4.4 Schema por defecto derivado
Builder que arme el schema a partir de `document_types.fields` cuando no haya
`output_schema` definido (fallback mejor que el genérico).

### 4.5 Trazabilidad / provenance (decisión §5.7)
Por cada campo del output guardamos su **fuente**, usando el tipo canónico ya existente
`Citation` (`document_id`, `document_type_slug`, `field_path`, `value`, `sub_check_id`;
ver `domain/models/processing/citation.py`). Es casi idéntico a `ResolvedValue`, así que:

- **Campos determinísticos (`x-source`):** `ResolvedValue` → `Citation` (mapeo directo).
  Para `@rule.<slug>` la cita apunta a la regla (vía `sub_check_id`/result).
- **Campos LLM:** el agente **debe** emitir `citations` por campo (los rule kinds ya lo
  hacen); se persisten como provenance del campo.

Forma persistida (junto al `output`, en columna/clave hermana, p.ej. `output_provenance`):
```jsonc
{ "<json_pointer_del_campo>": [ Citation, ... ] }   // p.ej. "/total": [{document_id, field_path:"total", ...}]
```
Aplica a **ambos niveles** (doc y agregado). Habilita highlight en UI y auditoría.

### 4.6 Versionado del schema (decisión §5.9)
Versionado **explícito** además del snapshot:

- `Workflow.output_schema_version: int` y `DocumentType.output_schema_version: int`
  (se incrementan al editar el schema correspondiente).
- **Historial:** tabla(s) `*_output_schema_versions` (`entity_id`, `version`, `schema`,
  `created_at`, `created_by`) → permite auditoría y rollback.
- Cada output generado registra la **versión usada**: `WorkflowDocument.output_schema_version`
  y, a nivel agregado, el `output_schema_snapshot` (ya existente) + número de versión.
- El snapshot se conserva para reproducibilidad exacta aunque se borre/cambie una versión.

---

## 5. Decisiones

### Resueltas
1. **✅ Unidad de salida:** **ambas** — output por documento + output agregado del case.
2. **✅ Estrategia:** **híbrida** — proyección determinística (`x-source`) + LLM para
   campos narrativos. (ver §4.1)
4. **✅ Schema por documento:** **campo nuevo `DocumentType.output_schema`** (JSONB),
   editable en backoffice. Separa "qué se extrae" (`fields`) de "qué se entrega"
   (`output_schema`).
8. **✅ Disparo:** ambos niveles se generan en **`complete_run`**, cuando ya existen
   `mapped_extraction` y `rule_results`.
5. **✅ Ref a reglas:** añadir **`WorkflowRule.slug`** (único por workflow) → notación
   `@rule.<slug>.path` en `x-source`. (ver §4.1.1)
6. **✅ Docs en prompt LLM:** se inyectan **todos** los `mapped_extraction` del case
   (con guardas de tamaño en §6 si crece demasiado).

3. **✅ Persistencia output por doc:** columna nueva **`WorkflowDocument.output`** (JSONB),
   consistente con `extraction`/`mapped_extraction`. (ver §4.0)
7. **✅ Trazabilidad:** **provenance completo** por campo, usando el tipo canónico
   `Citation` (det vía `ResolvedValue`→`Citation`; LLM exige `citations`). (ver §4.5)
9. **✅ Versionado:** **explícito** — `output_schema_version` + historial. (ver §4.6)

### Abiertas
_(ninguna — todas las decisiones de diseño están cerradas; pendiente solo el detalle
de implementación por archivo en §7)_

---

## 6. Edge cases a considerar

- Reglas `FAILED / ERRORED / SKIPPED` y `scope.on_empty = SKIPPED`: un `@rule.<slug>.x`
  que apunte a una regla sin output → resolver a `null` o delegar al LLM (definir).
- `WorkflowRule.slug`: colisiones en el backfill desde `name`; unicidad por workflow;
  renombrar slug rompe `output_schema` que lo referencie (validar al guardar).
- `@rule.<slug>` cuando la regla corre sobre **múltiples** documentos (varios
  `WorkflowRuleResult` para esa regla en el run): ¿cuál output toma? (lista vs. error).
- `mapped_extraction = null` (mapeo falló) con `extraction` OK → fallback.
- Documentos sin `document_type_id` (bucket "Otros").
- **Multi-documento:** agregación vs. por-documento (ver decisión §5.1).
- **Tamaño de prompt:** muchos docs × `mapped_extraction` grande → exceder context
  window; necesita truncado/selección.
- LLM devuelve JSON que **valida pero inventa datos** no anclados a la extracción
  (mitigado por la capa híbrida §4.2).
- Coherencia del verdict (el verdict es final).
- Concurrencia/idempotencia: `force`, `regenerate_on_run_complete`, re-runs.
- Tenancy: filtrar `WorkflowDocument` por `tenant_id`.
- `output_schema` inválido o cambia entre runs (cubierto por snapshot + versión, §4.6).
- Campo LLM **sin** `citations` cuando el provenance las exige (§4.5) → ¿falla, warning,
  o se persiste sin traza? (definir).
- `output_provenance` con JSON Pointers a campos anidados/arrays (`/items/0/amount`):
  generación consistente de las claves.
- Bump de `output_schema_version` mientras hay runs en vuelo → el run usa el snapshot
  de su versión, no la nueva.

---

## 7. Plan de implementación (draft — pendiente de cerrar §5.3–5.9)

### Fase 0 — Proyección determinística (núcleo compartido)
1. Añadir `WorkflowRule.slug` (único por `workflow_id`): dominio/ORM/migración +
   backfill desde `name` + generación/validación en backoffice.
2. Extender resolutor (§2.6) con la notación `@rule.<slug>.path` (resuelve contra el
   `WorkflowRuleResult.output` del run). Reutilizar `@slug.path` / `#kb` / `{{token}}`.
3. Función `project_schema(schema, context) -> (resolved_fields, llm_fields)` donde
   `context` = {documents (`mapped_extraction`), rule_results by slug, system tokens}.

### Fase 1 — Schema, versionado y persistencia
3. `DocumentType.output_schema` (JSONB) + `output_schema_version` (int) y
   `Workflow.output_schema_version` (int) + tablas `*_output_schema_versions` (§4.6).
4. `WorkflowDocument`: columnas `output`, `output_provenance`, `output_schema_version` (§4.0/§4.5).
5. Dominio/ORM/builders/presenters para los campos nuevos; UI backoffice para editar
   `DocumentType.output_schema` (bump de versión + historial).

### Fase 2 — Output por documento
6. Use case `BuildDocumentOutput`: proyección determinística (`x-source`) +
   (opcional) LLM por documento; produce `output` + `output_provenance` (Citations, §4.5);
   valida con `jsonschema`; persiste con `output_schema_version`.
7. Invocado desde `complete_run`, por cada documento del run, antes del agregado (§5.8).

### Fase 3 — Output agregado del case
8. Cargar `WorkflowDocument`s (con su `output`) en `SynthesisRunner`; extender
   `SynthesizerInput` con `documents` (todos, §5.6) y actualizar `_build_user_prompt`.
9. Aplicar la misma capa híbrida + provenance al `workflow.output_schema`.
10. Extender `compute_input_hash` con `mapped_extraction` / document outputs / versión.

### Fase 4 — Soporte
11. Builder de schema por defecto desde `document_types.fields`.
12. Confirmar wiring del agente real (no `StaticLLMRunner`) en `bootstrap.py`.
13. Tests: unit (proyección + provenance + prompt), use case (mocked repos), e2e del run.
