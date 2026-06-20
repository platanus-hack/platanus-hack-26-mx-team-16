# Consensus Strategy

Documento técnico sobre la estrategia de consenso multi-agente que Doxiq usa para evaluar `AnalysisRule`s sobre los documentos de un case.

> Specs fuente: [`product/specs/analysis-rules/_archive/analysis-execution.md`](../product/specs/analysis-rules/_archive/analysis-execution.md), [`product/plans/analysis-rules/_archive/analysis-exec-report.md`](../product/plans/analysis-rules/_archive/analysis-exec-report.md).

---

## 1. Motivación

Las `AnalysisRule`s mezclan checks **objetivos** (comparaciones numéricas, regex, rangos de fecha, presencia de campos) con checks **subjetivos** que requieren juicio del LLM ("¿la cláusula del contrato es razonable?", "¿la justificación del gasto es coherente con el rubro?").

Los checks subjetivos tienen tres riesgos clásicos del LLM-as-a-judge:

1. **Varianza de muestreo** — la misma pregunta puede dar veredictos distintos entre corridas.
2. **Alucinaciones** — el modelo afirma datos que no están en el extraction.
3. **Edge cases ignorados** — el modelo se "acomoda" en la respuesta más probable y pasa por alto excepciones.

La estrategia de consenso ataca los tres con la misma receta: **muchas muestras + auditoría cruzada + verificación determinística**.

---

## 2. Arquitectura del pipeline (5 etapas)

Cada `AnalysisRule` se divide en *combinaciones* de documentos (producto cartesiano sobre los slugs que la regla menciona). Por cada combinación se ejecutan estas 5 etapas en orden:

```
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 1 — Pre-evaluación determinística (sin LLM)               │
│   Ejecuta el AST cacheado de la regla:                          │
│     numeric_comparison · date_range · regex_match               │
│     field_exists · length_check · enum_check                    │
│   Marca checks subjetivos como "delegado al reviewer"           │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 2 — Reviewer agent (Claude Opus 4.7 + tools)              │
│   Tools: get_document, get_field, get_raw_ocr,                  │
│          python_exec, current_datetime, kb_search               │
│   Output: { is_passed, reasoning, citations, ... }              │
│   Citaciones validadas con JMESPath contra el extraction real   │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 3 — Self-consistency (N=5 reviewers en paralelo)          │
│   Resolución del verdict:                                       │
│     • 5/0 ó 4/1   → mayoría clara                               │
│     • 3/2         → escala a etapa 4 (needs_critic)             │
│     • ≥3 nulls    → inconcluyente, error="no_consensus"         │
└─────────────────────────────────────────────────────────────────┘
                             ↓ (solo si needs_critic)
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 4 — Critic agent (Gemini 2.5 Pro, otro proveedor)         │
│   Recibe: regla + verdict reviewer + reasoning + citations      │
│   Devuelve: { verdict_agreement, feedback, severity }           │
│   severity=high   → 1 rerun reviewer con feedback inyectado     │
│   severity=med/low→ feedback queda como warning, verdict igual  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 5 — Verificación post-hoc determinística                  │
│   • Si rule.output_enabled: valida structured_output vs schema  │
│   • Cross-check de hechos citados contra el extraction real     │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                  AnalysisRuleResult persistido
                  Evento RULE_RESULT_READY emitido por SSE
```

---

## 3. Flujo de datos

### 3.1 Entradas al pipeline

Por cada combinación, el orquestador arma el siguiente payload:

| Entrada | Origen | Uso |
|---|---|---|
| `rule.content` | `AnalysisRule` (texto natural con tokens `@slug.field`, `#kb_slug`, `{{system_var}}`) | Prompt al reviewer y al critic |
| `rule.parsed_ast` | Cacheado por el parser LLM al guardar la regla | Etapa 1 (checks objetivos) y para marcar checks subjetivos |
| `rule.output_schema` | Opcional, si `output_enabled=true` | Forzar `response_format` JSON al reviewer; validar en etapa 5 |
| `rule.kb_ids` | FKs a `KnowledgeBase` | Acota el `kb_search` tool del reviewer |
| `combination.documents` | `WorkflowDocument`s elegidos por slug | Construye `{slug: {fields_schema, extraction}}` para el system prompt |
| `workflow.reviewer_model` / `workflow.critic_model` | Configuración por workflow | Selecciona los modelos para etapas 2–4 |
| `workflow.analysis_consensus_samples` | Default = 5 | N de muestras paralelas en etapa 3 |

### 3.2 Reviewer → consenso (etapas 2 y 3)

1. Se lanzan **N instancias paralelas** del `AgnoAgentReviewer` (default N=5), todas con el mismo system prompt y temperature > 0.
2. Cada instancia produce:
   ```json
   {
     "is_passed": true | false | null,
     "reasoning": "...",
     "citations": [{ "claim": "...", "document_id": "...", "field_path": "..." }],
     "structured_output": { ... }   // si output_enabled
   }
   ```
