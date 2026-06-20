---
status: done
owner: Vic
created: 2026-06-17
completed: 2026-06-17
---

# Extraction Gate Consolidation

> **HECHO 2026-06-17** (hard cutover). Backend 1435 tests verde (6 fallas pre-existentes
> ajenas: integration/llm + script_transport); FE tsc 0 + vitest 9/9. Pendiente operativo:
> re-seed dev (versiones publicadas viejas con confidence_gate/review_gate).

## Objetivo
Colapsar `confidence_gate` + (camino gate de) `await_clarification` + `review_gate`
en **una sola fase durable `extraction_gate`** (case-scope, PRE-analyze). Eliminar el
acoplamiento por `scratch["gate"]`. Mantener `approval` (Gate 2, L1/L2) intacto.

## Decisión de diseño (ADR-able)
**Branch-inside-phase, no branch-as-structure.** NO se agregan nodos condicionales/loop
al pipeline (ver discusión: el `when` cubre condicionales; los loops viven en fases
durables). La rama clarify↔review pasa de ser estructura (3 fases + variable en scratch)
a lógica local de `extraction_gate`. Esto es consistente con la decisión de no agregar
control-flow genérico.

## Por qué existían 3 fases
El pipeline es lineal (sin if/else). Para expresar "si baja confianza → clarify, si no →
review, si no → continue" se simulaba una rama: `confidence_gate` computa una `decision`
en `scratch["gate"]` y `await_clarification`/`review_gate` son no-ops salvo que la
decisión les toque. Es un workaround por falta de branching.

## Las DOS compuertas (no se tocan ambas)
- **Gate 1 (pre-analyze, EXTRACCIÓN):** confianza de campos → clarify (al remitente) o
  review (staff corrige campos). ⇒ **esto se consolida en `extraction_gate`.**
- **Gate 2 (post-analyze, VEREDICTO):** sign-off del resultado con N niveles L1/L2 ⇒
  ya es UNA fase (`approval` + `ActivationPolicy.stages`). **Se deja igual.**

## Fase nueva: `extraction_gate`
1. `PhaseKind.EXTRACTION_GATE` (enum `common/domain/enums/pipelines.py`), scope=case.
2. `ExtractionGateConfig` (`phase_configs.py`): audiencias de clarify y de review,
   `expires_in_hours`/`resolution_timeout`/`on_timeout` (fusión de ConfidenceGateConfig +
   AwaitClarificationConfig + bits de gate de HumanReviewConfig).
3. Handler (`gate_phases.py` o módulo nuevo):
   - lee `scratch["policies"]["activation"]`.
   - `EVALUATE_ACTIVATION_GATE_ACTIVITY` → items.
   - sin items ⇒ continue (checkpoint byte-compat con `_legacy_confidence_gate`).
   - con items ⇒ branch local por `policy.on_low_confidence`:
     - `clarify` → reusa `OpenClarificationTask` + NEEDS_CLARIFICATION + webhook + espera
       (timeout/escalamiento de await_clarification) → PROCESSING.
     - `review` → reusa la lógica de `_gate_review` (open review task + NEEDS_REVIEW + espera).
   - fallback (sin policy/sin caso) ⇒ continue (compat E3/E4).

## Remociones
- `confidence_gate` + `_set_gate_result` + productor de `scratch["gate"]`.
- `review_gate` (human_review kind=review trigger=gate) + `_gate_review` → absorbidos.
- `await_clarification`: **conserva su camino standalone F6** (pausa de aclaración
  incondicional); solo se le quita el camino gate-driven.

## Wiring a actualizar
- `runtime` PHASE_LIBRARY/PHASE_SCOPES (alta de 1, baja de 2 kinds).
- `capability_macros`: capacidad CLARIFICATION + orden canónico `_CANONICAL_ORDER` +
  `derive_capabilities` (detectar `extraction_gate`).
- `phase_catalog`: `configSchema` de `extraction_gate`.
- `recipes.standard_case_phases` + fixtures (`pedidos_multicanal`, `circular_judicial`).
- FE: spine adapter (stages confidence/clarify/review → 1 stage `extraction_gate`),
  `phase-config-form`, UI de capacidades, `pipeline-validation` (orden de scope).

