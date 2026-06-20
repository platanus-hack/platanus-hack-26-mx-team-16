---
feature: pipeline
type: spec
status: partial
coverage: 50
audited: 2026-06-16
---

# Workflow Case Pipeline

> Cómo procesa Doxiq un `WorkflowCase` desde que llegan los archivos hasta el output estructurado. Define las **fases**
> del pipeline y las **dos dimensiones** de output que produce la evaluación de reglas.

---

## 1. El pipeline en una imagen

```
INGEST → PROCESSING → REVIEW? → EVALUATE? → SYNTHESIZE
            │                       │
            ├─ EXTRACT_TEXT         ├─ Validation → signals + verdict
            ├─ CLASSIFY_PAGES       └─ Enrichment → enrichment_blocks
            ├─ EXTRACT_FIELDS         (dos dimensiones del mismo output;
            └─ VALIDATE_EXTRACTION    una sola ejecución por regla)
```

| Fase | Qué hace | Output |
|---|---|---|
| **`INGEST`** | Recibe los archivos del case y los persiste. | Un `WorkflowDocumentSet` por archivo cargado. |
| **`PROCESSING`** | Sub-pipeline orquestado en un workflow de **Temporal**. Contiene cuatro sub-fases secuenciales (ver abajo). | N `WorkflowDocument`s con `document_type_id` y fields extraídos + validados. |
| &nbsp;&nbsp;`EXTRACT_TEXT` | Lee el texto del archivo vía OCR (ej. Textract). | Texto OCR persistido en el `WorkflowDocumentSet`. |
| &nbsp;&nbsp;`CLASSIFY_PAGES` | Clasifica las páginas del Set en N `WorkflowDocument`s, cada uno asociado a un `DocumentType`. **Aquí se hace el splitting implícito** — si más adelante hace falta, esta fase es donde aterrizan estrategias adicionales (regex, blank-page, visual marker). | N `WorkflowDocument`s con `document_type_id` y `page_range`. |
| &nbsp;&nbsp;`EXTRACT_FIELDS` | Por cada `WorkflowDocument`, extrae datos estructurados usando `DocumentType.fields` (JSON Schema) con structured generation. | Una extraction por documento, accesible como `@<doctype>.<field>`. |
| &nbsp;&nbsp;`VALIDATE_EXTRACTION` | Valida los fields extraídos contra `DocumentType.validation_rules`. | Flags de validez por field; los inválidos quedan marcados pero no bloquean el run. |
| **`REVIEW`** *(diferida)* | Pausa el run para human-in-the-loop sobre las extractions. | Override no destructivo de fields; runner reanuda en `EVALUATE`. |
| **`EVALUATE`** *(opcional)* | Corre las `WorkflowRule`s del workflow. **Dos sub-fases en paralelo**, cada una activa solo si hay reglas de su tipo: **Validation** (cross-document → verdict) y **Enrichment** (transformaciones → shapes nuevos). | `signals` + `verdict` (Validation) y/o `enrichment_blocks` (Enrichment). |
| **`SYNTHESIZE`** | Compone la salida final conforme al `output_schema` del workflow. Si `output_schema` es `NULL` se usa un default orientado a validación. Recibe los outputs de `EVALUATE` + extractions del case. | JSON final entregado al cliente, opcionalmente con narrativa textual. |

- **`INGEST`, `PROCESSING` y `SYNTHESIZE` siempre corren** (sus sub-fases dentro de PROCESSING también). `EVALUATE` se skipea si el workflow no tiene reglas. `REVIEW` está reservada y diferida.
- **`PROCESSING` vive en Temporal.** El resto del pipeline corre en el runner de la API. La frontera Temporal/API existe porque PROCESSING tiene pasos largos, retriables y caros (OCR, LLMs); Temporal le da reintentos y resiliencia.
- **Splitting implícito en `CLASSIFY_PAGES`.** No hay fase `SPLIT` separada: la clasificación de páginas decide cuántos `WorkflowDocument`s se crean por Set. Si en el futuro hace falta una estrategia distinta de splitting, va dentro de esa misma sub-fase.
- **`EVALUATE` produce dos dimensiones de output.** Validation y Enrichment **no son dos ejecuciones distintas**: cada regla se evalúa **una sola vez** y, según el flag `produces_enrichment` de su kind, su result alimenta una dimensión u otra. Cada dimensión aparece en el summary solo si tiene contenido. Un workflow puede aportar a ambas, a una sola, o a ninguna (caso solo-extracción).
- **Sin DAG.** Pipeline lineal de fases macro; el paralelismo solo aparece dentro de `EVALUATE`. Si aparecen topologías más complejas, generalizar entonces — no antes.

