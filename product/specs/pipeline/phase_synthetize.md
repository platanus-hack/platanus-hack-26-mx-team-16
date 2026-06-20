---
feature: pipeline
type: spec
status: partial
coverage: 55
audited: 2026-06-16
---

# Phase `SYNTHESIZE` — Modelo extendido

> Sub-spec de la fase `SYNTHESIZE` del pipeline (ver `general.md`). Define el **modelo target** del synthesizer:
> el contrato `output_schema` con el cliente, el sistema de **mapeo declarativo** que permite proyección
> determinística sin LLM, el rol minoritario (pero importante) del LLM para narrativa, el ciclo de
> resíntesis sin re-evaluar, y la política de caché y errores.
>
> Idea central que guía todas las decisiones: **la síntesis es mayormente transformación de datos, no
> generación de datos**. La extracción y el juicio ya ocurrieron en `PROCESSING` y `EVALUATE`; aquí solo
> se reordena lo que ya está, en el shape que el cliente quiere consumir.

> **Convención del documento:** las decisiones marcadas **(hoy)** ya están en el código. Las marcadas **(target)**
> son cambios propuestos sobre lo existente. La sección §11 lista todos los deltas en una sola tabla.

---

## 1. Alcance

**Cubre:**
- Contrato `Workflow.output_schema` (JSON Schema configurable, con default).
- Sistema de mapeo declarativo (`x-source`) que permite rellenar fields sin invocar al LLM.
- Mini-pipeline interno del synthesizer (5 etapas, mayoría sin LLM).
- Generación de narrativa textual cuando el schema lo requiere.
- Resíntesis (re-correr SYNTHESIZE sin re-evaluar reglas).
- Caching por hash de inputs + schema.
- Errores, degradación y soft-fail.

**Fuera de alcance** (vive en otros specs):
- Pipeline macro (`general.md`).
- Fase `EVALUATE` (`phase_evaluate.md`).
- Editor del `output_schema` y UX de configuración (`create-rules.md` / spec del backoffice del workflow).
- Presentación del output al cliente (`analysis-exec-report.md`).
- Streaming SSE de la síntesis en progreso (sub-spec de SSE endpoints).

---

## 2. Principios de diseño

1. **La síntesis es transformación pura.** Mismos inputs → mismo output. La estocasticidad del LLM se mitiga con caché determinística por hash de inputs y, cuando hay LLM, con seed fijo + temperature baja.
2. **Schema-driven, no prompt-driven.** El `output_schema` del workflow es el contrato con el cliente. La síntesis es servidumbre del schema, no al revés. Cambiar el schema cambia el output sin re-tocar reglas.
3. **Mapeo declarativo > LLM siempre que se pueda.** Los fields cuya fuente está clara (un signal específico, un enrichment_block, una extraction) se llenan **sin LLM** vía annotations en el schema. El LLM se reserva para narrativa y para fields semánticamente complejos.
4. **Citations propagables.** Cada field del output puede heredar las citations del signal/block/extraction que lo originó. La trazabilidad llega al cliente sin trabajo extra del usuario.
5. **Soft-fail.** Si SYNTHESIZE crashea o el LLM falla, el cliente sigue pudiendo leer el summary crudo (`verdict`, `signals`, `enrichment_blocks`). El run no se marca como FAILED por culpa de la síntesis.
6. **Resíntesis sin re-evaluación.** Cambiar el `output_schema` (por ej. el cliente pide nuevo formato) **no** debe disparar re-evaluación de reglas. Solo re-corre SYNTHESIZE con el summary existente.
7. **Cacheable por hash.** `(summary_hash, output_schema_version, locale, synthesizer.name)` es la clave de caché. Idénticos inputs producen idéntico output sin re-procesar.
8. **Narrativa opcional, locale-aware.** La narrativa es un field más del schema (en el default está presente; los custom pueden omitirla). El idioma viene de `Workflow.output_locale`.

---

## 3. El `output_schema` — contrato con el cliente

### 3.1 Modelo (target)

```python
class Workflow:
    output_schema: dict | None       # JSON Schema. NULL → se usa el default
    output_locale: str = "es"        # ISO 639-1 — idioma de la narrativa
    output_schema_version: int       # incrementa con cada edición → invalida caché de síntesis
```

