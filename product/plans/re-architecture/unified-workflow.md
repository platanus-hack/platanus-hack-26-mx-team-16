---
feature: re-architecture
type: plan
status: implemented
coverage: 92
audited: 2026-06-16
---

# Propuesta E7 · Workflow único con capacidades derivadas + caso universal

> **Estado:** dirección decidida en exploración con Vic (2026-06-11) · **propuesta, sin compromiso de
> implementación** · prerequisito **CUMPLIDO**: pipeline 1:1 implementado el 2026-06-11
> (`product/plans/pipeline/pipeline.md` + ADR 0002, migración `9b1c7e2af40d`; golden ✓, dev migrado 10↔10).
> Cuando se decida ejecutar: revisar punto a punto como el plan de pipeline, y recién entonces ADR.
> *(Actualizado tras la implementación del 1:1 — revisión contra código 2026-06-11.)*

---

## 0. Decisiones ya tomadas en el brainstorm (2026-06-11)

| # | Decisión | Resolución |
|---|---|---|
| 1 | Fuente de verdad de capacidades | **Derivadas del pipeline** (cero columnas nuevas; sin drift flag↔receta). |
| 2 | Existencia de casos | **Caso universal**: todo upload/ingesta crea (o encuentra) su caso; straight-through trivial si la receta no tiene gates. |
| 3 | Registro | Propuesta E7 (este doc) + nota en memoria; ADR recién al comprometer implementación. |

---

## 1. Tesis

Un **solo tipo de workflow**. Lo que un workflow "puede hacer" no lo declara un enum
(`workflow_type STANDARD|ANALYSIS` muere): lo **deriva su pipeline** (fases + policies de la versión
vigente). Agregar una capacidad = una **edición guiada del pipeline** (macro/wizard que inserta fases y
scaffolds de policies y publica v+1). El editor de fases (tab «Pipeline» del detalle, ADR 0002) sigue
siendo la vista avanzada.

Jerarquía final del modelo:

```
Workflow ──1:1── Pipeline (ADR 0002 · IMPLEMENTADO)
                   └─ WorkflowCase      = contenedor de negocio UNIVERSAL (timeline, estado, output)
                        └─ DocumentSet  = registro técnico del run de UN archivo (seq/replay, attempts, duración)
                             └─ WorkflowDocuments (reales + virtuales EXTERNAL_DATA/TOOL)
```

**Por qué encaja:** hoy `WorkflowDocumentSet` ya es un run-record (`file_id` singular,
`processing_job_id`, `last_seq`, `attempts`, `duration_ms`) y ya tiene FK `workflow_case_id`; el
dispatcher ya sirve ambos modos. La dualidad solo existe porque en STANDARD el set juega ambos roles.

**Evidencia nueva post-1:1 (el patrón ya debutó en producción de código):** los entry points existen
(`application/pipelines/entry_points.py::EntryPoint{INGEST,REEXTRACT,DATA}` + `select_phases` +
`PipelineRunInput.entry_point`), y la **primera capacidad derivada del pipeline ya está viva**: m2m
`_start_data_run` responde **409 si `select_phases(version.phases, EntryPoint.DATA)` está vacío** — es
decir, «acepta datos» ya se deriva de las fases, no de un flag. `derive_capabilities` (F0) generaliza
exactamente ese patrón.

## 2. Mapa de capacidades (derivación)

| Capacidad | Se deriva de | Qué desbloquea en UI/API |
|---|---|---|
| Extracción | fases document-scope (base, siempre) | upload, docs, re-extracción |
| Expediente multi-doc | `await_documents` + CompletenessPolicy | completitud, `ready`/force, badge RECEIVING |
| Análisis / reglas | fase `analyze` | tab reglas, runs de análisis, `/cases/{id}/data` |
| Confianza capa-2 | fase `assess` | merge capa-1/2, señales |
| Enriquecimiento | fase `enrich` | tools firmadas, docs TOOL |
| Aclaraciones | fase `await_clarification` | `case.needs_clarification` |
| Revisión humana | ActivationPolicy.stages | colas L1/L2, claim/lock, corrections |
| Salida estructurada | fases `output`+`deliver` | output schema, destinos, webhooks |
| Fan-out | `classify_pages.fan_out` | child cases, lineage |
| QA | `qa_sample_rate` | cola QA staff, métricas |
| Canales / sources | conexiones (ya ortogonal) | igual que hoy |

Implementación: servicio de dominio `derive_capabilities(version: PipelineVersion) -> set[Capability]`,
expuesto en el presenter del workflow para que el FE gatee tabs/acciones. Una sola función, testeable puro.
Generaliza el patrón ya vivo en m2m (`select_phases(…, DATA)` vacío ⇒ 409) y se apoya en `PhaseKind` +
el catálogo único `domain/services/phase_catalog.py` (E6) + las policies de la versión vigente.

## 3. Caso universal — qué cambia

- **Dispatcher de uploads**: find-or-create de caso `per_upload` antes de crear el set (los canales E6 ya
  tienen `case_strategy`; ingest ya auto-crea casos; el dispatcher ya resuelve la receta por
  `find_by_workflow` post-1:1). El run document-scope queda colgado del caso. La validación a relajar
  está en `dispatcher.py:203-210` (`WorkflowTypeMismatchError`, doble guard type↔`workflow_case_id`).