---

## 2. Las fases

### `INGEST`

Recibe los archivos que el cliente sube como parte del case (PDF, TIF, imágenes) y los persiste. Es una fase liviana — no procesa contenido, solo materializa el archivo en storage y crea la fila de tracking.

**Output:** un `WorkflowDocumentSet` por archivo (contiene el blob/referencia al storage + metadata como número de páginas y mime type). En este punto el Set todavía no tiene texto OCR ni `WorkflowDocument`s hijos — eso lo produce `PROCESSING`.

### `PROCESSING`

Sub-pipeline orquestado en un **workflow de Temporal**. Vive en Temporal (no en el runner de la API) porque sus sub-fases son largas, caras y necesitan reintentos resilientes (OCR puede tardar minutos, los LLMs fallan transitoriamente). Contiene cuatro sub-fases secuenciales que transforman un `WorkflowDocumentSet` recién ingerido en N `WorkflowDocument`s con datos estructurados validados.

#### `EXTRACT_TEXT`

Lee el texto del archivo del Set usando un OCR (hoy Textract; pluggable). El texto queda persistido en el `WorkflowDocumentSet` para que las sub-fases siguientes lo consuman sin re-procesar.

**Output:** texto OCR + metadata por página (bounding boxes, tablas detectadas) en el Set.

#### `CLASSIFY_PAGES`

Clasifica las páginas del Set en N `WorkflowDocument`s, asignando cada uno a un `DocumentType` del catálogo del workflow. Aquí ocurre el **splitting implícito**: un Set con un solo tipo lógico produce un Document; un Set con varios tipos pegados (ej. una circular con N oficios) produce N Documents distintos, cada uno con su `page_range` y `document_type_id`.

**Estrategias futuras de splitting** aterrizan dentro de esta misma sub-fase — no hay una fase `SPLIT` separada. Hoy la única estrategia es la clasificación LLM por contenido; mañana pueden sumarse `regex_header`, `blank_page`, `visual_marker`, etc., todas como variantes internas de `CLASSIFY_PAGES`.

**Output:** N `WorkflowDocument`s hijos del Set, cada uno con `document_type_id` y `page_range` seteados.

#### `EXTRACT_FIELDS`

Por cada `WorkflowDocument`, extrae datos estructurados usando `DocumentType.fields` (un JSON Schema que el cliente edita en el backoffice). Usa un LLM con structured generation que recibe el texto OCR del rango de páginas del Document y produce un objeto que valida contra el schema.

**Ejemplo:** `DocumentType.fields` para `cedula` puede ser `{numero_documento: string, nombre_completo: string, fecha_nacimiento: date}`. Tras esta sub-fase, esos valores quedan accesibles en prompts de reglas como `@cedula.numero_documento`, etc.

**Output:** una extraction por `WorkflowDocument`, accesible vía la sintaxis `@<doctype_slug>.<field_path>` (ej. `@cedula.numero_documento`, `@estado_cuenta.saldos[].monto`). Si un documento tiene tablas o secciones repetidas, se modelan como arrays dentro del schema; no se generan múltiples extractions por documento.

#### `VALIDATE_EXTRACTION`

Valida los fields extraídos en la sub-fase anterior contra `DocumentType.validation_rules` (reglas a nivel field — formato, rangos, presencia obligatoria, checksums tipo RUT/CUIT, etc.). Es una validación **estructural y por documento**, distinta de las reglas cross-document de `EVALUATE`.

**Output:** flags de validez por field. Los inválidos quedan marcados (visibles en la UI y consumibles por reglas de EVALUATE) pero no bloquean el run — la decisión de qué hacer con datos inválidos vive en EVALUATE/SYNTHESIZE, no acá.

### `REVIEW` — opcional, **diferida**

> **Estado: documentada, sin implementación inmediata.** El lugar está reservado; el detalle vive aquí para no perderlo cuando aparezca un cliente que la necesite (caso Recetas vs Póliza). Implementa el **human-in-the-loop**.

