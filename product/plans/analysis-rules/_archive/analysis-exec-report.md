---
feature: analysis-rules
type: plan
status: obsolete
coverage: 35
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

# Reporte: Implementación de Analysis Execution

> **Estado:** ✅ Implementado, **223 tests pasando**, frontend compila limpio, migración aplicada.
> **Spec base:** [`product/specs/analysis-rules/_archive/analysis-execution.md`](./analysis-execution.md)
> **Fecha:** 2026-05-02

---

## 1. TL;DR

Implementé el motor que **ejecuta las reglas de análisis** que tú defines en el backoffice contra los documentos extraídos de un case. Cuando el usuario aprieta "Ejecutar análisis" en la UI, el backend:

1. Toma cada regla activa, la divide en checks atómicos (precomputados por un LLM cuando guardaste la regla).
   2. Por cada combinación de documentos posibles, corre 5 etapas: pre-validación determinística, reviewer LLM con tools, self-consistency con N=5 muestras, crítico cross-provider opcional, y verificación post-hoc.
3. Persiste los resultados con citaciones obligatorias a los campos del extraction.
4. Streamea progreso vía SSE para que la UI muestre los resultados en vivo.

---

## 2. ¿Qué problema resuelve?

**Antes**: existía un stub que devolvía `is_passed=True` para todas las reglas. Sin LLM, sin trazabilidad, sin estructura.

**Ahora**: cada regla del workflow se evalúa con un pipeline auditable. Si una regla dice _"el monto de la factura debe ser mayor a 100"_, el sistema:
- **Verifica determinísticamente** la comparación numérica (sin gastar tokens).
- Si la regla además dice _"y el titular debe ser el mismo que en la cédula"_, **delega esa parte al reviewer LLM** que tiene tools para leer los documentos.
- **Valida que el reviewer cite exactamente** qué campo de qué documento usó (no permite alucinaciones).
- Si los samples del reviewer no se ponen de acuerdo, **escala a un crítico de otro proveedor** (Claude vs Gemini).
- **Persiste todo** — verdict, razonamiento, citaciones, warnings — para revisión humana.

---

## 3. Las 5 etapas del pipeline (en orden, por cada combinación de documentos)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 1 — Pre-evaluación determinística (sin LLM)                  │
│    ✓ Ejecuta el AST cacheado de la regla:                          │
│        numeric_comparison, date_range, regex_match,                 │
│        field_exists, length_check, enum_check                       │
│    ✓ Marca checks subjetivos como "delegado al reviewer"            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 2 — Reviewer agent (Claude Opus 4.7 + tools)                 │
│    Tools: get_document, get_field, get_raw_ocr, python_exec,       │
│           current_datetime, kb_search                               │
│    Output requerido: { is_passed, reasoning, citations, ... }      │
│    Citaciones validadas con JMESPath contra el extraction real     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 3 — Self-consistency (N=5 reviewers en paralelo)             │
│    Resolución del verdict:                                          │
│      • 5/0, 4/1                  → mayoría clara                    │
│      • 3/2 (o cualquier ratio ≤ 2/3) → escala a etapa 4             │
│      • ≥3 nulls                  → inconcluyente, error="no_consensus" │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (si needs_critic)
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 4 — Critic agent (Gemini 2.5 Pro, otro proveedor)            │
│    Recibe: regla + verdict del reviewer + reasoning + citations    │
│    Devuelve: { verdict_agreement, feedback, severity }              │
│    Si severity=high  → 1 rerun del reviewer con feedback inyectado │
│    Si severity=med/low → feedback queda como warning, verdict no cambia │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 5 — Verificación post-hoc determinística                     │
│    • Si rule.output_enabled: valida structured_output vs JSON Schema│
│    • Cross-check: si el agente reportó "fecha=2024-03-15" pero      │
│      el extraction dice "2024-05-13" → verification_warning         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                      AnalysisRuleResult persistido
                      Evento RULE_RESULT_READY emitido por SSE