## Riesgos / estrategia de test
- **Golden E4/E5** codifican la secuencia vieja + checkpoints/eventos ⇒ re-grabar.
- **E2E Playwright vivos** ejercen el gate ⇒ correr/ajustar después.
- Unit nuevos: continue / clarify / review / fallback legacy byte-compat.
- Sin migración (las fases viven en el JSONB del recipe). Versiones ya publicadas en dev
  con fases viejas ⇒ re-seed/re-publish.

## ⚠️ Restricción crítica (Temporal replay · versiones selladas)
Las versiones de pipeline son **inmutables** y el motor es Temporal (replay-safe). Un run
en vuelo (p. ej. pausado en `await_clarification`) o una versión ya publicada que referencia
`confidence_gate`/`review_gate` **falla en replay** si borro esos handlers. Dos estrategias:
- **Hard cutover (dev/pre-release):** borrar handlers viejos + re-seed/re-publish de los
  workflows dev a `extraction_gate`. Runs en vuelo viejos se orfanan (aceptable en dev).
  Estado final limpio. Apropiado porque toda la branch `feat/re-arch` es pre-release.
- **Expand/contract:** mantener handlers viejos REGISTRADOS (solo legacy/replay), sacarlos
  del recipe/template/editor, agregar `extraction_gate`. Retiro de handlers = cleanup
  posterior gated en "0 runs en vuelo con versiones viejas". Más seguro, más sucio.

## Mapa de cambios (de code-explorer, archivo:línea)
Backend handlers/registro: `gate_phases.py` (confidence_gate:103, _set_gate_result:55,
_legacy:64), `pause_phases.py` (await_clarification:323 + guard scratch:329, _gate_review:881,
human_review router:413, _open_and_wait cfg_model:181). Enum: `common/domain/enums/pipelines.py`
(CONFIDENCE_GATE:43, AWAIT_CLARIFICATION:52, HUMAN_REVIEW:53). Registro: `runtime.py`
(register_phase:159, PHASE_LIBRARY:151, PHASE_SCOPES:156). Config: `phase_configs.py`
(ConfidenceGateConfig:155, AwaitClarificationConfig:184, HumanReviewConfig:206,
PHASE_CONFIG_MODELS:264). Capacidades: `capability_macros.py` (_CANONICAL_ORDER:23, _MACROS
CLARIFICATION:69), `capabilities.py` (CLARIFICATION:82, HUMAN_REVIEW:95). Catálogo:
`phase_catalog.py` (_PHASE_DESCRIPTIONS:108). Recipe: `recipes.py` (standard_case_phases:137-142).
`scratch["gate"]` consumidores: pause_phases 326/429/889 + gate_phases 61.

Tests (golden/estructura a re-grabar/ajustar): `test_confidence_gate.py`,
`test_activation_gate_phase.py` (asserts scratch["gate"] 83/102/114/126/139),
`test_case_pause_phases.py` (gate clarify 246, gate_review 536/580; F6 332/562 deben SOBREVIVIR),
`test_pipeline_structure_e4.py` (SCOPES 29-35), `test_phase_scopes.py` (34, 86-88),
`test_phase_configs.py` (96), `test_entry_points.py` (179).

FE: `pipeline-stages.ts` (STAGE_DEFS quality 62-71, PHASE_LABELS 111-127, stageIdForPhase 160),
`spine/adapter.ts` (ENGINE_KIND 61, TEMPLATE_CONFIG 70 review_gate, SPINE_STAGES quality 165-203,
realEditorKind 76), `spine/types.ts`, `spine/icons.tsx`, `executions/phase-meta.ts`.

## Secuencia (staged, additivo primero — vale para ambas estrategias)
1. `PhaseKind.EXTRACTION_GATE` + `ExtractionGateConfig` + handler nuevo (additivo).
2. recipes/template/fixtures → `extraction_gate`; capabilities/catalog/FE.
3. Tests del handler nuevo + ajustar estructura/scope.
4. **(según estrategia)** remover handlers viejos + acoplamiento `scratch["gate"]`, o dejarlos legacy.
5. re-grabar golden, suite verde, E2E, re-seed dev.

## Decisiones (cerradas con Vic 2026-06-17)
- **Nombre de la fase:** `extraction_gate`.
- **clarify ↔ review:** mutuamente excluyentes (un `on_low_confidence` por breach).
- **`await_clarification`:** se CONSERVA standalone (camino F6); solo se le quita el
  camino gate-driven.