> **No hay `synthesis_enabled`.** SYNTHESIZE siempre corre — fue decisión de `general.md`. Si el cliente solo quiere el summary crudo, lo lee directo de la API (`synthesis_status` permite distinguir si la síntesis terminó OK, degraded, o erred — ver §10). Si en algún momento hace falta una válvula operacional para apagar la síntesis (incidente con un proveedor LLM, A/B), va como **feature flag de plataforma** (no como config del workflow), porque es decisión de operaciones, no de modelado del workflow.

### 3.2 Default schema (cuando `output_schema=NULL`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["verdict", "signals", "narrative"],
  "properties": {
    "verdict": {
      "enum": ["PASS", "REVIEW", "FAIL", null],
      "x-source": "$.summary.verdict"
    },
    "confidence_score": {
      "type": "number", "minimum": 0, "maximum": 1,
      "x-source": "$.summary.confidence_score"
    },
    "signals": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "rule_label": { "type": "string" },
          "polarity":   { "enum": ["PASS", "FAIL", "NEUTRAL"] },
          "severity":   { "enum": ["BLOCKER", "MAJOR", "MINOR", "INFO"] },
          "detail":     { "type": "object" },
          "citations":  { "type": "array" }
        }
      },
      "x-source": "$.summary.signals[*]"
    },
    "enrichment": {
      "type": "array",
      "items": { "type": "object" },
      "x-source": "$.summary.enrichment_blocks[*]"
    },
    "degraded_rules": {
      "type": "array",
      "x-source": "$.summary.degraded_rules[*]"
    },
    "narrative": {
      "type": "string",
      "x-llm": {
        "purpose": "explain_verdict",
        "max_words": 200
      }
    }
  }
}
```

Pensado para los casos típicos (workflow de validación con verdict + razones + citations + texto explicativo). Cubre Caso 1 (Microcrédito) y Caso 2 (Fondos) sin que el cliente tenga que escribir schema; Caso 3 (Recetas) lo usará una vez que `REVIEW` esté implementada (ver `general.md`).

### 3.3 Custom schema con annotations

Para que la síntesis sea predictible y barata, los fields del custom schema declaran su fuente vía dos extension keywords:

| Annotation | Significado | Quién la rellena |
|---|---|---|
| `x-source: "<jsonpath>"` | El field se rellena con el valor del jsonpath aplicado al `SynthesisContext`. | Proyección estructural (sin LLM). |
| `x-llm: { purpose, ... }` | El field se rellena con LLM, usando el `purpose` como guía. | Etapa LLM. |
| (sin annotation) | El field se rellena con LLM, con todo el `SynthesisContext` como input. | Etapa LLM. |

**Ejemplo (Caso Desgravámenes del cliente):**

```json
{
  "type": "object",
  "properties": {
    "datos": {
      "type": "object",
      "properties": {
        "persona_principal": {
          "x-source": "$.summary.enrichment_blocks[?(@.rule_label=='extract_persona_principal')].output"
        },
        "agraviados": {
          "type": "array",
          "x-source": "$.summary.enrichment_blocks[?(@.rule_label=='extract_agraviados')].output.items[*]"
        }
      }
    },
    "analysis": {
      "type": "object",
      "properties": {
        "status":    { "x-source": "$.summary.verdict" },
        "razones":   { "x-source": "$.summary.signals[?(@.polarity=='FAIL')].detail.reason" },
        "citations": { "x-source": "$.summary.signals[*].citations[*]" }
      }
    },
    "summary_text": {
      "x-llm": {
        "purpose": "summarize_for_underwriter",
        "tone": "formal",
        "max_words": 150
      }
    }
  }
}
```

**Resultado:** todo `datos` y `analysis.{status, razones, citations}` se rellenan por proyección JSONPath (cero LLM). Solo `summary_text` invoca al LLM.

### 3.4 JSONPath como lenguaje de mapeo

Decisión: usar **JSONPath estándar** (no inventar lenguaje propio).

- Sintaxis ampliamente conocida, librerías maduras en Python (`jsonpath-ng`).
- Filtros (`[?(@.x=='y')]`) cubren los casos comunes (filtrar signals por polarity, blocks por rule_id, etc.).
- Si una expresión devuelve **0 resultados**, el field queda en `null` (o vacío para arrays). No es error — el cliente decide qué hacer con nulls vía `required` del JSON Schema.
- Si devuelve **1 resultado** y el field es escalar → se asigna directo. Si devuelve **N** y el field es array → wrap.
- Tipos incompatibles (jsonpath devuelve string, schema espera number) → **soft-fail al field**: queda en `null`, se anota en `synthesis_metadata.field_errors`. Las demás ramas siguen, la síntesis no aborta.

> **Política única de errores en S2:** **siempre soft-fail al field**. Una expresión JSONPath malformada, tipos incompatibles, o cualquier excepción evaluando una rama → el field queda `null` y se loggea. La síntesis sigue con las demás ramas. Si después en S5 un field obligatorio quedó `null`, ahí se decide qué hacer (ver §6 S5).

> **Por qué no GraphQL / Jq / lenguaje propio:** JSONPath es el estándar de facto para extracción declarativa de JSON, soporta lo que necesitamos, y no requiere que el usuario aprenda algo nuevo si ya editó schemas REST.

---

## 4. Inputs al synthesizer

```python
@dataclass
class SynthesisContext:
    summary: WorkflowAnalysisRunSummary       # verdict, signals, enrichment_blocks, degraded_rules, confidence_score
    case: CaseSnapshot                        # ver shape abajo
    output_schema: dict                       # custom o default
    locale: str                               # idioma para narrativa
    workflow_meta: dict                       # workflow_id, version, name, industry — disponible para el LLM


