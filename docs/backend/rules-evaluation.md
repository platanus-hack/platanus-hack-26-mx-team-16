# Mini-pipeline de evaluación de una `WorkflowRule`

> Doc educativa sobre **cómo se evalúa una regla por dentro** durante la fase `EVALUATE` del pipeline.
> Pensada para que un desarrollador nuevo entienda el flujo paso a paso, vea ejemplos concretos
> y pueda razonar sobre costos, modos de fallo y observabilidad.
>
> El **spec normativo** (Protocol del kind, esquemas, target model) vive en
> [`product/specs/pipeline/phase_evaluate.md`](../../product/specs/pipeline/phase_evaluate.md). Este documento es la
> versión narrativa con worked examples — si encontrás divergencia, manda el spec.

---

## 1. Visión general

Cuando la fase `EVALUATE` arranca, el runner toma cada `WorkflowRule` configurada en el workflow y, por cada `Combination` que produce su scope, la pasa por **hasta cinco etapas**:

```
Combination
   │
   ├─[E1] resolución de inputs    ──── siempre
   │
   ├─[E2] pre-evaluación det.     ──── si artifact tiene sub-checks deterministic
   │      (puede cortocircuitar si el resultado ya está decidido)
   │
   ├─[E3] reviewer LLM N votos    ──── si quedan sub-checks llm
   │      self-consistency = N   (kind default, rule override)
   │
   ├─[E4] crítico cross-provider  ──── si kind.supports_critic=True y rule.critic_enabled
   │      (opcional; mejora precisión a costo de latencia y $)
   │
   └─[E5] verificación citations  ──── si kind.requires_citations=True
                                       (re-chequea que cada citation existe en el doc real)
```

**Cada etapa es opcional.** Una regla simple es una sola llamada al LLM (E1 + E3); una regla cara puede pasar las cinco. El usuario nunca paga más de lo que su caso necesita.

### Por qué este orden

Las etapas están deliberadamente ordenadas por dos ejes:

```
       más barato  →  más caro
       más determinístico  →  más probabilístico
       
       E1     E2          E3            E4              E5
       (i/o)  (cpu/regex) (LLM × N)     (LLM otro proveedor)  (i/o + comparación)
       µs     µs–ms       segundos      segundos              ms
```

La consecuencia es que **el sistema corta lo antes posible**. Si en E2 ya quedó decidido el árbol AND/OR, no se gasta nada en E3 — y si E3 es suficiente, no se invoca el crítico de E4.

---

## 2. Las cinco etapas en detalle

### E1 — Resolución de inputs

**Cuándo corre:** siempre. Es plumbing del runner, no del kind.

**Qué hace:** construye el `EvalInputs` que el kind va a recibir, juntando información de múltiples fuentes:

```python
EvalInputs(
    documents          = [...],   # docs del scope, con extracted_fields y text
    document_refs      = {...},   # slug → [doc_ids] que cae en cada slot
    knowledge_context  = [...],   # KB docs resueltos durante compile()
    tokens             = {...},   # valores concretos de los @-tokens
)
```

- Los `documents` salen del `scope_resolver` aplicado al case.
- Los `document_refs` mapean cada slot del prompt a los doc_ids que lo alimentaron.
- El `knowledge_context` viene del `compiled_with` (KB docs ya resueltos en `compile()`) y/o lookups ad-hoc declarados por el kind.
- Los `tokens` son los valores resueltos: `@cedula.numero_documento` → `"12345678-K"`, `{{now}}` → `"2026-05-06T..."`, etc.

**Modos de fallo:**
- Si la `compilation` no está `READY` (está `FAILED` o `STALE`) → el runner aborta con `status=SKIPPED`. Las etapas E2-E5 no corren.
- Si un token no se puede resolver (ej. `@cedula.x` pero el doc no tiene field `x` extraído) → según política del kind: o se sustituye por `null` y se loggea, o aborta como `status=ERRORED`.

---

### E2 — Pre-evaluación determinística

**Cuándo corre:** si el `artifact` de la compilation tiene sub-checks marcados como `deterministic`.

**Qué hace:** ejecuta esos sub-checks **sin invocar al LLM**. Tipos típicos:

| Sub-check | Implementación |
|---|---|
| Regex / pattern match (RUT, email, etc.) | `re.match()` |
| Comparación de fechas (≤, ≥, rango) | `datetime` comparisons |
| Rango numérico (≥ x, entre [a,b]) | aritmética simple |
| Presencia/ausencia de field | `field in extracted` |
| Checksum (RUT, CUIT, IBAN) | función validadora |
| Igualdad estructural | `==` |

Cada sub-check produce `{check_id, outcome: PASS|FAIL, value, expected}`.

**Cortocircuito:** después de evaluar los deterministicos, el runner mira el árbol AND/OR:

- Árbol `AND(...)` con algún sub-check `FAIL` deterministic → **outcome = FAIL** ya está decidido. Se emite el result y se saltan E3-E5.
- Árbol `OR(...)` con algún sub-check `PASS` deterministic → **outcome = PASS** decidido. Se saltan E3-E5.
- En otro caso → quedan sub-checks `llm` por evaluar; pasa a E3.

**Modos de fallo:**
- Excepción inesperada en un sub-check determinístico (ej. el regex es inválido — pero esto debió fallar en `compile()`) → `status=ERRORED`.
- Si todos los sub-checks son `llm` y no hay deterministicos → E2 no corre, pasa directo a E3.

> **Hoy esto vive embebido en `VALIDATION.evaluate`.** El target del spec es externalizar E2 a un servicio compartido para que cualquier kind con sub-checks pueda aprovecharlo.

---

### E3 — Reviewer LLM con self-consistency N

**Cuándo corre:** si quedan sub-checks `llm` después de E2.

**Qué hace:** invoca al LLM **N veces en paralelo** con el mismo prompt y agrega las respuestas por mayoría. `N` se llama el **factor de self-consistency**:

- `N` lo define el kind (`default_self_consistency_n`).
- La regla puede overridarlo en su `config.self_consistency_n`.
- Para kinds simples `N=1` (un solo call). Para kinds donde la varianza importa (`SCORING`, `CLASSIFICATION`), `N=5` o más.

**Estructura del prompt al LLM:**
- System prompt del kind (fijo, define el formato de salida).
- Sub-checks pendientes serializados como instrucciones.
- Tokens resueltos inyectados literalmente.
- Documentos del scope (texto OCR, opcionalmente con bounding boxes).
- KB context relevante.
- Tools disponibles (búsqueda KB, lookup externo, etc.) según el kind.

**Agregación de votos:**
- Cada voto produce un output que respeta el `output_schema` del kind.
- Para outputs idénticos → mayoría simple.
- Para outputs con variación menor (ej. citations apuntan a líneas distintas pero mismo PASS/FAIL) → mayoría sobre el outcome canónico (`tree_outcome` + `polarity`); las citations se acumulan/depuran.
- En empate (raro con N impar) → se elige la respuesta de mayor confianza self-reported, o se anota `evaluation_metadata.tied_vote=True` y se baja severity un escalón.

**Modos de fallo:**
- Timeout o error transient del provider → reintento con backoff (configurable).
- Más de la mitad de los votos fallan → `status=ERRORED`.
- Output que no valida contra `output_schema` → `status=ERRORED`, `error="output schema violation: ..."`.

**`evaluation_metadata` registra:**
- `n_votes` ejecutados.
- Resumen anonimizado de cada voto (modelo, latencia, outcome).
- Voto ganador.
- Tools invocados y resultado (si aplica).

---

### E4 — Crítico cross-provider (opcional)

**Cuándo corre:** si `kind.supports_critic=True` **y** `rule.critic_enabled=True`.

**Qué hace:** un **segundo LLM, de un proveedor distinto** al del reviewer, recibe `(prompt original, output del reviewer, evidencia)` y emite uno de tres veredictos:

| Veredicto del crítico | Efecto |
|---|---|
| **Confirmar** | Output del reviewer queda intacto. `evaluation_metadata.critic_dissent=False`. |
| **Corregir** | El crítico propone un output revisado. Si pasa el `output_schema`, **reemplaza** al output del reviewer. Se anotan ambas versiones para auditoría. |
| **Disentir sin alternativa** | El crítico no está de acuerdo pero no propone alternativa concreta. Se baja `severity` un escalón (BLOCKER → MAJOR, MAJOR → MINOR), `evaluation_metadata.critic_dissent=True`. No bloquea el run. |

