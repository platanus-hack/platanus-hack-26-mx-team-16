---
feature: analysis-rules
type: spec
status: obsolete
coverage: 25
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

# Spec: Ejecución de Analysis Rules

Estado: **ready — listo para implementar**

---

## 1. Resumen

Este spec define el motor que ejecuta los `AnalysisRule`s de un workflow contra los datos extraídos de un `WorkflowCase` y persiste los resultados.

La evaluación de cada regla pasa por un pipeline multi-etapa (pre-evaluación determinística → reviewer LLM con tools → self-consistency N=5 → crítico cross-provider opcional → verificación post-hoc). El objetivo es **máxima precisión y trazabilidad, sin optimizar por costo en v1**.

El usuario dispara un análisis sobre un case desde la UI; el motor corre en background, transmite resultados en streaming via SSE, y al cerrar produce un `AnalysisRun` con N `AnalysisRuleResult`s persistidos.

---

## 2. Contexto del codebase actual

### 2.1 Document Types

Definidos en el backoffice, viven a nivel de workflow. Modelo (`src/common/domain/models/processing/document_type.py`):

| Campo              | Tipo         | Notas                                           |
| ------------------ | ------------ | ----------------------------------------------- |
| `uuid`             | UUID         |                                                 |
| `workflow_id`      | UUID         | scope                                           |
| `name`             | str          | "Cedula de Identidad"                           |
| `slug`             | str \| None  | usado por el clasificador (`"cedula"`)          |
| `description`      | str \| None  |                                                 |
| `fields`           | dict         | JSON Schema del documento                       |
| `validation_rules` | list[dict]   | reglas a nivel campo (no de cruce entre docs)   |
| `sample_file_id`   | UUID \| None |                                                 |

Los `validation_rules` ya se ejecutan dentro del pipeline de extracción y **no son parte de este spec**. Aquí solo nos interesan `fields` y `slug`.

### 2.2 Pipeline OCR, clasificación y extracción

Orquestado por Temporal (`DocumentProcessingWorkflow` en `src/workflows/presentation/workflows/document_processing.py`). Pasos:

1. `extract_text` (OCR vía Textract layout).
2. `classify_pages` — agrupa páginas y asigna un `slug` de `DocumentType`.
3. `persist_classified_documents` — crea N `WorkflowDocument` por archivo, vinculando cada uno a su `document_type_id`. Documentos cuyo slug no pertenece al workflow quedan con `document_type_id = NULL` (bucket "Otros").
4. `extract_fields` — extractor LLM contra el `fields` del DocumentType.
5. `validate_extraction` — corre los `validation_rules` por campo.

Resultado relevante: `WorkflowDocument.extraction` (dict con valores extraídos) y `WorkflowDocument.document_type_id`.

### 2.3 Analysis Rules (estado actual)

Modelo `AnalysisRule` (`src/common/domain/models/processing/analysis_rule.py`):

| Campo            | Tipo         | Notas                                      |
| ---------------- | ------------ | ------------------------------------------ |
| `uuid`           | UUID         |                                            |
| `workflow_id`    | UUID         | scope                                      |
| `name`           | str \| None  |                                            |
| `content`        | str          | plantilla del prompt (con tokens)          |
| `is_active`      | bool         | si false, se ignora                        |
| `kb_ids`         | list[UUID]   | docs de knowledge base                     |
| `output_enabled` | bool         | true → respuesta estructurada              |
| `output_schema`  | dict \| None | JSON Schema de la respuesta (si enabled)   |

CRUD ya existe (`presentation/endpoints/analysis_rule.py`, `application/analysis_rules/`). Las reglas **no** referencian `document_type_id` explícitamente: las referencias se inyectan en `content` como tokens.

Tokens soportados (resolver: `src/workflows/infrastructure/services/prompt/`):

- `@<slug>.<jmespath>` → valor extraído del `WorkflowDocument` cuyo `DocumentType.slug` matchea `slug`.
- `{{<system-var>}}` → `fecha-hoy`, `datetime-now`, etc.

El renderer existente produce `RenderedPrompt(text, unresolved_tokens)`. En este spec lo reusamos solo para el campo de auditoría (no como input del agente).

Las `AnalysisRule` solo existen en workflows con `workflow_type = "ANALYSIS"`.

---

## 3. Vista general del flujo