Pausa el run hasta que un humano confirme o edite las extracciones de `PROCESSING`, antes de evaluar reglas.

- **Cuándo usarla:** la precisión es crítica y un error en `EXTRACT_FIELDS` cascadea (caso Recetas: confirmar la lista de medicamentos antes de cruzar con la póliza).
- **Comportamiento:** runner persiste `status=AWAITING_REVIEW`, emite SSE `review.opened`, espera `POST /runs/{id}/review/resolve`. Las ediciones se guardan como override **no destructivo** (queda el rastro extraído vs confirmado), y el runner reanuda en `EVALUATE`.
- **Configurable por workflow:** qué fields/document_types abren review, roles autorizados, SLA opcional.
- **Edge cases sin política todavía** — se resuelven cuando se implemente, en sub-spec dedicada `workflow-review-phase.md`:
  - SLA breach (¿reanuda con originales? ¿falla? ¿escala?).
  - Rechazo total (vs editar): ¿cancela el run? ¿endpoint dedicado?
  - Concurrencia entre dos reviewers tomando el mismo review.
  - Re-apertura post-resolución.
  - Notificaciones (out of scope de este spec).
  - Shape del request body de `/review/resolve`.

### `EVALUATE` — opcional

Si el workflow tiene `WorkflowRule`s configuradas, las evalúa todas en una sola pasada. **Cada regla se ejecuta una vez**; según el flag `produces_enrichment` de su kind, su result alimenta una de las dos dimensiones del summary:

- **Validation** — reglas cross-document (`VALIDATION` y kinds afines del catálogo) que verifican condiciones que mezclan datos de varios `WorkflowDocument`s. Producen `VerdictSignal`s que el aggregator combina en un `verdict` final.
- **Enrichment** — reglas (`DERIVATION`, `SUMMARIZATION`, etc.) que **transforman** datos de uno o más documentos en shapes nuevos pensados para alimentar `SYNTHESIZE`.

Ambas dimensiones se construyen sobre la misma corrida y aparecen en el summary solo si tienen contenido (ver §3 para el detalle de cómo se reparte cada result). Si no hay reglas configuradas, `EVALUATE` se skipea y el run va directo a `SYNTHESIZE` con solo las extractions del case.

A nivel pipeline una regla es **una unidad atómica** que produce un `WorkflowRuleResult`. **Cómo se compila y evalúa internamente cada regla** (sub-checks AND/OR, pre-evaluación determinística, reviewer LLM con self-consistency, crítico cross-provider, verificación post-hoc de citations) vive en una sub-spec dedicada — fuera del alcance de este documento.

> **Human-in-the-loop fuera de EVALUATE.** El único mecanismo HITL del pipeline es la fase `REVIEW` (diferida hoy), que pausa el run para que un humano confirme/edite extractions antes de evaluar reglas. No existe un kind de regla que pause el runner mid-EVALUATE — si en el futuro aparece un caso real que lo justifique, se diseña ahí.

### `SYNTHESIZE`

**Siempre corre.** Toma los outputs de `EVALUATE` (y opcionalmente las extractions del case) y genera la salida final conforme al `output_schema` del workflow.

`Workflow.output_schema` es un JSON Schema **opcional**: si está en `NULL`, el synthesizer aplica un **schema default orientado a validación** (verdict + razones + citations), pensado para los casos típicos donde el cliente quiere un fallo estructurado. Workflows que necesitan otra forma (consolidación de datos, reporte custom) definen su propio schema.

**Ejemplo:** el cliente de Desgravámenes define `output_schema` como `{datos: {persona_principal, agraviados[], vehiculos[]}, analysis: {status, razones[], citations[]}}`. El synthesizer compone ese shape combinando `enrichment_blocks` (para el bloque `datos`) y `signals` + `verdict` (para `analysis`).

Inputs que recibe:

- **Run summary** — `verdict` (puede ser `None` si no había reglas de Validation), `signals` con sus `detail`s, `enrichment_blocks` con sus outputs y citations.
- **Case context** — los `WorkflowDocument`s del case con sus extractions, para casos en que el `output_schema` referencia datos extraídos directamente y no derivados por reglas.

Comportamiento según el workflow:

- **Con reglas:** el synthesizer compone el `output_schema` (custom o default) usando signals, verdict y enrichment_blocks.
- **Sin reglas:** `EVALUATE` se skipeó; el synthesizer compone sobre las extractions directamente. Útil para flujos puro-extracción donde el cliente quiere un JSON final consolidado.