**Por qué cross-provider:** errores correlacionados entre llamadas al mismo modelo se detectan poco con self-consistency (el modelo equivoca igual en cada voto). Un proveedor distinto rompe esa correlación.

**Pares típicos:**
- Reviewer Anthropic Claude ↔ Crítico OpenAI GPT
- Reviewer OpenAI GPT ↔ Crítico Google Gemini
- Reviewer Anthropic Claude ↔ Crítico DeepSeek

**Modos de fallo:**
- Crítico falla (timeout, error) → se loggea, output del reviewer queda intacto, `evaluation_metadata.critic_unavailable=True`. **No bloquea el result.**

---

### E5 — Verificación post-hoc de citations

**Cuándo corre:** si `kind.requires_citations=True`.

**Qué hace:** para cada `Citation` que el output declara, chequea que el span/página/bbox **realmente existe en el documento referenciado**:

```python
class Citation:
    document_id: UUID         # qué doc (case o KB)
    page: int | None          # página
    bbox: tuple | None        # bounding box (x1, y1, x2, y2) si aplica
    text_span: str | None     # texto literal citado
    offset: tuple | None      # offsets en el text OCR (start, end)
```

Para cada citation:
1. Carga el doc referenciado.
2. Si tiene `text_span`: chequea que el string aparece en el OCR del doc/página declarada (con normalización de whitespace y typos toleradas dentro de un threshold).
3. Si tiene `bbox`: chequea que la bounding box cae dentro de las dimensiones de la página.
4. Si tiene `offset`: chequea que es un rango válido del OCR text.

**Resultado por citation:** `verified` o `unverified`.

**Política para citations no verificadas:**
- Se anotan en `evaluation_metadata.unverified_citations = [citation_index, ...]`.
- Si `kind.requires_citations=True` (la citation es prueba del juicio) → se baja `severity` un escalón.
- Si `False` (la citation es informativa) → solo se loggea, sin penalización.

**No se elimina el result** ni se marca como `ERRORED` por citations malas — el output ya contiene info útil; lo que cambia es la confianza.

---

## 3. Worked examples

### Setup compartido

**Regla:** *"Validar la cédula del solicitante"* — kind `VALIDATION`, `mode=SINGLE_DOCUMENT`.

**Sub-checks compilados** (artifact que produjo `compile()`):

```
AND
├── ① RUT formato válido (^\d{1,8}-[\dKk]$)         [DETERMINISTIC]
├── ② fecha_nacimiento ≤ {{now}}                    [DETERMINISTIC]
├── ③ nombre coincide con titular de #contrato_marco [LLM]
└── ④ la firma manuscrita está visible              [LLM]
```

**Config:**
- `self_consistency_n = 3` (rule override; kind default era 1).
- `kind.supports_critic = True` y `rule.critic_enabled = True`.
- `kind.requires_citations = True` (sub-check ③ hace claims sobre páginas).

**Case:** 1 cédula de Pedro García + el documento `contrato_marco` está en el KB.

---

### Caso A — Happy path: corren las 5 etapas

#### E1 — Resolución de inputs

```python
EvalInputs(
    documents = [EvalDocumentInput(
        doc_id=...,
        extracted_fields={
            "numero_documento": "12345678-K",
            "fecha_nacimiento": "1985-04-12",
            "nombre": "Pedro García"
        },
        text="...",
    )],
    document_refs     = {"cedula": [pedro_cedula_uuid]},
    knowledge_context = [{"slug": "contrato_marco", "text": "...titular: Pedro García..."}],
    tokens            = {
        "cedula.numero_documento": "12345678-K",
        "cedula.fecha_nacimiento": "1985-04-12",
        "cedula.nombre": "Pedro García",
        "now": "2026-05-06T12:00:00Z",
    },
)
```

#### E2 — Pre-evaluación determinística

- **①** `re.match(r"^\d{1,8}-[\dKk]$", "12345678-K")` → **PASS** ✓
- **②** `date("1985-04-12") <= date("2026-05-06")` → **PASS** ✓

Estado del árbol: `AND(PASS, PASS, ?, ?)`. **No hay cortocircuito** porque el AND aún puede fallar por ③ o ④ → pasa a E3.

> Costo de E2: cero LLM, ~µs.

#### E3 — Reviewer LLM con self-consistency N=3