```
┌──────────────────────────┐
│ A. CREATE/EDIT RULE      │  Usuario guarda regla
│   → parser LLM corre     │  (Sonnet 4.6, una sola vez)
│   → AST cacheado en DB   │
└──────────────────────────┘
              │
              ▼
┌──────────────────────────┐
│ B. TRIGGER ANALYSIS      │  POST /analysis-runs
│   → validaciones         │  (case listo, no concurrencia, caps)
│   → crea AnalysisRun     │
└──────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────┐
│ C. PIPELINE (background task + SSE)              │
│                                                   │
│   Por cada regla activa:                          │
│     fan-out combinatorio (producto cartesiano)    │
│       Por cada combinación:                       │
│         Etapa 1: pre-evaluación determinística    │
│         Etapa 2: reviewer agent (Agno + tools)    │
│         Etapa 3: self-consistency N=5 paralelo    │
│         Etapa 4: crítico cross-provider (si 3/2) │
│         Etapa 5: verificación post-hoc            │
│         → persistir AnalysisRuleResult            │
│         → emit RULE_RESULT_READY (SSE)            │
└──────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────┐
│ D. READ RESULTS          │  GET /analysis-runs/{id}
│   → presenter            │  con citaciones, consensus,
│   → UI render            │  warnings, structured_output
└──────────────────────────┘
```

Las secciones 4-8 desarrollan cada paso en orden.

---

## 4. Paso A: Crear/editar una regla (parser cacheado)

El parser corre **una sola vez** por versión de la regla (al crear o al cambiar `content`). No está en el path crítico de la evaluación — su salida queda cacheada en la DB y la etapa 1 del pipeline simplemente la ejecuta.

### 4.1 Cambios al modelo `AnalysisRule`

Cinco campos nuevos:

| Campo                    | Tipo               | Notas                                                                          |
| ------------------------ | ------------------ | ------------------------------------------------------------------------------ |
| `parsed_checks`          | JSONB \| None      | AST de checks atómicos; `null` mientras el parser no haya corrido o si falló   |
| `previous_parsed_checks` | JSONB \| None      | AST anterior, guardado tras un re-parseo; permite rollback manual              |
| `parser_version`         | str \| None        | versión del parser usada; `null` mientras no haya corrido                      |
| `parsed_at`              | datetime \| None   | última vez que se parseó                                                       |
| `parser_error`           | str \| None        | si el parser falló; la etapa 1 se skipea y el reviewer asume toda la carga    |

Una regla con `parsed_checks=null` o `parser_error != null` sigue siendo **válida** para evaluación; solo pierde la pre-validación determinística.

### 4.2 Trigger del parser

`WorkflowRuleCreator` y `WorkflowRuleUpdater` encolan el `ParseAnalysisRule` use case como background task tras persistir. En `update`, si `content` no cambió, no se re-parsea.

### 4.3 Modelo LLM y schema de output

LLM call con structured output. Modelo default: **Claude Sonnet 4.6** (sweet spot — Opus es overkill para descomposición de reglas, Haiku misclasifica lógica compuesta).

Input al LLM:

- `rule.content` (texto crudo).
- Lista de `slug`s + `fields_schema` de los `DocumentType`s del workflow (para que entienda tipos: numéricos, fechas, strings, enums…).
- La taxonomía cerrada de tipos de check soportados — el LLM debe forzarse a clasificar dentro de ella.

Output (structured): `list[Check]` con el schema:

```jsonc
{
  "id": "check_1",
  "kind": "numeric_comparison" | "date_range" | "regex_match" | "field_exists" | "length_check" | "enum_check" | "subjective",
  "operands": { /* específico por kind, ver taxonomía; vacío para subjective */ },
  "natural_language": "el fragmento original que originó este check"
}
```

> El `type` (objective/subjective) se deriva del `kind`: cualquier kind distinto de `subjective` es objetivo. No se almacena por separado.

### 4.4 Taxonomía cerrada de checks objetivos

Solo estos seis kinds se ejecutan en código en la etapa 1. Cualquier cosa fuera → `subjective`.

| `kind`               | Operands                                                | Ejecución                                  |
| -------------------- | ------------------------------------------------------- | ------------------------------------------ |
| `numeric_comparison` | `{field, op: <\|<=\|==\|>=\|>, value}`                  | parse a float, comparar                    |
| `date_range`         | `{field, from, to}` (from/to soportan `{{system-vars}}`) | parse ISO/DD-MM-YYYY, comparar timestamps  |
| `regex_match`        | `{field, pattern, flags}`                               | `re.fullmatch`                             |
| `field_exists`       | `{field}`                                               | `field is not None and field != ""`        |
| `length_check`       | `{field, op, value}`                                    | `len(str(field)) op value`                 |
| `enum_check`         | `{field, allowed: [...]}`                               | `field in allowed`                         |

Cada `field` es un token `@<slug>.<jmespath>` resuelto en tiempo de etapa 1.

### 4.5 Failure modes del parser

- LLM call falla / timeout → `parser_error="llm_call_failed"`, `parsed_checks=null`.
- LLM devuelve JSON inválido → `parser_error="invalid_output"`.
- Schema validation post-LLM falla → `parser_error="schema_mismatch"`.
- Cualquier otro error → `parser_error="<excepción>"`.

En todos los casos la regla sigue siendo válida para evaluación.

### 4.6 UX en el editor de reglas

Tras guardar, la UI consulta el endpoint `GET` de la regla y muestra la descomposición:

```
Tu regla fue interpretada como:

✓ Check objetivo · numeric_comparison: monto_total > 100
✓ Check objetivo · date_range: fecha_emision en últimos 3 meses
○ Check subjetivo: similitud de titular vs nombres de cédula  → delegado al reviewer
```

Si `parser_error != null`, banner amarillo: "No pudimos descomponer tu regla automáticamente — el análisis correrá igual, pero sin pre-validación determinística."

El usuario puede editar y re-guardar para forzar re-parseo.

### 4.7 Re-parseo al bumpear `PARSER_VERSION` (estrategia lazy)

- Cualquier acceso a una regla con `parser_version != PARSER_VERSION_ACTUAL` (lectura, edición, o evaluación en un `AnalysisRun`) dispara un re-parseo en background. El acceso retorna el AST viejo si la operación no puede esperar; el siguiente acceso ya verá el nuevo.
- Antes de sobrescribir, el `parsed_checks` actual se mueve a `previous_parsed_checks` para rollback manual.
- Para forzar re-parseo masivo: `python backend/scripts/reparse_rules.py [--tenant <uuid>] [--workflow <uuid>]`.
- **Race con runs en curso:** si `PARSER_VERSION` bumpea mientras hay un `AnalysisRun` activo, el run **continúa con el AST viejo hasta terminar**. No se interrumpe. El próximo run ya usará el AST nuevo.

---

## 5. Paso B: Disparar un análisis

### 5.1 Endpoints

| Método | Ruta                                                           | Propósito                                       |
| ------ | -------------------------------------------------------------- | ----------------------------------------------- |
| POST   | `/v1/workflows/{workflow_id}/cases/{case_id}/analysis-runs`    | Crear y disparar un nuevo `AnalysisRun`         |
| GET    | `/v1/workflows/{workflow_id}/cases/{case_id}/analysis-runs`    | Listar runs del case (más reciente primero)     |
| GET    | `/v1/analysis-runs/{run_id}`                                   | Detalle del run + sus `AnalysisRuleResult`s     |
| GET    | `/v1/analysis-runs/{run_id}/events`                            | SSE stream de eventos del run en vivo           |
| POST   | `/v1/analysis-runs/{run_id}/cancel`                            | Cancelar un run en curso                        |

`POST /analysis-runs` devuelve `202 Accepted` con el `AnalysisRun` recién creado en `status=RUNNING`. La UI debería abrir inmediatamente la conexión SSE a `/events`.

Cada disparo crea un `AnalysisRun` nuevo (histórico — no sobrescribe runs previos).

### 5.2 Validaciones de entrada

Toda falla devuelve `4xx` antes de crear el run:

- Workflow es de tipo `ANALYSIS`; case existe y pertenece al workflow.
- Workflow tiene al menos una `AnalysisRule` activa.
- **Sin concurrencia:** no hay otro `AnalysisRun` con `status` en (`RUNNING`, `CANCELING`) para el mismo `case_id` → `409 Conflict`, `code="analysis_already_running"`.
- **Extracción terminada:** todos los `WorkflowDocument` del case han terminado extracción (ninguno en `PROCESSING`/`EMPTY` pendiente) → `409 Conflict`, `code="extraction_in_progress"`, mensaje: "Espera a que termine la extracción de los documentos antes de iniciar el análisis."
- **Caps de combinaciones** (ver siguiente sección).

### 5.3 Cap de combinaciones (safety)

Sin límite, un case con 5×5×5 docs son 125 evaluaciones por regla; con 10 reglas → 1250 LLM calls del reviewer (más self-consistency × 5). Para evitar runs descontrolados:

- **Cap por regla:** 25 combinaciones. Si una regla excede, `400` con `code="rule_combinations_exceeded"`.
- **Cap global por run:** 200 combinaciones sumando todas las reglas activas. Si excede, `400` con `code="run_combinations_exceeded"`.

Ambos son hardcoded como constantes; se moverán a `tenant_settings` cuando aparezca el primer cliente con necesidades distintas. Mensaje al usuario: "Este case tiene demasiadas combinaciones — reduce los documentos o ajusta la regla."

### 5.4 Modelo nuevo: `AnalysisRun`

Tabla nueva `analysis_runs`. Una corrida agrupa todos los `AnalysisRuleResult`s producidos en un disparo.

| Campo          | Tipo                                                  | Notas                                              |
| -------------- | ----------------------------------------------------- | -------------------------------------------------- |
| `uuid`         | UUID                                                  |                                                    |
| `tenant_id`    | UUID                                                  |                                                    |
| `workflow_id`  | UUID                                                  |                                                    |
| `case_id`      | UUID                                                  |                                                    |
| `status`       | enum (`RUNNING/COMPLETED/FAILED/CANCELING/CANCELED`)  | nace en `RUNNING`                                  |
| `triggered_by` | UUID \| None                                          | user                                               |
| `started_at`   | datetime                                              |                                                    |
| `completed_at` | datetime \| None                                      |                                                    |
| `error`        | str \| None                                           | solo para fallos de orquestación; los errores por evaluación viven en `AnalysisRuleResult.error` |