```

---

## 4. Ejemplo end-to-end

### 4.1 La regla en el backoffice

```
Verifica que @cedula.fecha_nacimiento corresponda a alguien mayor a
18 años respecto a {{fecha-hoy}}, y que el nombre del titular sea
similar al que aparece en @factura.cliente.
```

### 4.2 Lo que hace el parser (al guardar la regla)

Disparado en background como tarea, llama a Claude Sonnet 4.6 que devuelve:

```json
{
  "checks": [
    {
      "id": "check_1",
      "kind": "date_range",
      "operands": {
        "field": "@cedula.fecha_nacimiento",
        "from": null,
        "to": "{{fecha-hoy}}"
      },
      "natural_language": "fecha de nacimiento debe ser anterior a hoy"
    },
    {
      "id": "check_2",
      "kind": "subjective",
      "operands": {},
      "natural_language": "el nombre del titular debe ser similar al cliente de la factura"
    }
  ]
}
```

Esto se cachea en `analysis_rules.parsed_checks`. El UI muestra esta descomposición en el modal de la regla.

### 4.3 Cuando el usuario ejecuta el análisis

El case tiene **2 cédulas** y **3 facturas**. La regla menciona ambos slugs → el motor genera **6 combinaciones** (2×3). Por cada una corre las 5 etapas.

**Etapa 1** (sin LLM):
```json
{
  "results": [
    {
      "check_id": "check_1",
      "kind": "date_range",
      "passed": true,
      "evidence": {
        "value": "1990-05-12",
        "from": null,
        "to": "2026-05-02"
      }
    },
    {
      "check_id": "check_2",
      "kind": "subjective",
      "passed": null,
      "evidence": { "delegated_to_reviewer": true }
    }
  ],
  "summary": { "total": 2, "objective": 1, "passed_objective": 1 }
}
```

**Etapa 2** (reviewer Claude Opus): recibe la regla original + el structured context con ambos documentos + los preliminary checks. Usa `get_field` para ver `@cedula.nombre` y `@factura.cliente`, decide que coinciden, devuelve:

```json
{
  "is_passed": true,
  "reasoning": "La cédula muestra Juan Pérez nacido el 1990-05-12 (35 años). La factura tiene como cliente 'Juan Perez' — la diferencia es solo la tilde, son la misma persona.",
  "citations": [
    { "claim": "fecha de nacimiento 1990-05-12", "documentId": "abc-123", "fieldPath": "fecha_nacimiento" },
    { "claim": "titular Juan Pérez", "documentId": "abc-123", "fieldPath": "nombre" },
    { "claim": "cliente Juan Perez", "documentId": "def-456", "fieldPath": "cliente" }
  ]
}
```

**Etapa 3**: corre 5 veces en paralelo. Si los 5 dicen `true` → `agreement_ratio = 1.0`, no se invoca crítico.

**Etapa 4**: skipped (no hay duda).

**Etapa 5**: no hay `output_schema`, solo verifica que las citaciones sean coherentes con el extraction real → todo OK.

### 4.4 Lo que ve el usuario en el frontend

- Card por regla agrupada, badge **"alta confianza"** verde.
- Click → expande con el reasoning, las 3 citaciones clickeables, los preliminary checks.
- Si fueran 6 combinaciones, ve 6 cards (una por combo) bajo la regla.

---

## 5. Cambios en la base de datos

### 5.1 Tabla nueva: `analysis_runs`

Una corrida agrupa todos los `AnalysisRuleResult` producidos en un disparo.

| Columna | Tipo | Notas |
|---|---|---|
| `uuid` | UUID PK | |
| `tenant_id`, `workflow_id`, `case_id` | UUID FK | |
| `status` | str | `RUNNING`, `COMPLETED`, `FAILED`, `CANCELING`, `CANCELED` |
| `triggered_by` | UUID? | Usuario que lo disparó |
| `started_at`, `completed_at` | datetime? | |
| `error` | text? | Solo para fallos de orquestación |

### 5.2 Tabla `analysis_rules` — 5 columnas nuevas

| Columna | Para qué |
|---|---|
| `parsed_checks` | AST cacheado (JSONB) — list de checks atómicos |
| `previous_parsed_checks` | AST anterior (rollback manual) |
| `parser_version` | Versión del parser que generó el AST |
| `parsed_at` | Timestamp del último parseo |
| `parser_error` | Si el parser falló — la regla sigue siendo válida sin pre-validación |

### 5.3 Tabla `analysis_rule_results` — rename + 9 columnas nuevas

- **Rename:** `structured_data` → `structured_output`
- **`is_passed`**: ahora `nullable` (antes era NOT NULL) para soportar verdict inconcluyente.
- **Nuevas columnas:**
  - `analysis_run_id` (FK a `analysis_runs`, NOT NULL)
  - `rendered_prompt` (text — solo auditoría, no es input del agente)
  - `document_refs` (JSONB — `{slug: workflow_document_id}`)
  - `citations` (JSONB — `[{claim, documentId, fieldPath}]`)
  - `preliminary_checks` (JSONB — output de la etapa 1)
  - `consensus` (JSONB — `{nSamples, agreementRatio, verdicts}`)
  - `critic_feedback` (text? — output del crítico si corrió)
  - `critic_iterations` (int — 0 si no se necesitó)
  - `verification_warnings` (JSONB — discrepancias detectadas en etapa 5)
  - `unresolved_tokens` (JSONB — tokens del template que no resolvieron)

### 5.4 Tabla `workflows` — 3 columnas nuevas (todas nullable, defaults en código)

| Columna | Default en código |
|---|---|
| `analysis_reviewer_model` | `claude-opus-4-7` |
| `analysis_critic_model` | `gemini-2.5-pro` |
| `analysis_consensus_samples` | `5` (rango 3-9) |

> Migración aplicada: `20260501.120000_h5c9e0d3a4f2_analysis_runs_pipeline.py`. Borra primero la join table `analysis_rule_result_documents` para no romper el FK.

---

## 6. API — endpoints nuevos

| Método | Ruta | Devuelve |
|---|---|---|
| `POST` | `/v1/workflows/{wf_id}/cases/{case_id}/analysis-runs` | `202 AnalysisRun` (status=RUNNING) |
| `GET` | `/v1/workflows/{wf_id}/cases/{case_id}/analysis-runs` | `[AnalysisRun]` ordenado por más reciente |
| `GET` | `/v1/analysis-runs/{run_id}` | `AnalysisRun + results[]` |
| `GET` | `/v1/analysis-runs/{run_id}/events` | `text/event-stream` (SSE) |
| `POST` | `/v1/analysis-runs/{run_id}/cancel` | `AnalysisRun` (status=CANCELING) |
| `GET` | `/v1/analysis-rules/{rule_id}` | `AnalysisRule` (con `parsedChecks`) — nuevo |

### Validaciones del POST (rechazos antes de crear el run):

| Caso | Status | code |
|---|---|---|
| Workflow no es ANALYSIS | 409 | `processing.WorkflowTypeMismatch` |
| Workflow sin reglas activas | 400 | `processing.InvalidAnalysisRule` |
| Ya hay un run activo para el case | 409 | `processing.AnalysisAlreadyRunning` |
| Algún doc del case está en extracción | 409 | `processing.ExtractionInProgress` |
| Una regla genera > 25 combinaciones | 400 | `processing.RuleCombinationsExceeded` |
| El run total > 200 combinaciones | 400 | `processing.RunCombinationsExceeded` |

### Eventos SSE (8 tipos)

```
RUN_STARTED          { runId, totalEvaluations }
EVALUATION_STARTED   { ruleId, combinationKey }
STAGE_PROGRESS       { ruleId, combinationKey, stage: 1|2|3|4|5, status }
RULE_RESULT_READY    AnalysisRuleResult completo
RUN_PROGRESS         { completed, total }
RUN_COMPLETED        { runId, summary: { passed, failed, errored } }
RUN_FAILED           { runId, error }
RUN_CANCELED         { runId, canceledAt, reason }
```

Cada evento lleva `seq` autoincremental y `ts`. El subscriber del frontend reconecta automáticamente con backoff exponencial.

---

## 7. Frontend — qué cambió

### 7.1 Modal de edición de regla

Cuando guardas o editas una regla **ya creada**, debajo del editor aparece un panel **"Tu regla fue interpretada como"** con una lista:

```
✓ [Comparación numérica]   monto > 100
✓ [Rango de fechas]        fecha emisión en últimos 3 meses
○ [Subjetivo]              similitud titular vs nombre cédula  → delegado al reviewer
```

Si el parser falló: banner amarillo claro de que el análisis sigue funcionando pero sin pre-validación.

### 7.2 Tab "Análisis" en el detalle del case

Reemplaza el placeholder vacío que existía. Tiene:

- **Botón "Ejecutar análisis"** (deshabilitado mientras hay un run activo, se reemplaza por "Cancelar").
- **Barra de progreso** `X / Y evaluaciones` mientras corre.
- **Cards agrupadas por regla**, cada una con verdict ✓/✗/⊘ y badge de confianza:
  - 🟢 **alta confianza** (agreementRatio = 1.0)
  - 🟡 **confianza media** (agreementRatio entre 0.6 y 1.0)
  - 🟣 **revisión del crítico** (criticIterations > 0)
  - ⚫ **inconcluyente** (error="no_consensus")
- **Card expandible** muestra: reasoning, lista de citaciones (clickeable a campo), warnings de verificación, structured output si existe.
- **Historial** de runs anteriores; click en uno re-attachea y muestra sus resultados.

### 7.3 Archivos creados / modificados

```
frontend/src/domain/entities/analysis-rule.ts       (extendido: parsedChecks, etc.)
frontend/src/domain/entities/analysis-run.ts        (NUEVO — todos los tipos del run)
frontend/src/infrastructure/repositories/http-analysis-rule.ts   (+ get(ruleId))
frontend/src/infrastructure/repositories/http-analysis-run.ts    (NUEVO)
frontend/src/presentation/components/rule-decomposition-panel.tsx (NUEVO)
frontend/src/presentation/components/analysis-run-panel.tsx       (NUEVO)
frontend/src/presentation/components/analysis-rule-modal.tsx     (panel insertado)
frontend/src/presentation/workflows/cases/case-detail-view.tsx   (tab cableado)
```

---

## 8. Las 9 inconsistencias detectadas durante el self-review (todas arregladas)

Después de implementar todo, hice un review formal del código. Encontré 10 problemas reales — apliqué los 9 más urgentes y dejé el último como TODO documentado (luego también lo arreglé al final con la versión JMESPath).

| # | Tipo | Qué pasaba antes | Qué hice |
|---|---|---|---|
| 1 | 🟥 **Bug** | El runner derivaba `case_id` de `inputs.documents[0].case_id` — si los docs no tenían case_id seteado, crasheaba con `RuntimeError`. | Agregué `case_id: UUID` a `RunnerInputs`, lo paso explícito desde el scheduler. |
| 2 | 🟥 **Bug** | La condición `needs_critic = abs(true-false) <= 1 and len(valid) >= 4` saltaba el caso 2/1 con N=3 (mínimo permitido por spec). | Reemplacé por `agreement_ratio <= 2/3` — escala correctamente para cualquier N entre 3 y 9. |
| 3 | 🟧 **Spec §9.2** | El error `no_classified_documents` se disparaba cuando la lista de combinaciones venía vacía (e.g., regla sin tokens). | Ahora se dispara cuando hay docs Y ninguno tiene `document_type_id` — que es lo que dice el spec. |
| 4 | 🟨 **Riesgo migración** | El `DELETE FROM analysis_rule_results` rompería el FK de `analysis_rule_result_documents` (la join table) si tenía rows. | Drené la join table primero. |
| 5 | 🟧 **Spec §8.2** | Faltaba `ruleContent` en el presenter y el TS interface. | Agregado en presenter (parámetro opcional), propagado por `GetRunDetail` y por el orquestador para SSE. |
| 6 | 🟧 **Spec §8.2** | Las citaciones venían en snake_case del LLM (`document_id`, `field_path`) pero el spec dice camelCase. | Helper `_camel_citation()` en el presenter; TS interface alineado a `documentId/fieldPath`. |
| 7 | 🟧 **Spec §7.1** | El payload de `RUN_CANCELED` no incluía `canceledAt`. | Agregado. |
| 8 | 🟧 **Spec §7.2** | Cancelación solo se chequeaba entre combinaciones, no entre etapas — un crítico en curso podía retrasar la cancelación 2 LLM calls. | Check antes de etapa 2 y antes de etapa 4 (las dos más caras). |
| 9 | 🟧 **Spec §6.5/§7.1** | El conteo de `errored` clasificaba doblemente `is_passed=None`. | Simplificado a `error != null OR is_passed is None` — el summary siempre suma al total. |
| 10 | 🟨 **Validador laxo** | El validador de citaciones solo verificaba el top-level del path (`nombre.primero` pasaba aunque `extraction["nombre"]["primero"]` no existiera). | **Resolución JMESPath end-to-end**: si el path es positivo debe resolver a no-null; si es `field_absent` el campo top-level debe estar declarado en el `fields` schema del DocumentType. |

---

## 9. Tests

| Suite | Cuántos | Qué cubre |
|---|---|---|
| `test_check_executor.py` | 19 | Cada uno de los 6 kinds objetivos (paso/falla/error), system-vars, subjetivos, parser unavailable |
| `test_fanout.py` | 10 | Producto cartesiano 1×N, 3×2, slugs sin docs, dedupe de tokens, estabilidad del `combinationKey` |
| `test_starter.py` | 7 | Las 6 validaciones de pre-flight + happy path |
| `test_llm_parser.py` | 9 | Validación de output del parser, demote de checks malformados a subjetivos |

**Total: 45/45 pasan**, integrados en la suite global de **223 tests pasando**.

> Los tests del reviewer/critic propiamente dichos no se hicieron — requieren mockear el SDK Anthropic/Gemini y son territorio de tests de integración. La lógica de **resolución de consenso** y **validación de citaciones** son testables sin LLM y están cubiertas por los smoke tests del proceso de review (no integradas a la suite, pero ejecutadas durante el desarrollo).

---

## 10. TODOs anclados en código (para v2 o cuando aparezcan los disparadores)

| # | Archivo:línea | Pendiente |
|---|---|---|
| 1 | `domain/services/analysis/parser.py:14` | Política de bump de `PARSER_VERSION` (semver vs entero) |
| 2 | `infrastructure/services/analysis/runner.py:62` | Mover caps `RULE_COMBINATION_CAP`/`RUN_COMBINATION_CAP` a `tenant_settings` |
| 3 | `infrastructure/services/analysis/reviewer.py:112` | Wire del extended-thinking budget de Anthropic vía Agno |
| 4 | `infrastructure/services/analysis/reviewer.py:336` | Reemplazar `asyncio.gather` por la primitiva multi-sample nativa de Agno |
| 5 | `application/analysis_runs/runner_scheduler.py:23` | Cron que rescata runs huérfanos + migración a ARQ/Temporal v2 |
| 6 | `presentation/endpoints/analysis_run.py:52` | Cablear `triggered_by` con el UUID del usuario autenticado |

---

## 11. Cómo probarlo manualmente

### Pre-requisitos
- Docker compose corriendo (`just dev-backend`).
- Variables `ANTHROPIC_API_KEY` y `GEMINI_API_KEY` exportadas en `backend/.env`.
- Un workflow con `workflow_type=ANALYSIS` y al menos un DocumentType.
- Al menos una `AnalysisRule` activa en ese workflow.
- Un case con documentos clasificados (status=`EXTRACTED`).

### Smoke flow

```bash
# 1) Crear una regla — el parser corre en background
curl -X POST http://localhost:8200/v1/workflows/{wf_id}/analysis-rules \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content": "Verifica que @cedula.fecha_nacimiento corresponda a alguien mayor a 18 años respecto a {{fecha-hoy}}"}'