Tolera `verdict=None` y listas vacías como inputs válidos.

---

## 3. Las dos dimensiones de `EVALUATE`

Las dos sub-fases de `EVALUATE` (Validation y Enrichment) producen las dos dimensiones del summary. Cada kind aporta a **exactamente una** dimensión. La elección se declara con un único flag:

```python
class WorkflowRuleKind(Protocol):
    name: str
    label: str
    description: str
    config_schema: dict     # JSON Schema que valida WorkflowRule.config
    output_schema: dict     # JSON Schema que valida WorkflowRuleResult.output
                            # (distinto de Workflow.output_schema y de DocumentType.fields)

    produces_enrichment: bool = False   # ← lo único nuevo

    def contribute_to_verdict(self, rule, result) -> VerdictSignal | None: ...
    async def compile(self, rule, ctx) -> CompilationOutcome: ...
    async def evaluate(self, rule, compilation, inputs, ctx) -> EvaluationOutcome: ...
```

| Dimensión | Sub-fase de `EVALUATE` | `produces_enrichment` | Kinds | El `output` se expone como… |
|---|---|:-:|---|---|
| **Validation** (juicio cross-document) | Validation | `False` (default) | **Hoy:** `VALIDATION`. **Catálogo (futuro):** `DETERMINISTIC_CHECK`, `TEMPORAL_RULE`, `DATA_FRESHNESS`, `SCORING`, `CLASSIFICATION`, `AGGREGATION`, `EXTERNAL_LOOKUP`, `PII_DETECTION`, `SENTIMENT_ANALYSIS`, `COMPARISON_TO_KB`, `LLM_VOTING`, `LLM_CRITIC` | `signal.detail` (drivers, alternatives, deltas, etc.) |
| **Enrichment** (datos) | Enrichment | `True` | **Hoy:** `DERIVATION`. **Catálogo (futuro):** `SUMMARIZATION` | `EnrichmentBlock.output` |

> **Por qué la mayoría de kinds son Validation**: la "data rica" que devuelve un kind de juicio (drivers de un `SCORING`, alternatives de un `CLASSIFICATION`, deltas de un `COMPARISON_TO_KB`) es **evidencia del veredicto**, no datos independientes. Va en `signal.detail` (un jsonb libre del `VerdictSignal`). Si saliera también como `EnrichmentBlock` sería duplicación. `Enrichment` queda para los kinds que producen datos **sin** emitir signal — extracción con schema custom (`DERIVATION`) y texto libre (`SUMMARIZATION`).

El runner ejecuta cada regla **una sola vez**. Según el flag `produces_enrichment` del kind, el result va a la dimensión Validation **o** a Enrichment, nunca a ambas:

```python
for rule in workflow.rules:
    result = await rule.kind.evaluate(...)
    persist(result)  # WorkflowRuleResult: una fila, sin duplicación

    if rule.kind.produces_enrichment:
        enrichment_blocks.append(EnrichmentBlock(
            rule_id=rule.uuid,
            kind=rule.kind.name,
            output=result.output,
            citations=result.citations,
            document_refs=result.document_refs,
        ))
    else:
        if signal := rule.kind.contribute_to_verdict(rule, result):
            signals.append(signal)

summary.signals           = signals
summary.verdict           = aggregate(signals) if signals else None
summary.enrichment_blocks = enrichment_blocks
```

**La UI muestra la sección `Validation` solo si `signals` no está vacío. Idem `Enrichment` con `enrichment_blocks`.** Cada signal se renderiza con su `detail` desplegable para mostrar la evidencia rica (drivers, alternatives, deltas, etc.).

**Ejemplo concreto** de qué entra dónde:

- Una regla `SCORING` produce un signal con `polarity=PASS`, `severity=MAJOR`, `detail = {score: 0.72, band: "LOW_RISK", drivers: [{factor: "ingresos_estables", weight: 0.4}, ...]}`. Va a la dimensión **Validation**. La UI lo pinta como un signal verde con un panel desplegable de drivers.
- Una regla `DERIVATION` produce un block con `output = {items: [{desc: "Honorarios", monto: 12500}, ...], total: 12500}`. Va a la dimensión **Enrichment**. La UI lo pinta como una tabla de datos.

