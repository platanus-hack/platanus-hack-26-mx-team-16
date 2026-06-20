---
feature: pipeline
type: spec
status: partial
coverage: 60
audited: 2026-06-16
---

# Phase `EVALUATE` — Modelo extendido

> Sub-spec de la fase `EVALUATE` del pipeline (ver `general.md`). Define el **modelo target** del kind plug-in,
> el ciclo de vida de una regla (compilación → evaluación → result), el mini-pipeline interno por regla, el reparto
> del result a las dos dimensiones del summary (Validation / Enrichment), y la agregación del verdict.
> Pensado para soportar **muchos más kinds** que los dos implementados hoy sin tener que rediseñar el contrato cada vez.

> **Convención del documento:** las decisiones marcadas **(hoy)** ya están en el código. Las marcadas **(target)**
> son cambios propuestos sobre lo existente. La sección §12 lista todos los deltas en una sola tabla.

---

## 1. Alcance

**Cubre:**
- Contrato del kind plug-in (`WorkflowRuleKind`) y todos los schemas que cada kind expone.
- Ciclo de vida: compilación, scope resolution, evaluación, result, agregación.
- Mini-pipeline interno de etapas opcionales (determinístico → LLM con self-consistency → crítico cross-provider → verificación post-hoc de citations).
- Reparto del result a las dimensiones `Validation` (signals + verdict) y `Enrichment` (enrichment_blocks).
- Algoritmo de agregación del verdict.
- Política de concurrencia y orden.

**Fuera de alcance** (vive en otros specs):
- Pipeline macro (`general.md`).
- UX de creación/edición de reglas (`create-rules.md`, `analisis-rules.md`).
- Forma del summary final entregado al cliente y su rendering (`analysis-exec-report.md`).
- Persistencia y migraciones de tablas (`workflow_persistence.md`).
- Fase `REVIEW` y kinds que requieren suspensión del runner (diferidos en `general.md`).

---

## 2. Principios de diseño

1. **Catálogo abierto de kinds.** Sumar un kind nuevo es implementar un Protocol y registrarlo. No requiere migración de schema, ni cambios al runner, ni a la agregación del verdict.
2. **Compilación separada de evaluación.** Lo caro o ambiguo (parsing del prompt, validación del config, resolución de tokens, KB lookups) ocurre **una vez al editar la regla**, no en cada run. La evaluación parte de un `artifact` ya validado.
3. **Pipeline interno por etapas opcionales.** Una regla simple es una sola llamada al LLM; una regla cara es 5 etapas. Cada kind declara sus defaults y cada regla puede sobreescribirlos. Nunca pagás más de lo que tu caso necesita.
4. **Citations como ciudadanas de primera.** Toda salida de un kind (signal o enrichment_block) puede incluir citations con la misma forma. La verificación post-hoc es transversal, no por-kind.
5. **El verdict se deriva, no se persiste como input.** Cada kind contribuye a lo sumo un `VerdictSignal`; el `Verdict` final es una función pura de `signals + degradación`. Cambiar la política del verdict es cambiar una función, no migrar datos.
6. **Scope explícito.** Qué documentos ve cada regla y cuántas veces se evalúa lo decide el `scope` de la regla — no el código del kind. Un mismo kind sirve para single-doc, tuple, agregado y all-docs.
7. **Result inmutable, dimensión derivada.** El runner persiste `WorkflowRuleResult` una vez. La proyección a `signals` o a `enrichment_blocks` se computa al construir el summary. Cambiar esa proyección no requiere re-evaluar reglas.

---

## 3. Modelo del Kind

### 3.1 Protocol (target)

```python
@runtime_checkable
class WorkflowRuleKind(Protocol):
    # Identidad
    name: str
    label: str
    description: str

    # Esquemas declarativos
    config_schema: dict           # JSON Schema → valida WorkflowRule.config al crear/editar
    detail_schema: dict           # JSON Schema → valida la forma de signal.detail        (target — NUEVO)
    default_self_consistency_n: int = 1   # cuántos votos del reviewer LLM por defecto    (target — NUEVO)
    supports_critic: bool = False         # opt-in al crítico cross-provider              (target — NUEVO)
    requires_citations: bool = False      # si True, gatilla la verificación post-hoc     (target — NUEVO)

    # Dimensión a la que aporta este kind (decisión declarativa, no por result)
    produces_enrichment: bool = False     # False → Validation | True → Enrichment        (target — NUEVO)

    def default_config(self) -> dict: ...
    def output_schema_for(self, rule: WorkflowRule) -> dict: ...      # ya existe

    async def compile(self, rule, ctx: CompileContext) -> CompilationOutcome: ...   # ya existe
    async def evaluate(self, rule, compilation, inputs: EvalInputs, ctx: EvalContext) -> EvaluationOutcome: ...  # ya existe

    def contribute_to_verdict(self, rule, result) -> VerdictSignal | None: ...      # ya existe
```

> **Por qué `produces_enrichment` como atributo y no como decisión por-result:** la dimensión que alimenta un kind es propiedad estable del **kind**, no del run. `DERIVATION` siempre produce datos; `VALIDATION` siempre produce juicio. Hacerlo flag por kind permite tests del catálogo, validaciones de UI ("este workflow no tiene reglas de Validation, ¿está bien?"), y agregación sin mirar el contenido del result.