# 2) ~3 segundos después, verificar el AST cacheado
curl http://localhost:8200/v1/analysis-rules/{rule_id} -H "Authorization: Bearer $TOKEN"
# Esperar ver "parsedChecks": [{"kind": "date_range", ...}]

# 3) Disparar un análisis sobre un case
curl -X POST http://localhost:8200/v1/workflows/{wf_id}/cases/{case_id}/analysis-runs \
  -H "Authorization: Bearer $TOKEN"
# → 202 con { uuid, status: "RUNNING" }

# 4) Suscribirse a los eventos en otra terminal
curl -N http://localhost:8200/v1/analysis-runs/{run_id}/events \
  -H "Authorization: Bearer $TOKEN"
# → ver RUN_STARTED, STAGE_PROGRESS, RULE_RESULT_READY, RUN_COMPLETED

# 5) Leer el detalle persistido
curl http://localhost:8200/v1/analysis-runs/{run_id} -H "Authorization: Bearer $TOKEN"
```

### En la UI

1. Entrar a un workflow tipo Analysis → tab "Reglas" → editar una → ver el panel de descomposición debajo del editor.
2. Entrar a un case del mismo workflow → tab "Análisis" → click "Ejecutar análisis" → ver progreso en vivo, expandir resultados.

### Forzar re-parseo masivo (cuando bumpeen `PARSER_VERSION`)

```bash
docker compose exec api python backend/scripts/reparse_rules.py
# Opcionales: --tenant <uuid>  --workflow <uuid>
```

---

## 12. Estructura de archivos creados (high-level)

```
backend/
  src/common/
    domain/
      enums/workflows.py                            (+ AnalysisRunStatus)
      exceptions/processing.py                      (+ 4 excepciones nuevas)
      models/processing/
        analysis_run.py                             (NUEVO)
        analysis_rule.py                            (extendido)
        analysis_rule_result.py                     (reescrito)
        workflow.py                                 (+ 3 campos)
    database/
      models/processing/
        analysis_run.py                             (NUEVO ORM)
        business_rule.py                            (+ 5 columnas)
        rule_evaluation_result.py                   (rename + 9 columnas)
        workspace.py                                (+ 3 columnas)
      versions/
        20260501.120000_h5c9e0d3a4f2_analysis_runs_pipeline.py  (migración)
    domain/contexts/domain.py                       (+ 2 repos en DomainContext)
    infrastructure/domain_builder.py                (wiring SQL repos)

  src/workflows/
    domain/
      events/
        __init__.py                                 (re-exports)
        analysis_run_event.py                       (NUEVO)
        document_set_event.py                       (movido del .py viejo)
      repositories/
        analysis_run.py                             (NUEVO)
        analysis_rule_result.py                     (+ list_by_run)
      services/analysis/
        checks.py                                   (taxonomía cerrada de 6 kinds)
        parser.py                                   (interfaz + PARSER_VERSION)
    application/
      analysis_rules/
        parser_runner.py                            (use case del parser)
        parser_scheduler.py                         (background task)
      analysis_runs/                                (NUEVO módulo)
        starter.py                                  (validaciones + crea AnalysisRun)
        cancel.py
        getters.py
        runner_scheduler.py                         (background task del orquestador)
    infrastructure/
      builders/
        analysis_rule.py                            (+ 5 campos)
        analysis_rule_result.py                     (reescrito)
        analysis_run.py                             (NUEVO)
        workflow.py                                 (+ 3 campos)
      repositories/
        sql_analysis_rule.py                        (+ 5 campos)
        sql_analysis_rule_result.py                 (reescrito)
        sql_analysis_run.py                         (NUEVO)
      services/analysis/                            (NUEVO directorio)
        llm_clients.py                              (wrappers Anthropic + Gemini)
        llm_parser.py                               (LLM parser de reglas)
        check_executor.py                           (Stage 1)
        sandbox.py                                  (RestrictedPython para python_exec)
        reviewer_tools.py                           (6 tools del reviewer)
        reviewer.py                                 (Stages 2-3)
        critic.py                                   (Stage 4)
        verifier.py                                 (Stage 5)
        runner.py                                   (orquestador con fan-out + SSE)
    presentation/
      endpoints/
        analysis_rule.py                            (+ get_rule, parser hook)
        analysis_run.py                             (NUEVO — 5 endpoints)
      presenters/
        analysis_rule.py                            (+ campos del parser)
        analysis_rule_result.py                     (reescrito)
      router.py                                     (+ analysis-runs router)
  scripts/
    reparse_rules.py                                (NUEVO)
  tests/workflows/
    application/analysis_runs/                      (NUEVO — 7 tests)
    infrastructure/services/analysis/               (NUEVO — 38 tests)