Se construye el prompt para los sub-checks ③ y ④ y se lanzan **3 calls paralelos**:

| Voto | Modelo | sub-check ③ | sub-check ④ |
|---|---|---|---|
| A | Claude Opus | PASS (cita: contrato_marco p.1 l.4) | PASS (cita: cédula p.2) |
| B | Claude Opus | PASS (cita: contrato_marco p.1 l.4) | PASS (cita: cédula p.2) |
| C | Claude Opus | PASS (cita: contrato_marco p.1 l.5) | FAIL ("firma borrosa") |

**Mayoría:** ③ PASS (3/3), ④ PASS (2/3). Estado del árbol: `AND(PASS, PASS, PASS, PASS)` → **PASS**.

```python
evaluation_metadata = {
    "n_votes": 3,
    "vote_breakdown": {"③": {"PASS": 3, "FAIL": 0}, "④": {"PASS": 2, "FAIL": 1}},
    "winner": "vote_A",
    ...
}
```

#### E4 — Crítico cross-provider

Se invoca a **GPT-5** (otro proveedor) con `(prompt, output_del_reviewer, docs)`:

→ Crítico **confirma**. `evaluation_metadata.critic_dissent = False`.

Si hubiera disentido, el `severity` del signal final habría bajado un escalón.

#### E5 — Verificación post-hoc de citations

| Citation | Doc | Check | Resultado |
|---|---|---|---|
| `contrato_marco` p.1 l.4 (text_span="titular: Pedro García") | KB | string en OCR de p.1 | ✓ verified |
| `cedula` p.2 (bbox firma) | case | bbox dentro de página 2 | ✓ verified |

Todas verificadas → no se penaliza.

#### Result final

```python
WorkflowRuleResult(
    status        = SUCCESS,
    output        = {
        "tree_outcome": "PASS",
        "sub_checks": [{"id": "①", "outcome": "PASS"}, ...]
    },
    citations     = [...verified...],
    document_refs = {"cedula": [pedro_cedula_uuid]},
    evaluation_metadata = {
        "n_votes": 3,
        "critic_dissent": False,
        "unverified_citations": [],
        "stage_timings": {"E1": 12, "E2": 3, "E3": 8420, "E4": 2150, "E5": 45},  # ms
        "shortcircuited_at": None,
    },
)
```

→ `kind.contribute_to_verdict(rule, result)` produce:

```python
VerdictSignal(
    polarity = PASS,
    severity = MAJOR,
    detail   = {"tree_outcome": "PASS", "sub_checks": [...], "drivers": [...]}
)
```

---

### Caso B — Fast path: cortocircuito en E2

**Misma regla, mismo case, pero la cédula tiene `numero_documento = "abc123"`** (RUT mal formado).

- **E1** — igual que en Caso A.
- **E2** — sub-check ① regex contra `"abc123"` → **FAIL** ✗
  - El árbol es `AND(...)`: con un FAIL determinístico, el outcome ya está decidido sin importar ③ y ④.
  - **Cortocircuito** → se emite el result directo.
- **E3, E4, E5** — **no se ejecutan**. Cero LLM calls.

```python
WorkflowRuleResult(
    status   = SUCCESS,
    output   = {"tree_outcome": "FAIL", "failed_sub_checks": ["①"]},
    citations = [],
    evaluation_metadata = {
        "shortcircuited_at": "E2",
        "stage_timings": {"E1": 12, "E2": 4},
    },
)

VerdictSignal(polarity=FAIL, severity=BLOCKER, detail={...})
```

**Costo total:** ~ms. Reproducible al 100%.

---

### Caso C — Kind de Enrichment sin sub-checks (DERIVATION)

**Regla:** *"Extraer el listado de items facturados como JSON"* — kind `DERIVATION`, `mode=AGGREGATE_OVER_TYPE`, target `factura`.

**Diferencias clave con `VALIDATION`:**
- `produces_enrichment = True` → el result va a `enrichment_blocks`, no a `signals`.
- El artifact **no tiene árbol AND/OR de sub-checks** — tiene un `output_schema` (lo que el LLM debe extraer) + un prompt template.
- **No hay E2:** sin sub-checks deterministicos, se salta directo a E3.