- **Straight-through**: receta sin gates ⇒ `RECEIVING→PROCESSING→COMPLETED` sin fricción (es el Caso 4 E6).
- **Set degradado a registro técnico**: conserva seq/replay SSE, `starting_seq` de re-extracción, jobs
  `/v1/extract` y el golden — nada de eso se toca. Su rename `document_set` → **`processing_job`** quedó
  zanjado como fase standalone post-E7 (spec: `product/plans/processing-jobs/rename-processing-job.md`).
- **Se disuelve la limitación de docs virtuales** (solo-con-caso): todo flujo tiene caso, enrich siempre
  puede persistir su doc TOOL.
- **FE**: la vista por defecto de todo workflow pasa a ser la de casos (E4 ya la construyó); la tabla de
  sets queda como vista técnica de runs (o dentro del caso).
- **`workflow_type` muere**: se retira el enum, las validaciones del dispatcher/creator y el
  `workflowType` de plantillas/bundles (la clase de bug «template ignoraba workflowType» de E6 se vuelve
  imposible).

## 3.bis ¿Qué pasa con los workflows existentes? (aclaración 2026-06-11)

**ANALYSIS → cambio CERO de comportamiento; solo pierde la etiqueta.** Post-ADR 0002 su pipeline
(propio, 1:1) ya define todo lo que hace: casos, máquina de estados, revisión, M2M, webhooks — nada de
eso depende del enum. En F2 se borra la columna sin migración de comportamiento; las tabs del FE que hoy
se muestran «porque es ANALYSIS» pasan a mostrarse «porque su pipeline tiene `analyze`/stages/…»
(mismas tabs, otra razón); los guards `WorkflowTypeMismatchError` desaparecen porque el caso siempre
existe. Upload a un caso existente sigue igual; upload «suelto» auto-crea caso `per_upload`.

**STANDARD → es el que realmente cambia.** Gana caso `per_upload` straight-through
(`RECEIVING→PROCESSING→COMPLETED`), la vista de casos como default, y acceso a docs virtuales/enrich
persistente. Su tabla de sets queda como vista técnica de runs.

**Definición operativa post-E7:** «workflow de análisis» deja de ser un tipo y pasa a ser una zona del
espectro de configuración — extract-only, extract+analyze sin revisión, o expediente completo son el
mismo (y único) tipo de workflow con distintas fases/policies.

## 4. Secuencia tentativa (post pipeline 1:1)

| Fase | Contenido |
|---|---|
| **F0** | `derive_capabilities` + exposición en presenter + FE gatea tabs por capacidad (sin tocar datos). |
| **F1** | Caso universal en dispatcher de uploads (`per_upload`) + casos como vista por defecto en FE. Incluye **relajar la validación type↔caso del dispatcher** (hoy exige STANDARD sin `workflow_case_id` / ANALYSIS con él — deja de aplicar). |
| **F2** | Retirar `workflow_type` (enum, validaciones, plantillas/bundles, FE). Incluye el **creator**: hoy clona `recipes.default_pipeline_template(workflow_type)` (STANDARD→extraction, ANALYSIS→analysis) — pasa a plantilla única + selector explícito en el alta. También caen `WorkflowTypeMismatchError` y los guards del dispatcher. |
| **F3** | Wizard «Agregar capacidad» (macros guiadas sobre el editor: insertan fases/policies, publican v+1). |
| **F4** | Limpieza + regresión + E2E vivo. Incluye el retiro definitivo de los slugs canónicos de `recipes.py` (`STANDARD_PIPELINE_SLUG`, `field-re-extraction`, `data-analysis`, …): post-1:1 siguen vivos solo como plantillas y referencia de la migración `9b1c7e2af40d` — al morir `workflow_type` quedan sin consumidores. |

## 5. Riesgos y preguntas abiertas (resolver al planificar en serio)

1. **Naming de casos per-upload** — ¿`name` = file_name? ¿numerador por workflow? (UX de la lista.)
2. **Agrupación en uploads** — ¿solo `per_upload`, o exponer `per_sender`-style también en UI algún día?
3. **Migración de datos** — dev-only hoy (trivial: backfill caso por set existente o solo flujos nuevos),
   pero si se pospone a post-prod el backfill se encarece.
4. **Golden/regresión** — el run estándar gana una fila de caso; el golden vigila `final_state` del
   intérprete, no debería moverse — verificar.
5. **Superficie** — ~78 archivos tocan `document_set`, ~86 `workflow_case`; el cambio es mayormente
   aditivo pero el blast radius de FE (vista por defecto) es real.
6. **Capacidades con prerequisitos** — p.ej. revisión exige `analyze`; el wizard debe ordenar/insertar
   dependencias (mismo validador del publish, `validate_phases`).

## 6. Relación con lo ya decidido

- **ADR 0002 (pipeline 1:1) — IMPLEMENTADO 2026-06-11** (migración `9b1c7e2af40d`; golden byte-idéntico;
  dev migrado 10 workflows ↔ 10 pipelines): E7 arranca sobre terreno ya validado. Pendiente heredado de
  ese trabajo (no de E7): squash de la cadena de migraciones antes del merge + E2E Playwright vivo del
  editor/duplicar.
- **D6 amendada** (doc-types workflow-scoped) y **«Duplicar workflow»** (ya existe:
  `application/workflows/duplicate.py` + `POST /v1/workflows/{id}/duplicate`) componen sin cambios.
- La tesis re-arq («pipeline-as-data, un motor») llega a su forma final: *un solo tipo de workflow cuyo
  comportamiento completo es data editable*.