@dataclass
class CaseSnapshot:
    case_id: UUID
    documents: list[CaseDocument]             # cada doc del case con su extracción y texto


@dataclass
class CaseDocument:
    document_id: UUID
    document_type_slug: str                   # "cedula", "factura", etc.
    extracted_fields: dict[str, Any]          # match con DocumentType.fields
    text: str | None                          # OCR del doc, opcional según tamaño
    page_count: int
```

JSONPath en las annotations opera sobre **este objeto entero**: `$.summary.signals[*]`, `$.case.documents[?(@.document_type_slug=='cedula')].extracted_fields.nombre`, `$.workflow_meta.industry`.

```python
class SynthesisStatus(str, Enum):
    SUCCESS  = "SUCCESS"   # output completo y conforme al schema
    DEGRADED = "DEGRADED"  # output entregable pero con sentinels o fields obligatorios en null
    ERRORED  = "ERRORED"   # síntesis falló estructuralmente; cliente recibe summary crudo


@dataclass
class SynthesisOutcome:
    output: dict                              # JSON conforme al output_schema
    schema_version: int                       # del output_schema en el momento de sintetizar
    status: SynthesisStatus                   # campo del modelo; expuesto en la API como `synthesis_status` (ver §10)
    citations: list[Citation]                 # consolidación de todas las citations propagadas
    narrative: str | None                     # convenience field si el schema tenía narrative
    synthesis_metadata: dict                  # timing por etapa, LLM calls, validation, field_errors
```

---

## 5. El protocol del Synthesizer

```python
class WorkflowSynthesizer(Protocol):
    name: str
    description: str

    async def synthesize(self, ctx: SynthesisContext) -> SynthesisOutcome: ...