> **Por qué `detail_schema` separado de `output_schema`:** `output` es lo que se persiste en `WorkflowRuleResult.output` (forma libre, definida por el kind). `detail` es lo que se proyecta a `signal.detail` cuando el kind aporta a Validation — un subset/transformación pensado para la UI. Tenerlo como schema declarativo permite validar que `contribute_to_verdict` no devuelva basura.

### 3.2 Catálogo target

| Kind | Dimensión | `detail` típico | Determinístico | Self-consistency default | Critic |
|---|---|---|:-:|:-:|:-:|
| `VALIDATION` (hoy) | Validation | `{tree_outcome, sub_checks[]}` | Parcial (sub-checks regex/format) | 3 | opt-in |
| `DERIVATION` (hoy) | Enrichment | — | No | 1 | opt-in |
| `SCORING` | Validation | `{score, band, drivers[]}` | No | 5 | sí |
| `CLASSIFICATION` | Validation | `{label, alternatives[], confidence}` | No | 5 | opt-in |
| `COMPARISON_TO_KB` | Validation | `{matched, deltas[], kb_refs[]}` | Parcial | 3 | opt-in |
| `DETERMINISTIC_CHECK` | Validation | `{checks[]}` | **Total** | 0 (no LLM) | no |
| `TEMPORAL_RULE` | Validation | `{periods[], breaches[]}` | Total | 0 | no |
| `DATA_FRESHNESS` | Validation | `{age_days, threshold}` | Total | 0 | no |
| `EXTERNAL_LOOKUP` | Validation | `{lookup_key, response, deltas}` | Parcial | 3 | opt-in |
| `PII_DETECTION` | Validation | `{found[], severity}` | Parcial | 1 | no |
| `SUMMARIZATION` | Enrichment | — | No | 1 | opt-in |
| `AGGREGATION` | Validation | `{by_group[], totals}` | Total | 0 | no |
| `LLM_VOTING` | Validation | `{votes[], winner}` | No | 5 (es su esencia) | opt-in |
| `LLM_CRITIC` | Validation | `{verdict, critique}` | No | 1 | n/a |

> Todo lo de la columna **dimensión** es decisión final por kind — no se reabre por regla.

---

## 4. Compilación

### 4.1 Lifecycle

```
PENDING → COMPILING → READY
                    └→ FAILED          (error en parse/config/tokens — la regla no es ejecutable)
READY    → STALE    (cuando se edita la regla)
STALE    → PENDING  (al re-compilar)
```

Una regla **no se evalúa con compilation en estado distinto de `READY`**. Si en runtime una regla apunta a una compilation `STALE` o `FAILED`, su result queda con `status=SKIPPED` y entra en `degraded_rules` (no bloquea el run).

### 4.2 Qué produce `compile()`

```python
@dataclass
class CompilationOutcome:
    artifact: dict[str, Any]       # forma libre, definida por el kind
    compiled_with: dict[str, Any]  # metadata (doc_types resueltos, kb_refs vigentes, hash del prompt, etc.)
```

El `artifact` es **kind-specific**. Ejemplos:
- `VALIDATION` → árbol AND/OR de sub-checks, cada uno marcado como `deterministic` o `llm`, con tokens ya resueltos a paths.
- `DERIVATION` → JSON Schema de salida + prompt template renderizado a placeholders tipados.
- `SCORING` → vector de drivers + función de banding.
- `DETERMINISTIC_CHECK` → AST evaluable sin LLM.

**`compiled_with`** es el contrato de invalidación: si cambia algo de lo que ahí se referencia (un `DocumentType.fields`, un `kb_doc_id`), la compilation pasa a `STALE`.

### 4.3 Resolución de tokens

Los prompts y configs de reglas referencian datos vía **tokens**:

| Token | Resuelve a |
|---|---|
| `@<doctype_slug>.<field_path>` | Field extraído de un `WorkflowDocument` de ese doc type del case |
| `#<kb_document.slug>` | Documento del Knowledge Base del workspace |
| `{{<system_var>}}` | Variable de sistema resuelta en runtime (ej. `{{now}}` para timestamp del run) |

> **Convención de prefijos:** tres universos disjuntos, cada uno con su sintaxis:
> - `@` → **datos del case** (extractions de los `WorkflowDocument`s).
> - `#` → **referencias al Knowledge Base** del workspace (documentos estáticos pre-indexados).
> - `{{…}}` → **variables de sistema** resueltas por el runner en cada evaluación. Catálogo inicial: `{{now}}` (UTC ISO-8601 al momento del run). Se irán agregando más a demanda (ej. `{{run_id}}`, `{{tenant_locale}}`).

La resolución ocurre en `compile()`: el artifact contiene paths/IDs ya validados. En `evaluate()` se leen los valores concretos por path, sin re-parsear strings. Esto es lo que hace que cambios al schema de un `DocumentType` invaliden la compilation.

---

## 5. Scope y combinations

Cada regla declara cuántas veces se evalúa y qué shape de inputs recibe el kind. Esto **es independiente del kind** — la misma `VALIDATION` puede correrse single-doc o cross-doc según su scope.

### 5.1 Modelo (target — minimalista)