3. Cada respuesta pasa una **validación programática** de citaciones:
   - `field_path` debe existir en el `fields_schema` del DocumentType.
   - Citas negativas (`claim: "field_absent"`) se validan contra `null`/vacío en el extraction.
   - No se aceptan citas a `extracted_text` (OCR crudo).
   - Si falta una cita requerida → re-prompt (máx 2 retries → `error="missing_citations"`).
4. Los N veredictos válidos se agregan en el campo `consensus` del resultado:
   ```json
   {
     "n_samples": 5,
     "agreement_ratio": 0.8,
     "verdicts": [true, true, true, true, false]
   }
   ```

### 3.3 Resolución del veredicto

| Distribución de N=5 | `agreement_ratio` | Acción |
|---|---|---|
| 5/0 | 1.0 | Veredicto mayoritario, **no** se llama al critic |
| 4/1 | 0.8 | Veredicto mayoritario, **no** se llama al critic |
| 3/2 | 0.6 | `needs_critic=true` → etapa 4 |
| ≥3 `null` | n/a | Persiste con `error="no_consensus"`, `is_passed=null` |

> **`consensus` es inmutable tras la etapa 3.** Aunque la etapa 4 cambie `is_passed`, el array de los 5 verdicts originales se conserva para auditoría. La señal de "el critic intervino" es `critic_iterations > 0`.

### 3.4 Critic → posible rerun (etapa 4)

Cuando se necesita critic:

1. Se invoca un **modelo de otro proveedor** (default reviewer = Claude Opus 4.7, critic = Gemini 2.5 Pro). El cambio de proveedor es deliberado: dos modelos de la misma familia tienden a alucinar lo mismo.
2. El critic recibe la regla original, el `reasoning` mayoritario, las `citations` y el mismo contexto estructurado. Devuelve:
   ```json
   { "verdict_agreement": bool, "feedback": "...", "severity": "low|medium|high" }
   ```
3. Si `severity=high` → se ejecuta **una sola corrida adicional del reviewer** con el `critic_feedback` inyectado al system prompt. Ese verdict sobrescribe `is_passed` y `reasoning`. Máx 2 iteraciones reviewer↔critic.
4. Si `severity=medium|low` → no se cambia el verdict. El `critic_feedback` queda en el resultado para mostrarse como warning en la UI.

### 3.5 Verificación post-hoc (etapa 5)

- Valida `structured_output` contra `output_schema` (si aplica). Schema mismatch → `error="schema_mismatch"` y se persiste el JSON crudo.
- Cross-check de hechos citados: si el reviewer dijo "fecha=2024-03-15" pero el extraction tiene "2024-05-13", se agrega entrada a `verification_warnings`.

### 3.6 Persistencia y eventos

Cada combinación produce un `AnalysisRuleResult` con (ver [`backend/src/common/domain/models/processing/workflow_analysis_run.py`](../backend/src/common/domain/models/processing/workflow_analysis_run.py) y la entidad frontend [`frontend/src/domain/entities/analysis-run.ts`](../frontend/src/domain/entities/analysis-run.ts)):

| Campo | Origen |
|---|---|
| `is_passed`, `reasoning` | Reviewer (mayoría, o rerun del critic si severity=high) |
| `consensus` | `{n_samples, agreement_ratio, verdicts}` de la etapa 3 |
| `critic_feedback`, `critic_iterations` | Etapa 4 |
| `citations` | Reviewer + validación programática |
| `preliminary_checks` | Etapa 1 |
| `verification_warnings` | Etapa 5 |
| `structured_output` | Reviewer (si `output_enabled=true`) |
| `unresolved_tokens` | Renderer al producir `rendered_prompt` |
| `error` | `missing_citations` \| `no_consensus` \| `schema_mismatch` \| `null` |

Eventos SSE emitidos durante el pipeline (consumidos por el frontend para streaming en vivo):

- `RUN_STARTED`, `EVALUATION_STARTED`, `STAGE_PROGRESS` (stages 1–5), `RULE_RESULT_READY`, `RUN_PROGRESS`, `RUN_COMPLETED` / `RUN_FAILED` / `RUN_CANCELED`.

### 3.7 Síntesis del run (post-pipeline, opcional)

Si `workflow.synthesis_enabled=true`, una vez cerrado el run un **synthesizer agent** (ver [`backend/src/workflows/application/analysis_run_summary/synthesis_runner.py`](../backend/src/workflows/application/analysis_run_summary/synthesis_runner.py)) toma todos los `AnalysisRuleResult`s y produce un resumen ejecutivo del case usando `workflow.synthesis_template`. Se cachea por `input_hash` (re-ejecutable con `force=True`).

---

## 4. Cómo se mapea el consenso al frontend