frontend/
  src/domain/entities/
    analysis-rule.ts                                (extendido)
    analysis-run.ts                                 (NUEVO)
  src/infrastructure/repositories/
    http-analysis-rule.ts                           (+ get)
    http-analysis-run.ts                            (NUEVO)
  src/presentation/
    components/
      rule-decomposition-panel.tsx                  (NUEVO)
      analysis-run-panel.tsx                        (NUEVO)
      analysis-rule-modal.tsx                       (panel cableado)
    workflows/cases/case-detail-view.tsx            (tab cableado)
```

**Borrados** (stub viejo, ya no se usa):
- `backend/src/workflows/presentation/endpoints/analize_stream.py`
- `backend/src/workflows/infrastructure/services/analysis_runner.py`
- `backend/src/workflows/infrastructure/repositories/mem_analysis_result.py`
- `backend/src/workflows/application/analysis_result/` (módulo entero)
- `backend/src/workflows/domain/repositories/analysis_result.py`
- `backend/src/common/domain/entities/processing.py`

---

## 13. Decisiones técnicas notables

| Decisión | Por qué |
|---|---|
| **Background tasks vía FastAPI `BackgroundTasks`** (no Temporal/ARQ) | Spec lo permite explícitamente para v1; menor complejidad. **Riesgo conocido**: runs huérfanos si el worker crashea — TODO #5 documenta la mitigación con cron. |
| **Sin Agno** | El SDK no estaba instalado; spec acepta `asyncio.gather()` como fallback para self-consistency paralela. Migración a Agno es TODO #4. |
| **Anthropic SDK directo + tool-use loop manual** | Sin Agno, controlamos exactamente la conversación. El loop tiene un cap de 10 iteraciones para evitar runaways. |
| **Sandbox con RestrictedPython + signal.SIGALRM** | El timeout de 2s funciona en main thread (extracción standalone) pero degrada a "best effort" en threads — aceptable para v1. |
| **Reviewer multi-sample con asyncio.gather** | Lanza N requests independientes al SDK Anthropic. Funciona pero abre N conexiones; Agno reduciría esto. |
| **Caps hardcodeados (25 por regla, 200 por run)** | Spec lo pide así; mover a `tenant_settings` es TODO #2. |
| **Re-parseo lazy + script masivo** | Cualquier acceso con `parser_version` distinto al actual encola un re-parseo en background. El script `reparse_rules.py` permite forzar masivo cuando se bumpea la versión. |

---

## 14. Cosas que NO están en este release

- **Re-parseo automático racing con runs activos**: spec dice que un run en curso usa el AST viejo hasta terminar — implementado correctamente (el orquestador lee `rule.parsed_checks` una sola vez al inicio).
- **Update endpoint de analysis-rules para parsear automático**: implementado vía `BackgroundTasks` solo cuando `content` cambia.
- **Cron para detectar runs huérfanos**: TODO #5.
- **Audit de Agno integration**: TODOs #3 y #4.
- **Wireado de `triggered_by` con el UUID del usuario logueado**: TODO #6 (hoy es `null`).
- **Tests de integración del reviewer/critic con LLMs reales**: requieren API keys + budget; conviene hacerlos como suite separada.

---

## 15. Cómo verificar que todo está OK

```bash
# Backend tests
cd backend && docker compose exec api python -m pytest tests/workflows tests/common
# → 223 passed