```python
class WorkflowRuleScope:
    mode: WorkflowRuleScopeMode      # SINGLE_DOCUMENT | TUPLE_CARTESIAN | AGGREGATE_OVER_TYPE | ALL_DOCUMENTS
    on_empty: WorkflowRuleOnEmpty    # SKIPPED | FAILED | PASSED
```

**Eso es todo el config del scope.** El usuario elige solo dos cosas: qué *intención* tiene la regla (`mode`) y qué hacer si el set termina vacío (`on_empty`).

> **Por qué no hay `target_doctype` ni `tuple_slots`:** los doctypes ya están **asignados a cada `WorkflowDocument` en PROCESSING** (sub-fase `CLASSIFY_PAGES`) — son ground truth, no algo que la regla necesite repetir. Y los doctypes que **la regla específica necesita** se **derivan del prompt**: el compilador parsea los `@<doctype_slug>.*` (y el marker `@<doctype_slug>` sin field path) y produce el set de slugs requeridos. Tener el doctype en dos lugares (config + prompt) es vector de inconsistencia y carga cognitiva sin beneficio.

### 5.2 Los cuatro `mode` con ejemplos

| `mode` | Una evaluación por… | Shape que ve el kind | Use case típico |
|---|---|---|---|
| `SINGLE_DOCUMENT` | cada doc del único tipo declarado en el prompt | un `EvalDocumentInput` | "RUT válido en cada cédula del case" → 3 cédulas → 3 evals → 3 signals |
| `TUPLE_CARTESIAN` | cada tupla del producto cartesiano de los tipos del prompt | una tupla de `EvalDocumentInput`s | "El titular de la cédula coincide con el de la póliza" → 1 cédula × 1 póliza → 1 eval → 1 signal |
| `AGGREGATE_OVER_TYPE` | una sola, con la lista completa del único tipo del prompt | `list[EvalDocumentInput]` | "El total facturado del mes no excede $500K" → 1 eval con la lista de N facturas → 1 signal |
| `ALL_DOCUMENTS` | una sola, con todos los docs del case | `list[EvalDocumentInput]` (mezcla de tipos) | "El case tiene cédula + comprobante + extracto" → 1 eval → 1 signal estructural |

> **Por qué `SINGLE_DOCUMENT` y `AGGREGATE_OVER_TYPE` son distintas aunque ambas referencien un solo tipo:** el shape del input al kind cambia (1 doc vs lista) y el fan-out de signals cambia (N vs 1). Son intenciones distintas: "validar cada uno" vs "validar el conjunto".

### 5.3 `on_empty` — qué pasa si el set queda vacío

| `on_empty` | Result | Aporta al verdict |
|---|---|---|
| `SKIPPED` (default) | `status=SKIPPED` | No (entra a `degraded_rules`, baja `confidence_score`) |
| `FAILED` | `status=SUCCESS`, signal con `polarity=FAIL` | Sí — la ausencia *es* el fallo deliberado |
| `PASSED` | `status=SUCCESS`, signal con `polarity=PASS` | Sí — la ausencia satisface la regla |

Ejemplos prácticos de cada uno:
- **`SKIPPED`** — "RUT válido en cada cédula"; si el case no trajo cédulas, la regla no aplica. No es ni pase ni fallo.
- **`FAILED`** — "el case debe tener al menos una factura del último mes"; ausencia = fallo.
- **`PASSED`** — "no debe haber facturas vencidas"; ausencia = la regla pasa por ausencia.

> **Guideline:** evitá overloading combinando "validez del contenido" + "presencia" en la misma regla. Si te tienta `on_empty=FAILED` para una regla de validez, considerá si no es más limpio modelar la presencia como una regla `ALL_DOCUMENTS` separada — más testeable, mejor diagnóstico, signals independientes en la UI.

### 5.4 Coherencia entre `mode` y los doctypes del prompt

El compilador parsea los `@`-tokens del prompt y deriva el set de doctype slugs únicos. Valida contra `mode`. Una regla incoherente queda con `compilation.status=FAILED` y no llega a ejecutarse.

| `mode` | Doctypes únicos en el prompt | Validación |
|---|---|---|
| `SINGLE_DOCUMENT` | 0 | ✗ — el compilador no sabe sobre qué tipo iterar. **Solución:** agregar el marker `@<doctype_slug>` (sin field path) en el prompt, o cambiar a `ALL_DOCUMENTS`. |
| `SINGLE_DOCUMENT` | 1 | ✓ |
| `SINGLE_DOCUMENT` | ≥2 | ✗ — no se pueden resolver refs de varios doctypes desde un solo documento. **Usar `TUPLE_CARTESIAN`.** |
| `TUPLE_CARTESIAN` | 0 ó 1 | ✗ — el cartesian necesita ≥2 tipos. **Usar `SINGLE_DOCUMENT` o `AGGREGATE_OVER_TYPE`.** |
| `TUPLE_CARTESIAN` | ≥2 | ✓ — los slots se infieren de los slugs del prompt |
| `AGGREGATE_OVER_TYPE` | 0 | ✗ — falta el marker `@<doctype_slug>` que indica qué tipo agregar |
| `AGGREGATE_OVER_TYPE` | 1 | ✓ |
| `AGGREGATE_OVER_TYPE` | ≥2 | ✗ — agregar sobre múltiples tipos no está soportado; modelar como dos reglas o usar `ALL_DOCUMENTS` |
| `ALL_DOCUMENTS` | cualquier número | ✓ — sin restricción; el kind ve todos los docs del case |