---

## 6. Paso C: Pipeline de evaluación

### 6.1 Vista alto nivel

Tras crear el `AnalysisRun`, el background task ejecuta:

1. Cargar contexto: reglas activas, `WorkflowDocument`s del case con `extraction`, `DocumentType`s del workflow.
2. Por cada regla: extraer slugs únicos del `content` (regex sobre tokens `@<slug>.<…>`, **no confundir con el parser LLM** que produce `parsed_checks`) → generar combinaciones (producto cartesiano).
3. Por cada combinación: ejecutar el pipeline de 5 etapas (sec. 6.3) y persistir el `AnalysisRuleResult` apenas termine.
4. Cerrar `AnalysisRun` con `status=COMPLETED` y `completed_at`. Si todo falla, `FAILED` + `error`.

> El `AnalysisRunner` actual (`src/workflows/infrastructure/services/analysis_runner.py`) es un stub. Este spec lo reemplaza.

### 6.2 Fan-out combinatorio (1 regla → N resultados)

Una regla genera un `AnalysisRuleResult` por cada combinación de instancias de los doc-types que referencia.

**Algoritmo:**

1. Parsear `rule.content` para extraer slugs únicos (`@<slug>.<…>`).
2. Para cada slug, listar los `WorkflowDocument` del case con `DocumentType.slug == slug`.
3. Generar el producto cartesiano. Cada elemento es una "combinación" — un mapping `{slug: WorkflowDocument}`.
4. Por cada combinación, ejecutar las 5 etapas y persistir un `AnalysisRuleResult` con `document_refs` apuntando a los doc IDs.

**Ejemplo:**

- Workflow: `cedula`, `comprobante`, `factura`.
- Case: 3 cédulas, 1 comprobante, 2 facturas.
- Regla menciona los 3 slugs → `3 × 1 × 2 = 6` evaluaciones → 6 `AnalysisRuleResult`s, cada uno con `document_refs` distinto.

**Casos especiales:**

- Regla menciona slugs no presentes en el case (0 docs): la combinatoria sigue, sustituyendo esa dimensión por un placeholder. `document_refs` queda con `{slug: None}`; el structured context para ese slug llega como `null` al agente; el `rendered_prompt` interpola los tokens de ese slug como `""`. **1 evaluación por dimensión faltante** (no 0).
- Regla sin tokens `@…` (solo `{{system-vars}}` o texto fijo): 1 evaluación, `document_refs = {}`.

### 6.3 Las 5 etapas por combinación

El objetivo es **máxima precisión y trazabilidad**, no costo.

#### Etapa 1 — Pre-evaluación determinística (sin LLM)

Solo ejecuta el AST cacheado en `rule.parsed_checks`. **No parsea nada en tiempo de evaluación.**

Por cada check del AST:

- **Objetivos** (`numeric_comparison`, `date_range`, `regex_match`, `field_exists`, `length_check`, `enum_check`): se evalúan contra el `extraction` de los docs de la combinación y producen evidencia: `{check_id, kind, result, passed, evidence}`.
- **Subjetivos**: se marcan como "delegado al reviewer" sin ejecución.

Output: `preliminary_checks` con la lista completa.

Si la regla no tiene `parsed_checks` (parser falló o aún no corrió), la etapa se skipea: `preliminary_checks = {"skipped": true, "reason": "parser_unavailable"}`. El reviewer asume toda la carga.

#### Etapa 2 — Reviewer agent (Agno con tools)

Un `AgnoAgentReviewer` configurado por combinación (de éste se lanzan N=5 instancias paralelas en la etapa 3). Cada instancia recibe:

- **Regla original** (no interpolada — el agente ve los tokens `@cedula.x` y los puede resolver via tools si necesita).
- **Tools disponibles:**
  - `get_document(slug, idx?)` → dict con `extraction` completa.
  - `get_field(slug, jmespath_expr)` → valor específico.
  - `get_raw_ocr(slug)` → `extracted_text` crudo (re-verificación si la extracción perdió algo).
  - `python_exec(code)` → sandbox **RestrictedPython**, stdlib limitada a `re` y `datetime`, timeout 2s, **one-shot** (sin estado persistente entre calls).
  - `current_datetime()` → fecha/hora actual.
  - `kb_search(query)` → retrieval acotado a `rule.kb_ids`. `top_k=10`, similarity threshold `0.85`. El agente decide cuándo invocarlo.
- **Contexto estructurado** (system prompt): JSON con `{slug: {fields_schema, extraction}}` por cada doc de la combinación, más los `preliminary_checks` de la etapa 1.
- **`output_schema`** si `rule.output_enabled` (forzar response_format JSON).