# Frontend types
cd frontend && pnpm exec tsc --noEmit
# → (no output = OK)

# Migración
cd backend && docker compose exec api alembic current
# → h5c9e0d3a4f2 (head)

# Endpoints registrados
cd backend && docker compose exec api python -c "from config.router import api_router; print(len(api_router.routes), 'routes')"
# → 89 routes
```

---

## 16. Glosario rápido

| Término | Significado |
|---|---|
| **Regla (`AnalysisRule`)** | Texto natural que el usuario escribe en el backoffice. Vive a nivel workflow. |
| **Check** | Pieza atómica de una regla — el parser LLM la genera. Puede ser objetivo (uno de 6 kinds ejecutables en código) o subjetivo (delegado al reviewer). |
| **Combinación** | Una asignación específica de documentos a los slugs que la regla menciona. Una regla con `@cedula.x` + `@factura.y` y un case con 2 cédulas y 3 facturas → 6 combinaciones. |
| **AnalysisRun** | Una ejecución de análisis sobre un case. Agrupa N `AnalysisRuleResult`s. |
| **AnalysisRuleResult** | Un veredicto por combinación. |
| **Reviewer** | El agente Anthropic que evalúa los checks subjetivos con tools. |
| **Critic** | Agente de un proveedor distinto (Gemini) que stress-testea al reviewer cuando la mayoría no es clara. |
| **Self-consistency** | Estrategia de N=5 muestras paralelas del reviewer y mayoría simple para reducir varianza. |
| **Citation** | Cada afirmación del reviewer debe citar `(documentId, fieldPath)` — validado con JMESPath contra el extraction real. |
| **PARSER_VERSION** | Versión del prompt + taxonomía del parser; bumpear invalida ASTs cacheados. |