> **Mensaje de error esperable:** `Rule scope is SINGLE_DOCUMENT but the prompt references multiple doctypes: ['cedula', 'poliza']. Change mode to TUPLE_CARTESIAN, or restrict the prompt to a single doctype.`

### 5.5 El marker `@<doctype_slug>` para reglas per-doc genéricas

Cuando una regla per-doc no necesita referenciar un field específico (la lógica vive 100% en el kind sobre el `text` u otros aspectos del doc), igual hay que decirle al compilador qué tipo iterar. Convención:

```
@contrato verifica que la última página contenga una firma manuscrita.
```

El `@contrato` solo (sin `.field`) actúa como **declaración de target**: la regla itera sobre docs de tipo `contrato`. No se renderiza como valor; el compilador lo consume y lo elimina del prompt final que ve el LLM.

Aplica también a `AGGREGATE_OVER_TYPE`:
```
@factura sumá los montos y verificá que el total no excede {{config.max_monto}}.
```

> **Por qué un marker en el prompt y no un campo `target_doctype` separado:** una sola fuente de verdad, validación implícita (no podés tener un marker que diga `cedula` y un config que diga `poliza`), y el editor de reglas puede sugerir/autocompletar markers junto con tokens normales.

### 5.6 Combinations y persistencia

Cada combination que el scope produce → **un `WorkflowRuleResult`**. El runner persiste:
- `document_refs` — `{slot_name: [doc_ids]}` que alimentaron cada placeholder del prompt en esta combination.
- `document_refs_hash` — SHA256 canónico de `document_refs`. Sirve para dedup intra-run (evitar re-evaluar la misma combination en reintentos) y como clave de caché.

Esto le da a la UI granularidad para mostrar "esta cédula falló esto, esa otra falló aquello" sin tener que re-parsear el output del kind.

### 5.7 UX del editor — auto-narrowing de los campos del scope

`mode` y `on_empty` son **campos persistidos y explícitos** (necesarios para runtime determinístico y para que el usuario tenga override). Pero el **editor de reglas no debe pedir al usuario que elija entre opciones inválidas o tipear algo que el sistema ya sabe**.

**Filosofía común** para los dos campos:
1. El editor parsea el prompt en vivo (mismo análisis que `compile()`) y **acota las opciones** disponibles según lo que se pueda derivar.
2. El usuario **nunca ve el nombre técnico** del valor (`SINGLE_DOCUMENT`, `SKIPPED`, etc.) — ve la **consecuencia observable** del comportamiento.
3. **Heurísticas léxicas baratas** sugieren un default; el usuario siempre puede overridar.
4. **Nada de LLMs en el camino crítico** de la compilación: reglas mecánicas + override explícito.

#### 5.7.1 `mode`

Según cuántos doctype slugs únicos detecte el editor en el prompt:

| # doctypes en el prompt | Qué muestra el editor | Mode resultante |
|---|---|---|
| **0** | Campo oculto. Banner informativo: *"Esta regla aplica a todos los documentos del case"*. | `ALL_DOCUMENTS` (auto-fijado) |
| **1** | Toggle de 2 opciones:<br>○ "Un signal por cada documento"<br>○ "Un signal sobre el conjunto" | `SINGLE_DOCUMENT` o `AGGREGATE_OVER_TYPE` |
| **≥2** | Toggle de 2 opciones:<br>○ "Un signal por cada combinación"<br>○ "Un signal consolidado del case" | `TUPLE_CARTESIAN` o `ALL_DOCUMENTS` |

**Principios específicos:**
- El editor **nunca muestra modes inválidos** para el prompt actual. La tabla de coherencia de §5.4 deja de ser validación post-hoc y pasa a ser restricción del UI: el usuario no puede llegar a un estado incoherente.
- Cambiar el prompt **re-acota el toggle**. Si el usuario tenía `SINGLE_DOCUMENT` con 1 doctype y agrega un segundo doctype al prompt, el toggle se actualiza a las opciones válidas para 2 doctypes (manteniendo la intención cuando es posible — `SINGLE_DOCUMENT` → `TUPLE_CARTESIAN` por ser ambos "un signal por unidad iterada"; `AGGREGATE_OVER_TYPE` → `ALL_DOCUMENTS` por ser ambos "un signal consolidado").

**Sugerencia léxica** *(fase 2, opcional):*

| Patrones en el prompt | Pre-selección |
|---|---|
| "cada", "every", "todos los X cumplen" | "Un signal por cada documento" / "por cada combinación" |
| "total", "suma", "promedio", "conteo", "ningún", "alguno" | "Un signal sobre el conjunto" / "consolidado" |
| "el case tiene", "expediente completo", "están presentes" | "Un signal consolidado del case" |

#### 5.7.2 `on_empty`

A diferencia de `mode`, las opciones válidas de `on_empty` no dependen del prompt — dependen del **`mode` ya elegido**:

| `mode` actual | ¿Se muestra `on_empty`? | Por qué |
|---|---|---|
| `SINGLE_DOCUMENT` | ✓ Sí | El set se filtra por doctype → puede quedar vacío |
| `AGGREGATE_OVER_TYPE` | ✓ Sí | Idem |
| `TUPLE_CARTESIAN` | ✓ Sí | El producto cartesiano queda vacío si **algún slot** está vacío |
| `ALL_DOCUMENTS` | **✗ Oculto** | El set son todos los docs del case — un case sin docs no existe. `on_empty` es no-op estructural |

Cuando se muestra, las **3 opciones con labels semánticos**:
- ○ "No aplica si no hay documentos del tipo" → `SKIPPED` (default conservador)
- ○ "Falla si no hay documentos del tipo" → `FAILED`
- ○ "Pasa si no hay documentos del tipo" → `PASSED`

**Sugerencia léxica** *(fase 2, opcional):*

| Patrones en el prompt | Pre-selección |
|---|---|
| "debe tener", "debe existir", "al menos uno", "como mínimo" | "Falla si no hay documentos" |
| "no debe haber", "ningún", "no existe", "ausencia de" | "Pasa si no hay documentos" |
| Todo lo demás | "No aplica si no hay documentos" (default) |

**Hint sobre overloading** *(opcional, fase 2):* cuando el usuario elige "Falla" o "Pasa", el editor surfacea un nudge no-bloqueante:

> ⓘ Esta regla ahora hace dos trabajos: **validar contenido** + **verificar presencia**. Para mejor diagnóstico, considerá separarlas en dos reglas independientes — una `ALL_DOCUMENTS` para presencia y otra `SINGLE_DOCUMENT`/`AGGREGATE_OVER_TYPE` para validez.

#### 5.7.3 Por qué no dejar que un LLM deduzca estos campos

Tentador pero estrictamente inferior:
- **Frágil** — silent failures cuando malinterpreta el intent del prompt (ej. "el monto de la factura" puede ser SINGLE o AGGREGATE; el LLM va a adivinar y la UI saldrá rota).
- **No determinístico** — dos compilaciones del mismo texto podrían producir valores distintos.
- **Sin override claro** — si el LLM se equivoca, el usuario no tiene un campo donde corregirlo sin pelear contra la deducción.

Acotar en el editor con **reglas mecánicas + heurísticas léxicas + override explícito** preserva todas las ventajas (cero config burden cuando es obvio) sin las desventajas.

> **Esta sección define el contrato de comportamiento** que el editor debe respetar respecto al modelo del scope. El detalle visual completo (componentes, validaciones inline, estados de carga, accessibility) vive en `create-rules.md`.

---

## 6. Mini-pipeline interno de evaluación

Por cada `Combination` resuelta del scope, una regla pasa por hasta cinco etapas. **Cada etapa es opcional** y se decide por la combinación de defaults del kind y overrides del rule.

```
Combination
   │
   ├─[E1] resolución de inputs   ──── siempre
   │
   ├─[E2] pre-evaluación det.    ──── si artifact tiene sub-checks deterministic
   │      (puede cortocircuitar si el resultado ya está decidido)
   │
   ├─[E3] reviewer LLM N votos   ──── si quedan sub-checks llm
   │      self-consistency = N  (kind default, rule override)
   │
   ├─[E4] crítico cross-provider ──── si kind.supports_critic=True y rule.critic_enabled
   │      (opcional; mejora precisión a costo de latencia y $)
   │
   └─[E5] verificación citations ──── si kind.requires_citations=True
                                      (re-chequea que cada citation existe en el doc real)
```

### E1 — Resolución de inputs

El runner construye un `EvalInputs`:

```python
@dataclass
class EvalInputs:
    documents: list[EvalDocumentInput]      # docs del scope, con extracted_fields y text
    document_refs: dict[str, list[UUID]]    # slug → [doc_ids] que cae en cada slot
    knowledge_context: list[dict]           # KB docs resueltos (en compile o ad-hoc)
    tokens: dict[str, Any]                  # valores concretos de @-tokens
```

### E2 — Pre-evaluación determinística (target)

Ejecuta los sub-checks del artifact que están marcados como `deterministic` (regex, formato de RUT/CUIT, comparación de fechas, presencia de field, rango numérico). Hoy esto vive **embebido en `VALIDATION.evaluate`**; se externaliza para que cualquier kind pueda aprovecharlo.

**Cortocircuito:** si los sub-checks deterministicos ya determinan el resultado del árbol AND/OR (ej. un AND con un sub-check FAIL deterministic), la regla salta E3-E5 y emite el result directo. Costo cero, reproducible 100%.

### E3 — Reviewer LLM con self-consistency

Para los sub-checks que requieren razonamiento se invoca el LLM `N` veces en paralelo (default del kind, override por regla). Las respuestas se agregan por **mayoría sobre el output canónico**:

- Si `N=1` (default para kinds simples), no hay agregación — un solo LLM call.
- Si `N>=3`, la respuesta más común gana; en empate se elige la de mayor confianza self-reported.
- El reviewer puede tener **tools** (búsqueda en KB, lookup externo, etc.) declarados por el kind.

`evaluation_metadata` registra el `n`, los outputs individuales (anonimizados), y el winner — útil para auditoría y para entrenar.