**Requisito duro: citaciones.** El agente debe emitir `citations` con `{claim, document_id, field_path}` por cada afirmación de su `reasoning` que aporte un dato (la prosa conectiva tipo "por lo tanto" no requiere cita). Reglas:

- `field_path` debe ser el nombre exacto de un campo del `extraction` del `document_id` correspondiente.
- Si el agente afirma "campo ausente / vacío", la cita es **negativa**: `{claim: "field_absent", document_id, field_path}`. Se valida que el `field_path` exista en el `fields_schema` del DocumentType pero esté `null` o vacío en el `extraction`.
- No se aceptan citas a `extracted_text` (OCR crudo) — solo a campos estructurados.

Validación programática post-respuesta. Si falla, se re-promptea (máx 2 retries; al tercero el resultado queda con `error="missing_citations"` y se persiste igual).

#### Etapa 3 — Self-consistency (N=5 en paralelo)

La etapa 2 corre **5 veces en paralelo** con temperatura > 0 (default `0.4`).

Persiste `consensus = {n_samples, agreement_ratio, verdicts: [bool | null, ...]}` — un slot por sample. `null` aparece cuando un reviewer no logró concluir (e.g., `error="missing_citations"`, schema mismatch, timeout).

**Resolución del verdict final:**

- **Mayoría binaria clara** (5/0, 4/1 sobre samples no-null): se cierra con la mayoría.
- **3/2 sobre samples no-null:** escala a etapa 4.
- **≥3 nulls:** muestra inconcluyente — `error="no_consensus"`, `is_passed=null`, persiste el reasoning más completo de los samples válidos.
- **Mix con nulls que no permite mayoría** (e.g., 2 true / 2 false / 1 null): se trata como 3/2 → escala a etapa 4.

#### Etapa 4 — Critic agent (cross-provider, opcional)

Solo se invoca si la etapa 3 dio 3/2 (o equivalente). Usa un **modelo distinto** al reviewer (default: reviewer = Claude Opus 4.7, critic = Gemini 2.5 Pro). Recibe:

- Regla original.
- Reasoning + verdict mayoritario del reviewer.
- Mismo contexto estructurado que el reviewer.

Tarea: identificar afirmaciones no soportadas, alucinaciones, edge cases ignorados. Devuelve `{verdict_agreement: bool, feedback: str, severity: low|medium|high}`.

- Si `severity=high` → se ejecuta **una sola corrida nueva del reviewer** (no se repite la self-consistency completa) con el `critic_feedback` inyectado al system prompt. El verdict de esa corrida sobrescribe `is_passed` y `reasoning` del resultado. Máx 2 iteraciones reviewer↔critic.
- Si `severity=low|medium` (sin importar `verdict_agreement`) → se persiste el verdict del reviewer y `critic_feedback` queda en el resultado para que la UI lo muestre como warning.

> **`consensus` es inmutable tras la etapa 3.** Aunque el rerun de etapa 4 cambie `is_passed`, `consensus` mantiene los 5 verdicts originales para auditoría. La señal de intervención del crítico es `critic_iterations > 0`.

#### Etapa 5 — Verificación post-hoc determinística

Si `rule.output_enabled = true`:

- Validar `structured_output` contra `output_schema` (JSON Schema validator). Falla → `error="schema_mismatch"` y el JSON crudo se guarda igual en `structured_output` para inspección.
- **Cross-check con datos crudos:** si el agente afirma `fecha_emision = "2024-03-15"` pero la `extraction` original dice `"2024-05-13"`, se agrega `verification_warnings: ["fecha_emision: agente reportó 2024-03-15, extracción dice 2024-05-13"]`. La regla NO falla automáticamente — los warnings son señales para el humano.

Si `rule.output_enabled = false`, esta etapa solo valida que las `citations` apunten a `document_id`s que están en `document_refs` (sanity check). Excepción: cuando `document_refs` tiene `{slug: None}` (slug sin docs en el case), las citaciones para ese slug deben usar `document_id: null` y `claim: "field_absent"` — la validación lo permite explícitamente.

### 6.4 Modelo `AnalysisRuleResult` (ajustes)