`frontend/src/domain/entities/analysis-run.ts` clasifica cada resultado en un `ConfidenceLevel`:

```ts
classifyConfidence(result):
  criticIterations > 0          → "critic_reviewed"
  error === "no_consensus"      → "inconclusive"
  agreementRatio === 1.0        → "high"
  agreementRatio ∈ [0.6, 1.0)   → "medium"
  resto                         → "inconclusive"
```

Esto le permite a la UI mostrar badges distintos para "5/5 acuerdo claro" vs "el critic intervino" vs "no hubo consenso".

---

## 5. Para qué tipo de evaluaciones es efectiva esta estrategia

La estrategia tiene un costo no trivial — N=5 llamadas LLM por combinación, más eventualmente la del critic y un rerun. Vale la pena cuando se cumple **al menos uno** de estos criterios:

### ✅ Casos donde aplica bien

- **Juicios subjetivos sobre texto extraído.** "¿La descripción del gasto es razonable para el rubro?", "¿la cláusula del contrato es ambigua?", "¿la justificación es coherente con el monto?". Aquí la varianza de muestreo es real y la mayoría de N=5 reduce el error sustancialmente.
- **Reglas con alto costo de falso positivo o falso negativo.** Cumplimiento regulatorio, validaciones legales, pre-aprobación financiera — donde un error silencioso es caro de revertir y conviene gastar más cómputo en confianza.
- **Verificaciones que requieren cruzar múltiples campos o documentos.** El reviewer puede usar `python_exec`, `kb_search` y `get_field` para componer evidencia. La auditoría cruzada del critic detecta cuando el reviewer "armó" una conclusión saltándose un paso.
- **Salidas estructuradas con schema (`output_enabled=true`).** El consenso reduce schemas mal formados; la etapa 5 captura los que se escapan.
- **Reglas que invocan KB.** Hay riesgo de que el reviewer cite mal o ignore un fragmento relevante; tener N muestras + critic con tools idénticas detecta esos sesgos.
- **Decisiones que un humano va a auditar.** El array `consensus.verdicts`, las `citations` y el `critic_feedback` dan una traza explicable, no solo un boolean.

### ❌ Casos donde *no* es eficiente

- **Checks puramente determinísticos.** Comparaciones numéricas, regex, presencia de campos, rangos de fecha — la etapa 1 ya los resuelve sin LLM. Forzar consenso aquí es solo gasto.
- **Lookups triviales** del estilo "¿el campo `nombre` existe?". `field_exists` lo cubre en etapa 1.
- **Pipelines de baja consecuencia con altos volúmenes.** Si el resultado se va a re-procesar de todas formas o el costo de un error es despreciable, N=1 sin critic es suficiente. Bajar `analysis_consensus_samples` por workflow es la palanca.
- **Loops de iteración rápida durante diseño de reglas.** Para iterar en el editor conviene un modo single-shot; el consenso completo se reserva para runs "de verdad".

### Reglas de pulgar para tunear `analysis_consensus_samples`

| Tipo de regla | Sugerido |
|---|---|
| 100% objetiva (etapa 1 cubre todo) | N/A — el LLM no se invoca |
| Subjetiva, baja consecuencia | `N=1` o `N=3` |
| Subjetiva, consecuencia media | `N=5` (default) |
| Subjetiva, alta consecuencia + critic obligatorio | `N=5` y mantener critic habilitado |

---

## 6. Tolerancia a fallos

- Si una de las N muestras del reviewer falla (timeout, schema inválido, citas inválidas tras 2 retries), se descarta y el consenso se calcula sobre las restantes. Si quedan <3 válidas → `error="no_consensus"`.
- Si el critic falla → se persiste el verdict del reviewer con `critic_iterations=0` y un warning interno.
- Si el synthesizer falla → el run queda marcado como completado igual; la síntesis se puede reintentar vía endpoint de re-synthesize.

---

## 7. Referencias en el código

| Capa | Archivo |
|---|---|
| Specs originales | `product/specs/analysis-rules/_archive/analysis-execution.md`, `product/plans/analysis-rules/_archive/analysis-exec-report.md` |
| Dominio del run | `backend/src/common/domain/models/processing/workflow_analysis_run.py` |
| Builder del run | `backend/src/workflows/infrastructure/builders/analysis_run.py` |
| Repo del run | `backend/src/workflows/infrastructure/repositories/sql_workflow_analysis_run.py` |
| Synthesizer | `backend/src/workflows/application/analysis_run_summary/synthesis_runner.py` |
| Synthesizer agent | `backend/src/workflows/infrastructure/services/run_summary/synthesizer.py` |
| Migración inicial | `backend/src/common/database/versions/20260503.084505_55c61ec5b69b_initial.py` |
| Migración synthesis | `backend/src/common/database/versions/20260506.230120_4fd3772c2a94_synthesis.py` |
| Entidad frontend | `frontend/src/domain/entities/analysis-run.ts` |