### E4 — Crítico cross-provider (target, opcional)

Un segundo LLM **de proveedor distinto** recibe `(prompt, output_del_reviewer, evidencia)` y puede:
- **Confirmar** → el output del reviewer queda intacto.
- **Corregir** → propone un output revisado; si la corrección pasa validación contra el `output_schema`, reemplaza al del reviewer.
- **Disentir sin alternativa** → se marca `evaluation_metadata.critic_dissent=True` y el result baja `severity` un escalón (BLOCKER → MAJOR, etc.) por ambigüedad. No bloquea el run.

Solo aplica a kinds con `supports_critic=True` y reglas con `critic_enabled=True` en su config.

### E5 — Verificación post-hoc de citations (target)

Para cada `Citation` que el reviewer produjo, el verificador chequea que el span de texto / página realmente existe en el documento referenciado. Si una citation **no es verificable**:

- Si `kind.requires_citations=True` (kinds donde la citation es prueba del juicio): se reduce la `severity` un escalón y se anota en `evaluation_metadata.unverified_citations`.
- Si `False`: solo se anota; no se penaliza.

Es transversal: la implementación vive en un servicio compartido y opera sobre el output sin depender del kind.

### 6.6 Resumen de configurabilidad

| Etapa | Ejecuta si… | Default por kind | Override por regla |
|---|---|---|---|
| E1 | siempre | — | — |
| E2 | hay sub-checks deterministic en artifact | implícito | — |
| E3 | hay sub-checks llm pendientes | `default_self_consistency_n` | `rule.config.self_consistency_n` |
| E4 | `kind.supports_critic` ∧ `rule.config.critic_enabled` | False | True/False |
| E5 | `kind.requires_citations` | depende del kind | — |

---

## 7. Result, status y degradación

```python
class WorkflowRuleResult:
    uuid, tenant_id, workflow_analysis_run_id, rule_id, case_id: UUID
    kind: str
    status: WorkflowRuleResultStatus       # ver tabla
    output: dict | None                    # forma definida por kind.output_schema_for(rule)
    reasoning: str | None                  # texto libre, audit
    citations: list[Citation]              # spans verificables
    document_refs: dict[str, list[UUID]]   # qué docs alimentaron qué slot
    document_refs_hash: str                # SHA256 canónico — dedup intra-run
    rendered_prompt: str | None            # prompt final tras tokens, audit
    evaluation_metadata: dict              # timing, n_votes, critic_dissent, unverified_citations, etc.
    error: str | None                      # solo si status=ERRORED
```

### Statuses (target — colapso desde 4 a 3)

| Status | Significado | Aporta a dimensión | Cuenta en `degraded_rules` |
|---|---|:-:|:-:|
| `SUCCESS` | Evaluación completa con output válido. La polaridad PASS/FAIL/NEUTRAL la lleva el signal, no el status. | Sí | No |
| `ERRORED` | Excepción no recuperable (LLM crash, timeout, output inválido contra schema). | No | Sí |
| `SKIPPED` | Pre-condición no se cumplió (compilation no `READY`, scope vacío con `on_empty=SKIPPED`, dependency upstream falló). | No | Sí |

> **Cambio sobre lo existente:** hoy hay además un status `FAILED` que se solapa con `polarity=FAIL` del signal. Es ambiguo (¿el LLM "falló" o el check resultó en FAIL?). Se elimina: la polaridad va siempre en el signal del result `SUCCESS`.

### `confidence_score`

```
confidence_score = |SUCCESS| / |total_results|     ∈ [0, 1]
```

Aparece en el summary y baja por cada `ERRORED` o `SKIPPED`.

---

## 8. Reparto a las dimensiones del summary

El runner ejecuta cada regla **una sola vez**. La proyección a una dimensión u otra se decide por el flag `produces_enrichment` del kind. Esto **no es paralelismo**, es proyección.

```python
async def evaluate_workflow(workflow, run_ctx) -> tuple[list[WorkflowRuleResult], list[VerdictSignal], list[EnrichmentBlock]]:
    results: list[WorkflowRuleResult] = []
    signals: list[VerdictSignal] = []
    enrichments: list[EnrichmentBlock] = []

    # Reglas en paralelo con concurrency bound (ver §10)
    raw_results = await gather_with_limit(
        [_run_rule(r, run_ctx) for r in workflow.rules],
        limit=RULES_CONCURRENCY,
    )
    for rule, result in zip(workflow.rules, raw_results):
        results.append(result)
        if result.status is not WorkflowRuleResultStatus.SUCCESS:
            continue
        kind = registry.get(rule.kind)
        if kind.produces_enrichment:
            enrichments.append(EnrichmentBlock(
                rule_id=rule.uuid,
                rule_label=rule.label,           # denormalizado para SYNTHESIZE — ver general.md §6
                kind=kind.name,
                output=result.output,
                citations=result.citations,
                document_refs=result.document_refs,
            ))
        else:
            if signal := kind.contribute_to_verdict(rule, result):
                signals.append(signal)

    return results, signals, enrichments
```