| Campo                   | Tipo                          | Notas                                                                              |
| ----------------------- | ----------------------------- | ---------------------------------------------------------------------------------- |
| `analysis_run_id`       | UUID **(nuevo)**              | FK al `AnalysisRun`                                                                |
| `rule_id`               | UUID                          | FK a `AnalysisRule`                                                                |
| `is_passed`             | bool \| None                  | verdict final (mayoría del consenso, sobrescrito por etapa 4 si aplica)            |
| `reasoning`             | str \| None                   | razonamiento de la mayoría                                                         |
| `structured_output`     | dict \| None                  | **renombrar** el campo actual `structured_data` → `structured_output`              |
| `rendered_prompt`       | str **(nuevo)**               | template interpolado — solo auditoría humana, no es input del agente               |
| `document_refs`         | dict **(nuevo)**              | `{slug: workflow_document_id}` de la combinación                                   |
| `citations`             | list[dict] **(nuevo)**        | `[{claim, document_id, field_path}]` validadas                                     |
| `preliminary_checks`    | dict **(nuevo)**              | salida de la etapa 1 determinística                                                |
| `consensus`             | dict **(nuevo)**              | `{n_samples, agreement_ratio, verdicts: [bool | null]}` de la self-consistency     |
| `critic_feedback`       | str \| None **(nuevo)**       | output del crítico si la etapa 4 corrió                                            |
| `critic_iterations`     | int **(nuevo)**               | 0 si no se necesitó crítico                                                        |
| `verification_warnings` | list[str] **(nuevo)**         | discrepancias detectadas en la etapa 5                                             |
| `unresolved_tokens`     | list[str] **(nuevo)**         | tokens que el renderer no pudo resolver al producir `rendered_prompt`              |
| `error`                 | str \| None                   |                                                                                    |

Reglas de llenado:

- `output_enabled = false` → `structured_output = NULL`. Resultado interpretado solo con `is_passed` + `reasoning`.
- `output_enabled = true` → JSON conforme a `output_schema` en `structured_output`. Schema mismatch → `error="schema_mismatch"` y JSON crudo persistido igual.

### 6.5 Tolerancia a fallos (best effort)

Una corrida típica genera decenas de evaluaciones; algunas pueden fallar aisladamente (timeout LLM, schema mismatch, error de red). El run **no falla globalmente** por una evaluación caída.

- Cada evaluación caída persiste un `AnalysisRuleResult` con `is_passed=null`, `error="<causa>"`.
- Las que terminaron quedan persistidas con sus datos.
- El `AnalysisRun` cierra en `status=COMPLETED` y la UI distingue resultados con `error != null` con un badge de warning.
- El run se marca `FAILED` solo si **todas** las evaluaciones fallan o si hay un error a nivel de orquestación (e.g., no se pudieron cargar los docs del case).

### 6.6 Configuración LLM por workflow

Tres campos nuevos en `Workflow`:

| Campo                         | Default              | Notas                                                |
| ----------------------------- | -------------------- | ---------------------------------------------------- |
| `analysis_reviewer_model`     | `claude-opus-4-7`    | Etapas 2-3, con thinking habilitado                  |
| `analysis_critic_model`       | `gemini-2.5-pro`     | Etapa 4 — debe ser de proveedor distinto al reviewer |
| `analysis_consensus_samples`  | `5`                  | Rango permitido: 3-9 (impar)                         |

Migración: tres ALTER TABLE a `workflows`, los tres nullable con defaults aplicados a nivel código (no DB) para que se pueda override por workflow.

### 6.7 Configuración de Agno

- **Structured output** (cuando `rule.output_enabled = true`): vía `response_format=json_schema` nativo del SDK Agno.
- **Tools**: registradas con el decorator `@tool`.
- **Multi-sample (etapa 3, N=5 paralelo)**: usar primitiva nativa de Agno si existe; si no, orquestar con `asyncio.gather()` lanzando N `Agent.arun()` independientes.
- **Cross-provider en el mismo `Team`**: confirmado soportado.
- **Thinking budget (Anthropic extended thinking)**: usar parámetro nativo de Agno si está expuesto. Si no, no es bloqueante para v1.

### 6.8 Tipo de ejecución

Background task vía `FastAPI BackgroundTasks` (mismo patrón que el extraction starter). No se usa Temporal en v1.

> **Riesgo conocido:** `BackgroundTasks` corre en el mismo proceso del worker FastAPI. Un restart/crash del worker (deploy, OOM) durante un run lo deja huérfano: `status=RUNNING` sin proceso activo. **Mitigación v1:** un job/cron que marca como `FAILED` runs en `RUNNING`/`CANCELING` cuyo `started_at` excede un umbral razonable (e.g., 30 min). Reintento manual desde la UI. Migración a una cola real (ARQ/Celery) o Temporal queda para v2.

---

## 7. Paso D: Streaming en vivo y cancelación

### 7.1 Eventos SSE

Mismo patrón que el extractor (`src/workflows/presentation/endpoints/case_events_endpoint.py`). El background task publica eventos a Redis y `GET /v1/analysis-runs/{run_id}/events` los emite al cliente.

| Tipo                  | Payload                                                                       |
| --------------------- | ----------------------------------------------------------------------------- |
| `RUN_STARTED`         | `{ runId, totalEvaluations }`                                                 |
| `EVALUATION_STARTED`  | `{ ruleId, combinationKey }`                                                  |
| `STAGE_PROGRESS`      | `{ ruleId, combinationKey, stage: 1\|2\|3\|4\|5, status }`                    |
| `RULE_RESULT_READY`   | `AnalysisRuleResult` completo (presenter dict)                                |
| `RUN_PROGRESS`        | `{ completed, total }` — barra de progreso global                             |
| `RUN_COMPLETED`       | `{ runId, completedAt, summary }`                                             |
| `RUN_FAILED`          | `{ runId, error }`                                                            |
| `RUN_CANCELED`        | `{ runId, canceledAt, reason }`                                               |