**Pipeline efectivo:**
- **E1** ✓ — construye inputs con la lista completa de facturas.
- **E2** ✗ — salteada (no hay sub-checks).
- **E3** ✓ — un solo call (`N=1` default para DERIVATION) con structured generation forzando el `output_schema`.
- **E4** ✗ — `kind.supports_critic = False` para este kind.
- **E5** ✓ — `kind.requires_citations = True` (cada item del JSON debe citar la página de la factura). Las citations no verificadas no bajan severity (no hay severity en Enrichment), solo se loggean.

**Result final:**

```python
WorkflowRuleResult(
    status = SUCCESS,
    output = {
        "items": [
            {"desc": "Honorarios profesionales", "monto": 12500, "page": 1},
            {"desc": "Movilización", "monto": 3200, "page": 2},
        ],
        "total": 15700,
    },
    citations = [...],
    evaluation_metadata = {"n_votes": 1, "stage_timings": {"E1": 8, "E3": 4200, "E5": 30}},
)
```

→ Va a `summary.enrichment_blocks` como un `EnrichmentBlock`.

---

## 4. Configuración por kind y por regla

| Variable | Define el kind | Override en la regla |
|---|---|---|
| `default_self_consistency_n` | ✓ | `rule.config.self_consistency_n` |
| `supports_critic` | ✓ (booleano) | — |
| `critic_enabled` | — | ✓ `rule.config.critic_enabled` (solo si `supports_critic=True`) |
| `requires_citations` | ✓ | — |
| `produces_enrichment` | ✓ | — |
| Severity / weight del signal | — | ✓ `rule.severity`, `rule.weight` |
| `on_empty` | — | ✓ `rule.scope.on_empty` |

> **Regla mental:** decisiones que cambian el shape o la semántica del output → del kind. Decisiones que ajustan el costo/precisión para un caso particular → de la regla.

---

## 5. Caching y dedup

Cada `WorkflowRuleResult` lleva un `document_refs_hash` (SHA256 canónico de `document_refs`). Sirve para:

- **Dedup intra-run:** si el runner se reintenta sobre el mismo set de combinations (ej. crash recovery), no se re-evalúan combinations que ya tienen result persistido con el mismo hash.
- **Caché cross-run** *(target, no implementado hoy):* si el mismo `document_refs_hash` apareció en un run previo del mismo workflow + misma `compilation.uuid`, se puede reutilizar el result anterior. Útil cuando un case se re-corre por cambio de una sola regla.

---

## 6. Modos de fallo por etapa

| Etapa | Falla → result |
|---|---|
| E1 | `status=SKIPPED` si compilation no `READY`. `status=ERRORED` si token unresolvable y kind no tolera nulls. |
| E2 | `status=ERRORED` si excepción en sub-check determinístico (raro — debió fallar en `compile()`). |
| E3 | Reintento con backoff configurable. Si >50% de votos fallan → `status=ERRORED`. Si output viola `output_schema` → `status=ERRORED`. |
| E4 | **Soft-fail**: si crítico no responde, output del reviewer queda; `evaluation_metadata.critic_unavailable=True`. |
| E5 | **Soft-fail**: citations no verificadas no eliminan el result, solo bajan severity (cuando `requires_citations=True`). |

**Reglas con `status=ERRORED` o `SKIPPED`** entran a `degraded_rules` del summary, bajan `confidence_score`, y empujan el verdict hacia `REVIEW` si superan el `degraded_threshold` del workflow (default `0.5`). No aportan a `signals` ni a `enrichment_blocks`.

---

## 7. Observabilidad — qué queda en `evaluation_metadata`

Estructura típica del jsonb:

```python
evaluation_metadata = {
    # Timing
    "stage_timings": {"E1": 12, "E2": 3, "E3": 8420, "E4": 2150, "E5": 45},  # ms

    # Cortocircuito
    "shortcircuited_at": None,  # o "E2" si E2 cortó

    # Self-consistency
    "n_votes": 3,
    "vote_breakdown": {"③": {"PASS": 3, "FAIL": 0}, "④": {"PASS": 2, "FAIL": 1}},
    "winner_vote_index": 0,
    "tied_vote": False,

    # Crítico
    "critic_dissent": False,
    "critic_unavailable": False,
    "critic_changes": None,  # diff vs reviewer si hubo correcciones

    # Citations
    "unverified_citations": [],  # índices de citations que fallaron E5

    # Modelos
    "models_used": {
        "reviewer": "claude-opus-4-7",
        "critic":   "gpt-5",
    },
    "token_counts": {"input": 1850, "output": 320},
}
```