Notas:
- Una regla con `produces_enrichment=True` **no** llama `contribute_to_verdict`. Aunque `contribute_to_verdict` esté en el Protocol, el runner no lo invoca para kinds de Enrichment — y los kinds de Enrichment pueden devolver `None` constante.
- `contribute_to_verdict` devuelve **a lo sumo un signal por result** — si un kind quiere emitir varios "veredictos", debe modelar cada uno como una regla distinta o como entradas dentro de `signal.detail`.
- Si `len(workflow.rules) == 0`, el runner se skipea entero (`EVALUATE` no corre, ver `general.md` §2).

---

## 9. Agregación del verdict

El verdict es una función pura de `(signals, results)`:

```python
@dataclass(frozen=True)
class VerdictBundle:
    verdict: Verdict                     # PASS | REVIEW | FAIL
    signals: list[SignalSnapshot]
    signals_by_polarity: dict[str, int]
    signals_by_severity: dict[str, int]
    blocking_failures: list[UUID]        # rule_ids con polarity=FAIL ∧ severity=BLOCKER
    degraded_rules: list[UUID]           # status ∈ {ERRORED, SKIPPED}
    confidence_score: float | None
```

Algoritmo (fija el target — hoy `verdict_logic.py` ya implementa lo principal):

1. Si `blocking_failures` no está vacío → **`FAIL`**.
2. Si `degraded_rules / total_rules > degraded_threshold` (default `0.5`) → **`REVIEW`**.
3. Si hay algún signal con `polarity=FAIL` y `severity in {MAJOR, MINOR}` → **`REVIEW`**.
4. Si todos los signals son `PASS` o `NEUTRAL` → **`PASS`**.
5. Caso degenerado (no hay signals y no hay degradación): **`verdict=None`** (ver `general.md` — Caso 5 Circulares).

`degraded_threshold` es **configurable a nivel workflow** (default `0.5`) — un workflow crítico puede subirlo a `0.1` para enviar a review ante cualquier degradación; uno tolerante puede bajarlo a `0.9`.

### 9.1 Cierre de `EVALUATE` — frontera con `SYNTHESIZE`

**`EVALUATE` termina exactamente cuando el `VerdictBundle` está computado**, no cuando los results individuales se persisten. La secuencia de cierre es:

```
1. Todas las (rule × combination) terminan       → list[WorkflowRuleResult] persistidos
2. Por cada SUCCESS de Validation:               → kind.contribute_to_verdict() → VerdictSignal
   Por cada SUCCESS de Enrichment:               → proyección output → EnrichmentBlock
3. VerdictAggregator.aggregate(signals, results) → VerdictBundle
4. WorkflowAnalysisRunSummary se arma con:       (verdict, signals, enrichment_blocks,
                                                  degraded_rules, confidence_score)
   ─────────────────────────────────────────────  ← AQUÍ TERMINA EVALUATE
5. SYNTHESIZE recibe ese summary como input
```

**Por qué la frontera está en (3-4) y no en (1):**
- Sin `VerdictBundle`, el output de EVALUATE está incompleto — el verdict, `degraded_rules` y `confidence_score` son tan parte del output como los signals.
- `SYNTHESIZE` consume el summary completo para componer el `output_schema`. Si la frontera estuviera antes, habría que duplicar la lógica de agregación o pasarle a SYNTHESIZE results crudos.
- La agregación es **pura y barata** (microsegundos): no tiene sentido conceptual ni operacional separarla.

**Implementación actual:** el hook `regenerate_on_run_complete.py` se dispara cuando el `WorkflowAnalysisRun` pasa a `COMPLETED`. Ese hook ejecuta secuencialmente:

1. `VerdictAggregator.execute()` — paso (3-4) de arriba. Si falla → el run queda con summary incompleto y se loggea.
2. `SynthesisRunner.enqueue()` — dispara `SYNTHESIZE` con el summary ya armado. Soft-fail: si falla, el verdict ya está disponible.

> **Nota:** esta frontera es secuencial, no concurrente. No tiene sentido empezar `SYNTHESIZE` antes de tener `VerdictBundle` porque su input lo necesita completo. Si en el futuro `SYNTHESIZE` se vuelve caro y queremos paralelizar partes que no dependen del verdict (ej. extracción puro de campos), eso sería un rediseño de SYNTHESIZE, no un movimiento de la frontera.

---

## 10. Concurrencia y orden

- **Reglas dentro de `EVALUATE`** corren en paralelo con `asyncio.gather` y un **`RULES_CONCURRENCY`** bound (default `8`, configurable por workflow). El bound existe para no saturar al provider de LLM ni al pool de DB.
- **Etapas dentro de una regla** son secuenciales (E1→E5). Solo E3 (los N votos del reviewer) corre en paralelo internamente.
- **Orden estable** de `signals[]` y `enrichment_blocks[]` en el summary: el del orden de `workflow.rules` (no el de finalización). El runner mantiene el zip `(rule, result)`.
- **Cancelación:** si el `WorkflowAnalysisRun` pasa a `CANCELING`, las reglas en vuelo se interrumpen; los results ya persistidos quedan, no se rollbackean. La agregación corre solo si el run llega a `COMPLETED`.

---

## 11. Cambios sobre el código existente