**Definiciones:**

- **`combinationKey`**: hash estable derivado de `{ruleId, document_refs}` (e.g., `sha1` de su JSON canonicalizado). Permite a la UI correlacionar eventos antes de que llegue el `uuid` del resultado persistido.
- **`summary`**: `{ passed: int, failed: int, errored: int }` donde `passed = is_passed=true`, `failed = is_passed=false`, `errored = error != null` (incluye `is_passed=null`).
- **`stage.status`**: `"started"` | `"completed"` | `"skipped"` | `"failed"`.

Cada evento lleva `seq` autoincremental y `timestamp` (mismo `CaseEvent` pattern).

### 7.2 Cancelación

`POST /v1/analysis-runs/{run_id}/cancel` marca `status=CANCELING` en DB. El background task verifica el flag entre combinaciones y entre etapas; al detectarlo termina con `status=CANCELED`.

- Combinaciones ya terminadas → persistidas con su `AnalysisRuleResult`.
- Combinación en vuelo → se deja terminar la **etapa actual** (el `asyncio.gather` de los samples de etapa 3 termina, o la corrida actual del crítico termina). No se intenta matar LLM calls en curso.
- Combinaciones aún no iniciadas → no se ejecutan; no producen `AnalysisRuleResult`.

Se emite `RUN_CANCELED` por SSE al cierre.

---

## 8. Paso E: Leer resultados

### 8.1 Endpoints de lectura

Definidos en la sección 5.1: `GET .../analysis-runs` (lista) y `GET /analysis-runs/{run_id}` (detalle con sus results).

### 8.2 Estructura del presenter

Por cada `AnalysisRuleResult`:

```jsonc
{
  "uuid": "…",
  "ruleId": "…",
  "ruleName": "Verificar mayor de edad",
  "ruleContent": "Verificar que @cedula.fecha_nacimiento sea mayor a 18 años respecto a {{datetime-now}}",
  "renderedPrompt": "Verificar que 1990-05-12 sea mayor a 18 años respecto a 2026-05-01T…",
  "documentRefs": { "cedula": "<workflow_document_uuid>" },
  "isPassed": true,
  "reasoning": "La cédula indica fecha de nacimiento 1990-05-12, hoy es 2026-05-01, han transcurrido ~36 años, por lo tanto es mayor de edad.",
  "citations": [
    { "claim": "fecha de nacimiento 1990-05-12", "documentId": "…", "fieldPath": "fecha_nacimiento" }
  ],
  "preliminaryChecks": {
    "date_diff_years": { "type": "objective", "result": 36, "passed": true }
  },
  "consensus": { "nSamples": 5, "agreementRatio": 1.0, "verdicts": [true, true, true, true, true] },
  "criticFeedback": null,
  "criticIterations": 0,
  "verificationWarnings": [],
  "unresolvedTokens": [],
  "structuredOutput": null,
  "error": null,
  "createdAt": "…"
}
```

### 8.3 Notas para la UI

- **Agrupación por regla**: cuando una regla generó N resultados (fan-out), agrupar por `ruleId` y etiquetar cada uno con los nombres de los docs en `documentRefs`.
- **Confianza visual**: badge combinando `consensus.agreementRatio` y `criticIterations`:
  - `criticIterations > 0` → "revisión del crítico" (mostrar `criticFeedback`), independientemente del ratio.
  - `agreementRatio == 1.0` → "alta confianza".
  - `agreementRatio == 0.8` → "confianza media".
  - `agreementRatio < 0.8` (sólo si `error="no_consensus"`) → "inconcluyente".
- **Citaciones clickeables**: cada item de `citations` enlaza al `WorkflowDocument` y resalta el campo.
- **Warnings de verificación**: si `verificationWarnings` no está vacío, banner amarillo con la lista.
- **Output estructurado**: si `rule.output_enabled = true`, pintar `structuredOutput` con el `output_schema` (form auto-generado). Si `false`, sólo `isPassed` + `reasoning` + `citations`.
- **Panel de auditoría**: `renderedPrompt`, `preliminaryChecks` y los 5 `verdicts` del consensus se muestran en un panel "ver detalle / debug" para forensics.

> `rendered_prompt` se persiste para auditoría humana, **no es input del agente**. El agente recibe la regla original + structured context.

---

## 9. Edge cases

### 9.1 Múltiples `WorkflowDocument` con el mismo `document_type`

Resuelto por el fan-out combinatorio (sec. 6.2). Una regla genera un `AnalysisRuleResult` por cada combinación; el conteo total de LLM calls del reviewer es `combinaciones × consensus_samples` (más eventuales corridas extra del crítico).