```

El Protocol expone **una sola operación: `synthesize(ctx)`**. Es una transformación pura `SynthesisContext → SynthesisOutcome`, sin acoplamiento a loading de runs, persistencia, ni queues.

> **Por qué un Protocol y no una sola implementación:** habilita catálogo de synthesizers especializados sin reescribir el runner. Casos plausibles: synthesizer "fast" sin LLM (output puramente estructural), synthesizer "rich" con narrativa elaborada, synthesizer "compliance" con formato regulatorio.

> **Por qué `resynthesize` NO está en el Protocol:** la resíntesis es **orquestación**, no responsabilidad del synthesizer. El flujo "cargar summary del run X + construir nuevo `SynthesisContext` + llamar `synthesizer.synthesize(ctx)` + reemplazar output anterior" vive en una use case (`ResynthesizeRun`) que orquesta esos pasos. El Protocol se mantiene puro y testeable.

**Default registrado:** `DefaultSynthesizer` cubre todos los casos hoy (proyección JSONPath + LLM para narrativa). Otros synthesizers se suman a demanda.

---

## 6. Mini-pipeline interno

A diferencia de EVALUATE (donde cada etapa puede ser cara), el pipeline de síntesis tiene **una sola etapa potencialmente cara** (S3, narrativa). Las demás son determinísticas y baratas:

```
SynthesisContext
   │
   ├─[S1] schema validation        ──── siempre — valida que output_schema es JSON Schema válido
   │
   ├─[S2] proyección estructural   ──── siempre — recorre el schema, evalúa x-source
   │      (rellena todos los fields con annotation)
   │
   ├─[S3] LLM filling              ──── si quedan fields sin annotation o con x-llm
   │      (un solo LLM call — el output debe respetar el schema vía structured generation)
   │
   ├─[S4] citation propagation     ──── siempre — consolida citations de los fields rellenos
   │
   └─[S5] output schema validation ──── siempre — el output completo valida contra output_schema