| # | Cambio | Motivo | Breaking |
|---|---|---|:-:|
| 1 | Agregar `produces_enrichment: bool` al Protocol del kind. | Hace explícito el reparto a dimensiones; permite validar workflows. | No (default `False`) |
| 2 | Agregar `detail_schema: dict` al Protocol del kind. | Validar `signal.detail`; documentar la forma para la UI. | No (default `{}` permisivo) |
| 3 | Agregar `default_self_consistency_n`, `supports_critic`, `requires_citations`. | Mover decisiones del código del kind al Protocol declarativo. | No |
| 4 | **Eliminar `WorkflowRuleResultStatus.FAILED`.** Usar solo `SUCCESS / ERRORED / SKIPPED` + `polarity` en el signal. | Ambigüedad entre "evaluación falló" y "el check dio FAIL". Migración: results con `FAILED` se releen como `SUCCESS` con polarity FAIL. | **Sí** (DB migration) |
| 5 | Externalizar la pre-evaluación determinística a un servicio compartido. | Hoy vive embebida en `VALIDATION.evaluate`; otros kinds deterministicos la necesitan. | No (refactor interno) |
| 6 | Agregar etapa de crítico cross-provider como servicio compartido. | Inexistente hoy; opt-in por kind+regla. | No |
| 7 | Agregar etapa de verificación post-hoc de citations. | Hoy solo se persisten; no se chequea que existan en el documento. | No |
| 8 | `verdict_logic.degraded_threshold` configurable a nivel workflow. | Hoy hardcodeado a `0.5`. | No (default igual) |
| 9 | Bound de concurrencia (`RULES_CONCURRENCY`) configurable por workflow. | Hoy las reglas corren secuencial; paralelizar con bound es la mejora. | No |
| 10 | `kind.contribute_to_verdict` no se invoca para kinds con `produces_enrichment=True`. | Coherencia con §8; evita que un kind de Enrichment empuje signals "por accidente". | No |
| 11 | Sumar tokens de sistema `{{<system_var>}}` (catálogo inicial: `{{now}}`). | Habilita reglas con contexto temporal (ej. "este documento no debe tener más de 90 días respecto a `{{now}}`"); base extensible para futuras vars sin re-tocar el parser. | No (sintaxis nueva) |
| 12 | **Eliminar `target_doctype` y `tuple_slots` del modelo del scope.** El scope se reduce a `(mode, on_empty)`; los doctypes que la regla necesita se derivan del prompt en `compile()`. | Una sola fuente de verdad (el prompt). Hoy el doctype puede vivir en config + prompt y desincronizarse — vector de errores silenciosos. | **Sí** (DB migration: drop columnas; re-compilar reglas existentes para extraer doctypes del prompt al `artifact`) |
| 13 | Sumar marker `@<doctype_slug>` (sin field path) como token válido del prompt. | Permite reglas per-doc genéricas (`SINGLE_DOCUMENT` / `AGGREGATE_OVER_TYPE`) cuyo prompt no necesita referenciar un field específico, sin reintroducir `target_doctype`. | No (sintaxis nueva) |

---

## 12. Glosario específico de `EVALUATE`

- **Combination** — una asignación concreta de documentos a los slots del scope de una regla. Una regla con `scope.mode=TUPLE_CARTESIAN` sobre `(cedula × poliza)` produce `|cedulas| × |polizas|` combinations, y por ende `|cedulas| × |polizas|` results.
- **`document_refs`** — diccionario `{slot_name: [document_ids]}` que dice qué documentos alimentaron qué placeholder del prompt en una combination concreta. Se persiste en el result para trazabilidad.
- **`document_refs_hash`** — SHA256 canónico de `document_refs`. Usado para dedup intra-run (evitar re-evaluar la misma combination si hay reintentos) y como clave de caché.
- **Compilation artifact** — el blob `dict` que produce `kind.compile()`; forma libre, definida por el kind. Es el insumo de `kind.evaluate()`.
- **`compiled_with`** — metadata de qué referencias externas (doc types, KB docs) se usaron al compilar. Si alguna cambia, la compilation pasa a `STALE`.
- **Sub-check** — nodo del árbol AND/OR que produce el artifact de un kind tipo `VALIDATION`. Cada sub-check es `deterministic` o `llm`. Los deterministic se evalúan en E2; los `llm` en E3.
- **Self-consistency** — técnica de invocar el mismo prompt al LLM `N` veces y agregar por mayoría. Reduce varianza a costo de N× latencia y costo. Se configura por kind (default) y por regla (override).
- **Crítico cross-provider** — segundo LLM de un proveedor distinto al del reviewer, que revisa el output del primero. Etapa E4.
- **Citation verificada** — un span de texto (página + bbox o offsets) que efectivamente existe en el documento referenciado tras chequearlo en E5. Citations no verificadas no eliminan el result, solo bajan severity.
- **Polarity** — `PASS / FAIL / NEUTRAL` que lleva un signal. Distinta del `status` del result. Solo aplica a kinds de Validation.
- **Severity** — `BLOCKER / MAJOR / MINOR / INFO`. Decide el peso del signal en la agregación; un solo `FAIL + BLOCKER` fuerza `verdict=FAIL`.
- **Degraded rule** — regla cuyo result terminó `ERRORED` o `SKIPPED`. Entra a `degraded_rules`, no aporta a dimensiones, baja `confidence_score`, y empuja al verdict hacia `REVIEW` si supera el `degraded_threshold` del workflow.