### 9.2 Case con docs pero ninguno categorizado dentro del workflow

(todos sus `WorkflowDocument.document_type_id` son `NULL` — bucket "Otros".)

El `AnalysisRun` se crea y queda en `status=COMPLETED` pero sin `AnalysisRuleResult`s; el run lleva un `error` informativo (`"no_classified_documents"`) y la UI muestra "no aplica".

### 9.3 Una `AnalysisRule` referencia tokens que no resuelven

Causas posibles: el slug no existe como `DocumentType` en el workflow, el campo no existe en el `extraction`, o el JMESPath devuelve vacío.

Como el agente recibe la regla original + structured context (no la plantilla interpolada), ve directamente que un campo está ausente o que un slug no tiene docs. No necesita un placeholder.

- **Para el `rendered_prompt`** (auditoría): el renderer interpola tokens irresolubles como `""` (string vacío entre comillas). Este texto **no** se le pasa al agente.
- **Para el agente**: el structured context para ese slug llega como `null`; sus tools devuelven `null`; el agente decide si la regla falla o si infiere desde otras fuentes (e.g., `get_raw_ocr`).
- **`citations`** sigue siendo obligatoria: si afirma "el campo no está presente", debe citar el `document_id` y el `field_path` que verificó (cita negativa).

**Combinación con el fan-out**: si una regla referencia un slug con 0 docs, esa dimensión del producto cartesiano genera 1 entrada con `{slug: None}` en `document_refs`; el agente reporta el campo faltante con citación al placeholder.

---

## 10. Decisiones tomadas (referencia)

| #  | Tema                          | Decisión                                                                              |
| -- | ----------------------------- | ------------------------------------------------------------------------------------- |
| 1  | Endpoint                      | Per-case, RESTful (`POST .../analysis-runs`)                                          |
| 2  | Fan-out                       | Producto cartesiano de instancias por slug referenciado                               |
| 3  | Tokens irresolubles           | Agente ve structured context (no placeholder); `rendered_prompt` usa `""` solo audit  |
| 4  | Output estructurado           | `structured_output` (rename de `structured_data`); solo se llena si `output_enabled`  |
| 5  | Cap combinaciones             | 25 por regla, 200 por run (hardcoded por ahora)                                       |
| 6  | Fallos parciales              | Best effort: el run queda `COMPLETED` con resultados marcados con `error` individual  |
| 7  | Arquitectura de evaluación    | Multi-etapa (5 etapas) con self-consistency + cross-provider critic                   |
| 8  | Modelos LLM                   | `analysis_reviewer_model` (Claude Opus 4.7), `analysis_critic_model` (Gemini 2.5 Pro) |
| 9  | Self-consistency              | N=5 muestras paralelas, mayoría simple para `is_passed`                               |
| 10 | Citaciones                    | Obligatorias: cada afirmación cita `(document_id, field_path)`; validación programática |
| 11 | Parser de reglas              | LLM call (Sonnet 4.6) al crear/editar, AST cacheado en `parsed_checks`                |
| 12 | Taxonomía objetivos           | Cerrada: 6 kinds (`numeric_comparison`, `date_range`, `regex_match`, `field_exists`, `length_check`, `enum_check`) |
| 13 | Re-ejecución                  | Cada disparo crea un `AnalysisRun` nuevo (histórico)                                  |
| 14 | Streaming                     | SSE desde v1, con eventos por etapa                                                   |
| 15 | Cancelación                   | `POST /analysis-runs/{id}/cancel`, flag `CANCELING` → `CANCELED`                      |
| 16 | Concurrencia                  | Un solo `AnalysisRun` activo por case — segundo disparo devuelve `409 Conflict`       |
| 17 | Pre-condición de extracción   | Bloquear disparo si algún doc del case está aún en extracción (`409 Conflict`)        |
| 18 | Sandbox `python_exec`         | RestrictedPython, stdlib `re` + `datetime`, timeout 2s, one-shot                      |
| 19 | Validador de citaciones       | Cita exacta a campo del `extraction`; cita negativa para campos ausentes; retry máx 2x |
| 20 | Agno config                   | Structured output nativo, tools `@tool`, multi-sample nativo si existe (sino `asyncio.gather`), cross-provider en mismo Team |
| 21 | KB retrieval                  | Scope a `rule.kb_ids`, `top_k=10`, threshold `0.85`, agente decide cuándo invocar     |
| 22 | Re-parseo de reglas           | Lazy en cada acceso + script `backend/scripts/reparse_rules.py` para forzar masivo; runs activos siguen con AST viejo; rollback via `previous_parsed_checks` |

---

## 11. Pendientes para resolver al implementar

- Confirmar en docs de Agno: API exacta para multi-sample paralelo y para extended thinking de Anthropic (si no existe, fallback ya documentado).
- Definir `PARSER_VERSION` inicial (probablemente `"1.0.0"`) y formato de bump (semver vs entero).