```

### S1 — Schema validation

Antes de procesar nada, valida que `output_schema` es un JSON Schema bien-formado. Si está mal:

- Si es el default → bug del sistema, alerta crítica, `status=ERRORED`.
- Si es custom → `status=ERRORED`, `error="invalid output_schema: ..."`. El editor del workflow debió validarlo antes pero protegemos en runtime.

### S2 — Proyección estructural

Recorre el schema y, para cada field con `x-source`:
1. Compila el JSONPath (cacheado por schema_version).
2. Evalúa contra el `SynthesisContext`.
3. Asigna el resultado al field correspondiente del output, validando tipo contra el schema parcial.

**Costo:** microsegundos por field. Cero LLM.

**Output parcial al final de S2:** un dict que tiene rellenos todos los fields con `x-source`. Los fields sin annotation o con `x-llm` quedan ausentes.

### S3 — LLM filling

**Solo corre si hay fields pendientes** (sin annotation o con `x-llm`). En la mayoría de schemas declarativamente bien hechos, esto reduce a un solo field: la narrativa.

**Un solo LLM call** con structured generation:
- Prompt incluye: el output parcial (de S2), el schema de los fields pendientes, los hints de cada `x-llm.purpose`, el `locale`, el verdict y un resumen del summary.
- Modelo configurable a nivel workspace (default: el reviewer del kind dominante o un modelo dedicado a generación).
- Temperature baja (0.2 default) para reproducibilidad razonable.
- **Timeout:** 30 s default, configurable a nivel workspace (`SYNTHESIS_LLM_TIMEOUT_S`).
- Output validado contra el sub-schema de los fields pendientes.

**Si el LLM falla, timeout, o el output no valida:**
- Reintento (1×) con prompt simplificado.
- Si vuelve a fallar → cada field pendiente queda con un **valor sentinel** (`null` para escalares, `[]` para arrays, `"(narrativa no disponible)"` para `narrative`).
- `synthesis_metadata.llm_filling_failed = True`, `synthesis_metadata.llm_failure_reason = "timeout" | "schema_violation" | "provider_error"`.
- **Soft-fail al field**, no a la síntesis entera. El run **no** se marca como `ERRORED`.

### S4 — Citation propagation

Consolida las `Citation`s de todos los fields que las heredaron vía `x-source`:
- Si un field se llenó desde `$.summary.signals[*].citations[*]`, esas citations se agregan al `SynthesisOutcome.citations` global.
- Deduplica por `(document_id, page, bbox/offset)`.
- Las citations también pueden quedar embebidas inline en cada field si el schema lo declara (`citations` como sub-property del field).

### S5 — Output schema validation

Valida el output final completo contra `output_schema`. Si falla:
- **Field obligatorio quedó `null`** (porque su `x-source` devolvió 0 resultados, o porque S3 cayó en sentinel) → se loggea en `synthesis_metadata.missing_required = [field_path, ...]`, `status=DEGRADED`. El output se entrega igual con el `null` o sentinel — el cliente decide qué hacer.
- **Inconsistencia estructural** del output (bug del synthesizer, output que no respeta tipos del schema) → `status=ERRORED`, output crudo guardado para debugging, fallback al summary crudo.

---

## 7. Narrativa

La narrativa **no es un concepto especial** — es un field más del schema con `x-llm`. El default schema la incluye con `purpose=explain_verdict`; los custom schemas la pueden omitir o redefinir.

**Tipos de narrativa que el sistema sabe generar** (vía `purpose`):

| `purpose` | Pensado para | Características |
|---|---|---|
| `explain_verdict` (default) | "Por qué este case PASSED/FAILED/REVIEW" | Cita los blocking_failures y signals MAJOR. Tono neutral, factual. |
| `summarize_for_underwriter` | Resumen ejecutivo para un humano que decide | Tono formal, ≤150 palabras, énfasis en riesgos. |
| `customer_facing` | Comunicación al cliente final | Tono empático, evita jerga técnica, no expone reglas internas. |
| `audit_log` | Registro para compliance | Cronológico, exhaustivo, todas las citations inline. |
| (custom string) | Use case específico del workflow | El prompt del LLM lo respeta como instrucción libre. |

**Locale:** la narrativa se genera en `Workflow.output_locale` (ISO 639-1). El system prompt del LLM se ajusta para forzar el idioma.

**Verdict-aware:** si `verdict=None` (Caso 5 Circulares — workflow puro de Enrichment), la narrativa con `purpose=explain_verdict` se omite o devuelve `"(no aplica — workflow sin reglas de validación)"`.

---

## 8. Resíntesis sin re-evaluar

**Caso de uso:** se necesita re-armar el output de un run sin re-pagar la evaluación de las reglas. Dos escenarios:

1. **Preview en el editor del schema** — el usuario edita el `output_schema` y quiere ver cómo quedaría el output sobre un run real (para validar el cambio antes de guardar).
2. **Re-síntesis on-demand** — operacional/soporte: forzar una nueva síntesis para un run específico (ej. el LLM falló y degradó la primera vez; se quiere reintentar con un modelo distinto o un schema actualizado).

**Flujo (un solo run a la vez):**

1. Use case `ResynthesizeRun` recibe `(run_id, output_schema | None)`.
2. Carga el `WorkflowAnalysisRunSummary` ya persistido (NO re-corre EVALUATE).
3. Construye un `SynthesisContext` nuevo con el schema indicado (o el actual del workflow si no se pasó uno).
4. Llama `synthesizer.synthesize(ctx)`.
5. El nuevo `SynthesisOutcome` **reemplaza** al anterior in-place. No hay tabla histórica de outputs en v1.

**Garantías:**
- `EVALUATE` no se re-ejecuta. Costo = una sola corrida de SYNTHESIZE (típicamente 1 LLM call para narrativa).
- `verdict`, `signals` y `enrichment_blocks` **no cambian** — siguen siendo los del run original.
- Si el nuevo schema es inválido (S1 fail), la resíntesis falla y el output anterior se conserva intacto.

> **Esto es lo que justifica separar EVALUATE de SYNTHESIZE como fases distintas.** Si fueran una sola fase, cambiar el formato del output forzaría re-correr todas las reglas, aunque el juicio no cambió.

### 8.1 Cambio de schema — política de runs históricos

Cuando se edita el `output_schema` del workflow:

- **Runs futuros** usan el schema nuevo (`output_schema_version` incrementa, los runs nuevos lo adoptan automáticamente).
- **Runs históricos quedan congelados** con el `SynthesisOutcome` que tenían al momento de su corrida original. **No se re-sintetizan automáticamente, ni masivamente.**
- Cada `SynthesisOutcome` persiste su `schema_version` para que el cliente sepa con qué versión del schema se generó.

**Por qué no bulk-migration automática:**
- Costo no acotado (workflows con miles de runs históricos × LLM calls).
- Decisiones operacionales no triviales (rate limit, progreso, cancelación, idempotencia, costo previo) que solo tienen sentido diseñar cuando aparezca un caso real.
- La consistencia visual entre runs viejos y nuevos se resuelve mejor en la **UI** (mostrar el schema_version junto al output, o renderizar runs viejos con un layout legacy) que forzando re-síntesis masiva.

**Si alguna vez hace falta migrar runs históricos al schema nuevo:** se hace caso por caso vía la resíntesis individual de §8 (mismo flujo, una run por vez). No hay endpoint bulk en v1.

---

## 9. Caching

Clave de caché: `sha256(summary_hash || output_schema_version || locale || synthesizer.name)`.

- **`summary_hash`** = SHA256 canónico de `(verdict, signals_ordered, enrichment_blocks_ordered, degraded_rules, confidence_score)`. Estable run-to-run para mismo input.
- **`output_schema_version`** = el integer del workflow en el momento de sintetizar.
- **`locale`** = el `Workflow.output_locale`.
- **`synthesizer.name`** = identidad del synthesizer registrado. Importante porque cambiar el synthesizer (ej. `default` → `compliance`) **debe** invalidar el caché — el output puede ser distinto aunque los inputs sean idénticos.

Cuando hit:
- Retorna el `SynthesisOutcome` cacheado sin re-correr S2-S5.
- `synthesis_metadata.cache_hit=True`.

Cuando miss:
- Corre el pipeline completo, persiste el `SynthesisOutcome`, escribe la entrada de caché.

**Invalidación:** automática vía cambio de cualquier componente de la clave. No hay TTL — los outputs son determinísticos por construcción (modulo LLM, que con seed+temp baja es razonablemente reproducible; si no, el cache_hit produce el output del primer call que es el "canónico").

---

## 10. Errores y degradación

| Etapa | Falla → comportamiento | Estado resultante |
|---|---|---|
| S1 | Schema inválido. Verdict y signals siguen disponibles desde summary. | `status=ERRORED` |
| S2 | Una expresión JSONPath inválida → ese field queda `null`, se loggea, las demás siguen. | `status=DEGRADED` (si el field era obligatorio) o `SUCCESS` |
| S3 | LLM falla → reintento, después sentinel. **Soft-fail al field**, síntesis sigue. | `status=DEGRADED` (si el field era obligatorio) o `SUCCESS` |
| S4 | Bug raro de propagación → citations parciales, log warn. | `status=SUCCESS` (citations son informativas) |
| S5 — *missing required* | Field obligatorio quedó `null` (S2 0 results / S3 sentinel). Output se entrega igual con el sentinel; cliente decide. | `status=DEGRADED` |
| S5 — *structural* | Output viola tipos del schema (bug). Output crudo guardado para debug; fallback al summary crudo. | `status=ERRORED` |

**Soft-fail global:** si SYNTHESIZE crashea o termina con `status=ERRORED`, **el run igualmente queda como `COMPLETED`** (no como FAILED). El cliente puede consumir el summary crudo (`verdict`, `signals`, `enrichment_blocks`) directamente desde la API si la síntesis no produjo output. Esto es porque la información valiosa (juicio de las reglas) ya existe — la síntesis es format conversion.

**Visibilidad para el cliente:**
- API expone `synthesis_status: SUCCESS | DEGRADED | ERRORED`.
- Si `DEGRADED`, expone `synthesis_warnings: list[str]` con qué fields quedaron con sentinel.
- Si `ERRORED`, el endpoint del output devuelve el summary crudo con `Content-Type` indicando "raw fallback".

---

## 11. Cambios sobre el código existente

| # | Cambio | Motivo | Breaking |
|---|---|---|:-:|
| 1 | Sumar `output_schema_version: int` a `Workflow`. Incrementa con cada edición del schema. | Clave de caché, trigger de resíntesis, audit. | No (default 1) |
| 2 | Sumar `output_locale: str` a `Workflow` (default `"es"`). | Narrativa multi-idioma sin hardcodear. | No |
| 3 | **Eliminar el campo `synthesis_enabled` del modelo `Workflow`.** SYNTHESIZE siempre corre. Si hace falta apagar la síntesis por incidente operacional, se hace vía feature flag de plataforma. | Coherencia con `general.md`; un workflow sin síntesis no tiene sentido en el modelo target. Si el cliente quiere el summary crudo, lo lee directo de la API. | **Sí** (DB migration: drop columna; workflows con `synthesis_enabled=False` quedan con síntesis activa — avisar a owners afectados) |
| 4 | Adoptar `x-source` (JSONPath) y `x-llm` (config) como extension keywords del JSON Schema. | Convertir la síntesis en mayormente declarativa; reducir 90% de los LLM calls. | No (annotations opcionales) |
| 5 | Convertir el synthesizer en plug-in via Protocol `WorkflowSynthesizer`. Hoy es una sola implementación monolítica. | Permitir synthesizers especializados (fast, rich, compliance) sin reescribir el runner. | No (refactor interno) |
| 6 | Implementar use case `ResynthesizeRun(run_id, schema?)` **single-run** (orquestación: cargar summary, construir `SynthesisContext` nuevo, llamar `synthesizer.synthesize`, reemplazar output). **No** se agrega un método separado al Protocol — el Protocol queda con solo `synthesize(ctx)`. **No hay endpoint bulk** (decisión §8.1). | Habilita re-síntesis individual (preview del editor, soporte/debug) sin acoplar loading/persistencia al synthesizer ni comprometer migraciones masivas. | No (capacidad nueva) |
| 7 | Caché de `SynthesisOutcome` con clave `(summary_hash, output_schema_version, locale, synthesizer.name)`. | Re-corridas idénticas reutilizan; re-síntesis trivial cuando no cambia el schema; cambiar de synthesizer invalida cache. | No |
| 8 | API: `synthesis_status`, `synthesis_warnings`, fallback al summary crudo cuando ERRORED. | Soft-fail visible al cliente sin que la integración se rompa. | No (campos nuevos) |
| 9 | Sumar `purpose` enum + custom string en `x-llm` para narrativa. Catálogo inicial: `explain_verdict`, `summarize_for_underwriter`, `customer_facing`, `audit_log`. | Estandarizar tipos de narrativa comunes. | No |
| 10 | Schema scaffolding: cuando el usuario crea un workflow nuevo, generar un `output_schema` candidato a partir de las reglas + kinds del workflow (con annotations sugeridas). | UX — pocos clientes querrán escribir el JSON Schema desde cero. Reduce fricción de adopción. | No (feature opcional del editor) |

---

## 12. Glosario específico de `SYNTHESIZE`

- **`SynthesisContext`** — el bundle de inputs del synthesizer: `summary` (output de EVALUATE), `case` (documents con extractions), `output_schema`, `locale`, `workflow_meta`. JSONPath en las annotations opera sobre este objeto.
- **`SynthesisOutcome`** — el resultado del synthesizer: `output` (JSON conforme al schema), `status` (`SynthesisStatus`), `schema_version`, `citations` consolidadas, `narrative` opcional, `synthesis_metadata`.
- **`x-source`** — annotation del JSON Schema que declara la fuente de un field como expresión JSONPath sobre el `SynthesisContext`. Permite proyección estructural sin LLM.
- **`x-llm`** — annotation del JSON Schema que declara que un field se debe rellenar con LLM, opcionalmente con un `purpose` que guía el prompt.
- **Proyección estructural** — la etapa S2 del mini-pipeline: recorrer el schema, evaluar JSONPaths, rellenar fields. Mayoría de los outputs se construyen 100% con esta etapa.
- **LLM filling** — la etapa S3: un solo LLM call para los fields que quedaron sin rellenar después de S2. Típicamente solo la narrativa.
- **Resíntesis** — re-correr SYNTHESIZE sobre un summary ya persistido, con un schema potencialmente nuevo. **No re-ejecuta EVALUATE.**
- **`summary_hash`** — SHA256 canónico del `WorkflowAnalysisRunSummary`. Junto con `output_schema_version`, `locale` y `synthesizer.name` forma la clave de caché.
- **`synthesis_status`** — campo del run expuesto en la API: `SUCCESS | DEGRADED | ERRORED`. `DEGRADED` significa que algunos fields cayeron en sentinel pero el output es consumible.
- **Sentinel** — valor que el synthesizer pone en un field cuando S3 falla y no puede generar el contenido real (`null` para escalares, `[]` para arrays, string fijo para `narrative`).
- **Default schema** — el JSON Schema que se usa cuando `Workflow.output_schema=NULL`. Cubre el caso "verdict + signals + narrativa" sin que el cliente tenga que escribir nada.