**Results con `status` distinto de `SUCCESS`** (`ERRORED`, `SKIPPED`) no aportan a ninguna dimensión. Van a `summary.degraded_rules` (lista de `rule_id` que no pudieron evaluarse) y bajan `summary.confidence_score` (proporción de reglas exitosas sobre el total, en `[0, 1]`). El pseudocódigo de arriba asume `status=SUCCESS`; el runner real filtra antes.

**Orden de `signals[]` y `enrichment_blocks[]`**: ambos se emiten en el **orden en que las reglas están definidas en el workflow**. La UI y los integradores pueden asumir orden estable y reproducible run-a-run para reglas idénticas.

---

## 4. Casos de cliente — qué dimensiones produce cada uno

> Recordatorio: la "evidencia rica" de un kind de Validation (drivers, discrepancias, alternatives, breakdowns) vive en `signal.detail`, **no** en Enrichment. Enrichment solo aparece cuando hay reglas con `produces_enrichment=True` (`DERIVATION`, `SUMMARIZATION`).

| Caso | Validation | Enrichment | Capacidades faltantes |
|---|---|---|---|
| **Microcréditos** | verdict tri-state `PASS` / `REVIEW` / `FAIL` (UI muestra APROBADO / EN REVISIÓN / RECHAZADO); `signal.detail` lleva score + drivers del `SCORING` | — | `SCORING` kind del catálogo |
| **Fondos de Crédito y Garantía** | verdict; `signal.detail` lleva los datos comparados (nombres, montos) y deltas del `COMPARISON_TO_KB` | — | `COMPARISON_TO_KB`, `VISUAL_MARKER_DETECTION` (firma del gerente) |
| **Recetas vs Póliza** | un signal por medicamento (cubierto sí/no, con razón en `detail`) | — opcional, solo si el cliente quiere un objeto consolidado vía `DERIVATION` | `REVIEW` (**diferida**), `EXTERNAL_LOOKUP`, dynamic context, KB dinámica con RAG |
| **Desgravámenes** | status COMPLETO / INCOMPLETO / FALLO + signals con citations de páginas en `detail` | `DERIVATION` con shape custom del cliente | — (cubierto con `VALIDATION` + `DERIVATION` existentes) |
| **Circulares** | — (vacío, la UI oculta la sección) | `DERIVATION` con array de oficios | Estrategia de splitting adicional dentro de `CLASSIFY_PAGES` (regex header / blank-page / visual marker) |

Dos lecturas importantes:

- **Solo casos 4 y 5** producen Enrichment de verdad. Los otros (1, 2, 3) son puro Validation con `signal.detail` rico — Enrichment queda vacío y la UI lo oculta.
- **Caso 5 prueba el modelo**: workflow puro de extracción sin verdict, sección Validation vacía. Hoy el sistema lo forzaría a tener un verdict trivial; con `verdict` nullable y `signals` opcionalmente vacío, el modelo lo soporta limpio. Cuando llegue el cliente real de Circulares hay que sumar la estrategia de splitting que corresponda dentro de `CLASSIFY_PAGES`.
- **Casos bloqueados por features diferidas**: caso 3 (Recetas) no se puede correr hasta que `REVIEW` se implemente. Los demás son atacables con la roadmap inmediata.

---

## 5. Qué falta para correr todos los casos

