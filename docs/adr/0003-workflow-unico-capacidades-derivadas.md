# 0003 — Workflow único: capacidades derivadas del pipeline + caso universal

- **Estado:** accepted (decidido punto a punto con Vic; implementado 2026-06-11, F0–F3)
- **Fecha:** 2026-06-11
- **Decisores:** Vic
- **Origen:** exploración E7 sobre `product/plans/re-architecture/unified-workflow.md`; prerequisito ADR
  0002 (pipeline 1:1) cumplido. Detonante: la dualidad `workflow_type` STANDARD|ANALYSIS y
  la dualidad `WorkflowDocumentSet`↔`WorkflowCase`.

## Contexto y problema

Tras ADR 0002 cada workflow es dueño 1:1 de su pipeline. Pero seguía habiendo dos enums/flags
paralelos que **duplican** la información que ya vive en la receta:

1. **`workflow_type` (STANDARD|ANALYSIS)** — una columna que decidía (a) qué plantilla clona el
   creator, (b) si el dispatcher acepta `workflow_case_id`, (c) qué tabs muestra el FE, (d) qué
   `type` va en el webhook. Cada una de esas ramas puede **driftear** de lo que el pipeline
   realmente hace: un workflow typed ANALYSIS cuya receta solo extrae muestra tabs vacías; la
   clase de bug «la plantilla ignoraba `workflowType`» (E6) nace de aquí.
2. **`WorkflowDocumentSet` vs `WorkflowCase`** — el set ya era un *run-record* (`file_id`
   singular, `processing_job_id`, `last_seq`, `attempts`, `duration_ms`, FK `workflow_case_id`),
   pero en STANDARD jugaba ADEMÁS el rol de contenedor de negocio, porque esos workflows no
   tenían caso. La limitación «documentos virtuales solo con caso» se sigue de esa dualidad.

El patrón correcto ya había debutado: m2m `_start_data_run` responde **409 si
`select_phases(version.phases, EntryPoint.DATA)` está vacío** — «acepta datos» ya se derivaba de
las fases, no de un flag.

## Drivers

- **Cero drift flag↔receta:** lo que un workflow «puede hacer» debe ser función de su pipeline,
  no de un enum que se mantiene aparte.
- **Un solo modelo mental:** un solo tipo de workflow cuyo comportamiento completo es *data
  editable* (la receta), no dos clases con caminos separados.
- **Documentos virtuales siempre disponibles** (enrich/`POST /cases/{id}/data`): requiere que
  todo flujo tenga caso.
- **Aditividad:** el cambio es mayormente aditivo sobre ADR 0002; el blast radius real es la
  vista por defecto del FE.

## Opciones consideradas

- **A — Mantener `workflow_type` como fuente de verdad de capacidades.** Status quo: drift
  perpetuo, doble mantenimiento receta↔flag. Rechazada.
- **B — Columnas de capacidad explícitas** (un bool por capacidad). Otra fuente de verdad que
  driftea respecto de la receta. Rechazada.
- **C — Capacidades DERIVADAS del pipeline + caso universal** (esta decisión). Cero columnas
  nuevas; la receta es la única fuente de verdad.

## Decisión

Un **solo tipo de workflow**. Cuatro piezas:

1. **Capacidades derivadas (`derive_capabilities(version) -> set[Capability]`)** — servicio de
   dominio puro que introspecta las fases + policies de la versión vigente. Generaliza el patrón
   de m2m. El presenter del workflow expone `capabilities`; el FE gatea tabs/acciones contra él.
   Mapeo: `analysis`←fase analyze, `layer2_confidence`←assess, `enrichment`←enrich,
   `clarification`←await_clarification, `structured_output`←output+deliver,
   `multi_doc_dossier`←await_documents, `human_review`←fase human_review o
   ActivationPolicy.stages, `fan_out`←classify_pages.config.fan_out==child_cases,
   `qa`←ActivationPolicy.qa_sample_rate>0, `extraction`←fases document-scope (base).

2. **Caso universal** — todo upload find-or-create su caso `per_upload` (idempotente por
   archivo, nombre = file_name + sufijo) en el dispatcher; el run document-scope cuelga del
   caso. El **set queda degradado a run técnico** de UN archivo (conserva seq/replay/jobs). El
   guard `type↔workflow_case_id` desaparece. **Straight-through** (receta sin fases case-scope):
   `finalize` cierra el caso RECEIVING→PROCESSING→COMPLETED — instrucción `finalize_closes_case`
   sembrada por el intérprete (ausente ⇒ no-op ⇒ golden de extracción byte-idéntico). Con cola
   case-scope lo cierra `deliver`; con `scope="document"` lo maneja el run CASE#.

3. **`workflow_type` retirado** — muere el enum `WorkflowType`, la columna `workflows.workflow_type`
   (migración drop), las validaciones del dispatcher/ingest, el `type` del webhook y el
   `workflowType` de bundles. El **alta elige una PLANTILLA por slug** (`template_slug`:
   standard-extraction=default, standard-analysis, standard-case con policies, extract-assess) en
   vez de un «tipo»; los bundles de industria (Pedidos/Circular) siguen por create+import.

4. **Wizard «agregar capacidad»** — `apply_capability(phases, policies, capability)`: la inversa
   de `derive_capabilities`. Inserta las fases + scaffolds de policy en orden canónico (respeta
   el invariante de scope de `validate_phases`) y publica v+1 por el mismo camino que el editor.
   El editor de fases (ADR 0002) sigue siendo la vista avanzada.

Jerarquía final: `Workflow ─1:1─ Pipeline └─ WorkflowCase (contenedor universal) └─ DocumentSet
(run técnico de un archivo) └─ WorkflowDocuments (reales + virtuales)`.

## Consecuencias

- **Positivas:** el drift flag↔receta es imposible por construcción; la clase de bug
  template↔workflowType (E6) desaparece; los documentos virtuales (enrich/data) funcionan en
  todo flujo; el modelo mental es uno solo; agregar una capacidad es una edición de data.
- **Costo:** la vista por defecto del FE pasa a casos para todo workflow (cambio visible). Un
  workflow antes typed ANALYSIS con receta solo-extracción deja de mostrar tabs vacías (corrección
  intencional, no regresión).
- **Migración:** drop de `workflows.workflow_type` (`f1a2b3c4d5e6`, dev-only, up/down/up probado).
- **Slugs canónicos de `recipes.py`:** NO se retiran — F2 los repurposó como claves del registry
  de plantillas (`pipeline_template_for_slug`); el plan original asumía que quedarían sin
  consumidores, pero ahora SON los identificadores de plantilla.

## Pendientes (no bloquean la decisión)

- Squash de la cadena de migraciones antes del merge de `feat/re-arch` (heredado de ADR 0002).
- E2E vivo (Playwright) del flujo caso-universal + wizard.
- Retiro de la rama inerte `WorkflowDocumentsTable` en `document-sets-view` (hoy `isStandard=true`
  fijo; la rama de docs sueltos quedó inalcanzable).