Esta info es **invaluable para auditoría** (¿por qué este result?), **debugging de regresiones** (¿el modelo cambió de comportamiento?), y **entrenamiento** (qué prompts producen votos divergentes).

---

## 8. Performance — guidelines prácticas

| Configuración | Latencia típica | Costo (LLM) |
|---|---|---|
| Solo deterministicos (cortocircuito en E2) | ~ms | $0 |
| `N=1`, sin crítico, sin citations | 5-10 s | 1× |
| `N=3`, sin crítico | 8-15 s | 3× |
| `N=5`, con crítico, con citations | 15-30 s | 6× |
| Worst case: regla pesada × case con 50 combinations | minutos | 300× |

**Cuándo enableable cada feature:**
- **`N>1`** — kinds donde la varianza del LLM cambia el outcome con frecuencia (`SCORING`, `CLASSIFICATION`, `LLM_VOTING`).
- **Crítico cross-provider** — reglas críticas para el negocio (`BLOCKER` severity), o cuando se detectó históricamente desacuerdo entre runs.
- **Verificación de citations** — siempre que las citations se muestren en la UI o se usen para audit. Costo bajo, valor alto.

**Cómo bajar costos:**
1. Maximizar sub-checks deterministicos en compilación (más cortocircuitos en E2).
2. Bajar `N` a 1 para reglas estables.
3. Desactivar crítico para reglas no críticas.
4. Aumentar `RULES_CONCURRENCY` a nivel workflow para paralelizar más reglas (sin reducir costo total, pero baja latencia wall-clock).

---

## 9. Cierre de `EVALUATE` — qué pasa cuando todas las reglas terminan

El mini-pipeline E1-E5 corre **por cada combination de cada regla**. Cuando la última combination de la última regla termina, el runner **todavía no terminó EVALUATE** — falta el paso de cierre.

### La secuencia completa

```
[A] Para cada (rule × combination) → mini-pipeline E1-E5 → WorkflowRuleResult persistido
        │
        ├─ Validation kinds:  kind.contribute_to_verdict() → VerdictSignal (en memoria)
        └─ Enrichment kinds:  proyección output → EnrichmentBlock (en memoria)
        │
        ▼
[B] VerdictAggregator.execute()
        │
        └─ verdict_logic.aggregate(signals, results) → VerdictBundle:
              ├─ verdict           = PASS | REVIEW | FAIL
              ├─ signals           = [SignalSnapshot, ...]
              ├─ blocking_failures = [rule_id, ...]   # FAIL + BLOCKER
              ├─ degraded_rules    = [rule_id, ...]   # ERRORED o SKIPPED
              ├─ confidence_score  = |SUCCESS| / |total|
              └─ signals_by_polarity / signals_by_severity
        │
        ▼
[C] WorkflowAnalysisRunSummary se arma con:
        (verdict, signals, enrichment_blocks, degraded_rules, confidence_score)

    ──────────────────────────────────────────────  ← AQUÍ TERMINA EVALUATE
        │
        ▼
[D] SYNTHESIZE arranca con el summary como input
```

### Por qué la frontera está en [B-C], no en [A]

Una pregunta natural es: "¿no termina EVALUATE cuando se generan los signals?" Casi — pero el output observable de EVALUATE incluye más que signals individuales:

- El **verdict** es el dato más importante para el cliente; sin él el run no es útil.
- `degraded_rules` y `confidence_score` cuentan **cuán confiable** fue el run; si más de la mitad de las reglas degradaron, el verdict pasa a `REVIEW`.
- Sin agregación, `SYNTHESIZE` recibiría signals crudos y tendría que computar el verdict por su cuenta — duplicación.

Como `verdict_logic.aggregate()` es **pura y barata** (microsegundos: solo cuenta signals por polaridad/severity y aplica reglas de decisión), no hay razón operacional para separarla en una "fase" propia. Conceptualmente es **el último paso de EVALUATE**.

### Algoritmo del verdict (resumen)

`verdict_logic.aggregate(signals, results)` aplica en orden:

1. Si hay algún `VerdictSignal` con `polarity=FAIL` y `severity=BLOCKER` → **`FAIL`**.
2. Si `len(degraded_rules) / len(results) > workflow.degraded_threshold` (default `0.5`) → **`REVIEW`**.
3. Si hay algún signal con `polarity=FAIL` y `severity ∈ {MAJOR, MINOR}` → **`REVIEW`**.
4. Si todos los signals son `PASS` o `NEUTRAL` → **`PASS`**.
5. Caso degenerado (no hay signals ni degradación, ej. workflow puro de Enrichment) → `verdict=None`.

### Implementación actual

El hook `regenerate_on_run_complete.py` se dispara cuando el `WorkflowAnalysisRun` pasa a `COMPLETED`. Ejecuta secuencialmente:

1. **`VerdictAggregator.execute()`** — corresponde a los pasos [B-C] de arriba. Si falla, el summary queda incompleto y se loggea (hard-fail dentro del runner, pero el run queda en estado consistente para reintento).
2. **`SynthesisRunner.enqueue()`** — dispara la fase `SYNTHESIZE` con el summary ya armado. Es **soft-fail**: si la síntesis crashea, el verdict y los signals ya están persistidos y disponibles para el cliente.

### Worked example — qué pasa al cerrar el caso A

Volviendo al [Caso A](#caso-a--happy-path-corren-las-5-etapas) (Pedro García, regla "Validar la cédula"):

Asumiendo que era la única regla del workflow:

```python
# Después de [A]:
results = [WorkflowRuleResult(status=SUCCESS, output={...}, ...)]
signals = [VerdictSignal(polarity=PASS, severity=MAJOR, detail={...})]
enrichments = []  # la regla era de Validation

# [B] VerdictAggregator.execute():
bundle = VerdictBundle(
    verdict             = PASS,    # 1 signal PASS, 0 blockers, 0 degraded
    signals             = [SignalSnapshot(...)],
    blocking_failures   = [],
    degraded_rules      = [],
    confidence_score    = 1.0,     # 1/1 SUCCESS
    signals_by_polarity = {"PASS": 1, "FAIL": 0, "NEUTRAL": 0},
    signals_by_severity = {"MAJOR": 1, ...},
)

# [C] WorkflowAnalysisRunSummary armado con bundle + enrichments=[].

# ────── EVALUATE termina aquí ──────

# [D] SYNTHESIZE arranca, recibe el summary, compone el output_schema.
```

Si la regla hubiera sido la única y hubiera fallado en E2 (Caso B, RUT mal formado):

```python
results = [WorkflowRuleResult(status=SUCCESS, output={"tree_outcome": "FAIL", ...}, ...)]
signals = [VerdictSignal(polarity=FAIL, severity=BLOCKER, detail={...})]

bundle = VerdictBundle(
    verdict             = FAIL,    # blocker FAIL → corta seco
    signals             = [SignalSnapshot(...)],
    blocking_failures   = [rule_id],
    degraded_rules      = [],
    confidence_score    = 1.0,
    ...
)
```

Ese es el output de EVALUATE: no es el `WorkflowRuleResult` aislado, es el `VerdictBundle` (que se proyecta dentro del `WorkflowAnalysisRunSummary`).

---

## 10. Para ir más a fondo

- [`product/specs/pipeline/phase_evaluate.md`](../../product/specs/pipeline/phase_evaluate.md) — spec normativo: Protocol del kind, schemas, target model, deltas sobre el código actual.
- [`product/specs/pipeline/general.md`](../../product/specs/pipeline/general.md) — pipeline macro (INGEST → PROCESSING → EVALUATE → SYNTHESIZE).
- [`product/plans/analysis-rules/_archive/create-rules.md`](../../product/plans/analysis-rules/_archive/create-rules.md) — UX del editor de reglas y cómo el usuario configura los campos descritos acá.
- Código relevante:
  - `backend/src/workflows/domain/rules/kind_protocol.py` — el Protocol del kind.
  - `backend/src/workflows/application/workflow_rules/evaluation/evaluator.py` — el runner principal.
  - `backend/src/workflows/application/workflow_rules/evaluation/scope_resolver.py` — generador de combinations.
  - `backend/src/workflows/infrastructure/services/rules/kinds/` — implementaciones de los kinds existentes.