| # | Capacidad | Desbloquea | Depende de | Estado |
|---|---|---|---|---|
| 1 | Sub-fases `Validation` y `Enrichment` paralelas dentro de `EVALUATE`; flag `produces_enrichment` en kind; `enrichment_blocks` en summary; `verdict` nullable; `signals` opcionalmente vacío | Casos 4 y 5 dejan de mentir; UI separa secciones por dimensión | — | **Inmediato** |
| 2 | `SCORING` kind del catálogo | Caso 1 formaliza el tri-state cuantitativo | #1 | Inmediato |
| 3 | `COMPARISON_TO_KB` kind del catálogo | Caso 2 (industria contra KB de referencia con delta numérico) | #1 | Inmediato (oportunista) |
| 4 | `EXTERNAL_LOOKUP` kind + dynamic context + KB dinámica (carga ad-hoc) + RAG semántico | Caso 3 (parcial — la otra mitad espera a `REVIEW`) | #1 | Inmediato si hay caso de uso sin REVIEW |
| 5 | Fase `REVIEW` (estado `AWAITING_REVIEW`, endpoints, SSE, UI editor de extractions, override no destructivo, edge cases en sub-spec) | Caso 3 completo; mejor UX en otros; habilita kinds con suspensión (`HUMAN_IN_THE_LOOP`) | — | **Diferido** |
| 6 | Estrategias adicionales de splitting dentro de `CLASSIFY_PAGES` (regex header, blank-page, visual marker) | Caso 5 (Circulares) | — | Diferido (depende de demanda) |
| 7 | `VISUAL_MARKER_DETECTION` kind (firmas/sellos, requiere modelo de visión) | Caso 2 (firma del gerente); también puede usarse como estrategia visual de splitting en `CLASSIFY_PAGES` | — (#6 solo si se reusa como estrategia) | Diferido (depende de demanda) |

> Estimaciones de esfuerzo deliberadamente fuera del spec: dependen del estado de la base de código al momento de implementar. Se puntean en el ticket correspondiente, no acá.

Lo realmente accionable hoy es **#1, #2, #3, posiblemente #4**. Esto cubre casos 1, 2, 4 con limpieza. Casos 3 y 5 esperan a `REVIEW` y a las estrategias extra de splitting respectivamente.

---

## 6. Modelo de datos — delta sobre lo existente

### `WorkflowAnalysisRunSummary`

```python
class EnrichmentBlock(BaseModel):
    rule_id: UUID
    rule_label: str                 # denormalizado del rule (slug/label legible) — clave para JSONPath en SYNTHESIZE
    kind: str
    output: dict[str, Any]
    citations: list[Citation]
    document_refs: dict[str, Any]   # qué documento alimentó qué slot del prompt;
                                    # proyectado desde WorkflowRuleResult.document_refs

class SignalSnapshot(BaseModel):
    rule_id: UUID
    rule_label: str                 # idem EnrichmentBlock — denormalizado para SYNTHESIZE
    polarity: WorkflowRuleVerdictPolarity
    severity: WorkflowRuleSeverity
    weight: float
    detail: dict[str, Any]
    citations: list[Citation]

class WorkflowAnalysisRunSummary(BaseModel):
    # …existente
    verdict: Verdict | None = None             # ← pasa a nullable
    signals: list[SignalSnapshot] = []
    enrichment_blocks: list[EnrichmentBlock] = []   # ← NUEVO
```

> **Por qué `rule_label` denormalizado:** la fase `SYNTHESIZE` compone outputs con `output_schema` que filtra por regla (ej. `enrichment_blocks[?(@.rule_label=='extract_persona')].output`). Forzar al synthesizer a hacer JOIN con la tabla de rules para resolver labels agrega complejidad sin beneficio. Es un `str` corto y estable; el costo del de-normalize es mínimo y mejora drásticamente la legibilidad de los schemas custom.

`enrichment_blocks` se **deriva al construir el summary** (cero migración). Persistirlo en una columna `jsonb` solo si benchmarks muestran latencia inaceptable al leer summaries grandes; por ahora no.

### `WorkflowDocument`

Los campos `document_set_id` y `page_range` ya existen en el modelo. Los `WorkflowDocument` son hijos del `WorkflowDocumentSet` (archivo físico) creados durante `CLASSIFY_PAGES` (uno o N por Set, según haga falta). El resto del pipeline opera sobre los hijos. Cuando se sumen estrategias de splitting adicionales (regex/blank-page/visual marker) van como variantes internas de `CLASSIFY_PAGES` — no hay migración de datos pendiente.

---

## 7. Glosario

- **Phase** — paso macro del pipeline. Hoy: `INGEST`, `PROCESSING` (con sub-fases `EXTRACT_TEXT`, `CLASSIFY_PAGES`, `EXTRACT_FIELDS`, `VALIDATE_EXTRACTION`), `EVALUATE`, `SYNTHESIZE`. Diferida (documentada sin implementación inmediata): `REVIEW`.
- **`PROCESSING` (Temporal)** — sub-pipeline orquestado en un workflow de Temporal. Aísla los pasos largos/caros/retriables (OCR + LLMs) del runner de la API, dándoles reintentos y resiliencia.
- **Splitting implícito** — la división de un `WorkflowDocumentSet` multi-doc en N `WorkflowDocument`s ocurre dentro de `CLASSIFY_PAGES`. No existe una fase `SPLIT` separada; estrategias adicionales (regex, blank-page, visual marker) aterrizan como variantes internas de esa sub-fase.
- **Output dimension** — una de las dos secciones del output de `EVALUATE`: `Validation` (signals + verdict) o `Enrichment` (blocks de datos). Producidas por las dos sub-fases homónimas que corren en paralelo. Cada una visible solo si tiene contenido.
- **Kind** — la "categoría" de una regla. Cada `WorkflowRule` tiene un `kind` (ej. `VALIDATION`, `DERIVATION`, `SCORING`) que define cómo se compila, cómo se evalúa, qué shape tiene su `output`, y a qué dimensión de `EVALUATE` aporta. Hoy hay dos kinds implementados (`VALIDATION` y `DERIVATION`); el resto está en el catálogo para implementar a demanda.
- **`VerdictSignal`** — estructura que produce un kind de Validation al evaluar una regla. Lleva `polarity` (PASS/FAIL/NEUTRAL), `severity` (BLOCKER/MAJOR/MINOR/INFO), `weight` y un campo libre `signal.detail` (jsonb) para evidencia rica del veredicto.
- **`signal.detail`** — el jsonb libre dentro de un `VerdictSignal`. Lleva la evidencia que sustenta el veredicto: drivers de un `SCORING`, alternatives de un `CLASSIFICATION`, deltas de un `COMPARISON_TO_KB`, etc. La UI lo muestra desplegable junto al signal.
- **`EnrichmentBlock`** — estructura que produce un kind de Enrichment. Proyección del `WorkflowRuleResult` que lleva `output` (los datos estructurados), `citations` y `document_refs` (qué documento alimentó qué slot del prompt).
- **`Citation`** — referencia a una porción específica de un documento (página, bounding box, span de texto) que sustenta un campo del output o un signal. Usada en `EnrichmentBlock.citations` y en `signal.detail.citations` cuando el kind las emite.
- **`produces_enrichment`** — flag booleano del kind. Si `True`, el `output` de cada result se expone como `EnrichmentBlock` (sub-fase Enrichment). Si `False`, se decide por `contribute_to_verdict` del mismo kind si emite signal (sub-fase Validation).
- **`DocumentType.fields`** vs **`DocumentType.validation_rules`** vs **`Workflow.output_schema`** — tres JSON Schemas/configs distintos. `DocumentType.fields` define qué extraer por tipo de documento (input de `EXTRACT_FIELDS`). `DocumentType.validation_rules` define la validación por field (input de `VALIDATE_EXTRACTION`). `Workflow.output_schema` define la forma del JSON final entregado al cliente (input de `SYNTHESIZE`). Tres niveles distintos del modelo.
- **`degraded_rules`** — lista de `rule_id`s cuyas reglas terminaron con `status` distinto de `SUCCESS` (ERRORED/SKIPPED). Aparece en el summary del run; no aporta a ninguna dimensión de output.
- **`confidence_score`** — proporción de reglas exitosas sobre el total del run, en `[0, 1]`. Aparece en el summary; cuanto más cerca de 1, menos reglas degradadas hubo.
- **`WorkflowDocument` hijo** — un documento lógico que cuelga de un `WorkflowDocumentSet` (archivo físico). Creado en `CLASSIFY_PAGES` con su `page_range` y `document_type_id`. Por default 1:1 con el Set; con multi-doc en un solo archivo, N:1.
- **Review (fase)** — pausa del run para edición humana de extracciones (HITL). **No es una rule**, es una fase del pipeline. Diferida hoy.
- **KB (Knowledge Base)** — repositorio de documentos de referencia del workspace, pre-indexados con embeddings. Las reglas pueden hacer búsqueda semántica (RAG) sobre el KB en sus prompts.
- **RAG (Retrieval-Augmented Generation)** — técnica donde el LLM recibe, junto con el prompt, fragmentos relevantes recuperados de un KB vía búsqueda semántica con embeddings. Las reglas pueden hacer RAG sobre el KB del workspace para fundamentar sus decisiones en lugar de inventar.
- **Dynamic context** — información traída en runtime (tool/API externa, o un KB cargado ad-hoc por run) que alimenta a reglas siguientes. Distinto del KB preindexado, que es estático del workspace.
