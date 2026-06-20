---
feature: pipeline
type: plan
status: implemented
coverage: 92
audited: 2026-06-16
---

# Plan de implementación · Pipeline propiedad del workflow (1:1)

> **Estado:** APROBADO punto a punto (2026-06-11) · implementación **pendiente de luz verde de Vic**.
> **Decisión formal:** ADR `docs/adr/0002-pipeline-propiedad-del-workflow.md`.
> Branch `feat/re-arch` (todo sin commitear, dev-only, sin prod ⇒ migración barata).
>
> **Decisión de Vic:** cada workflow es **dueño** de su pipeline (`Pipeline` + `PipelineVersion`).
> Se elimina el modelo *tenant-scoped compartido*. El reúso entre workflows se hace con **"Duplicar
> workflow"** (deep-copy). Además: **UI para editar las fases del pipeline en el detalle del workflow.**

---

## 0. Decisiones zanjadas en la revisión (no re-litigar)

| # | Decisión | Resolución |
|---|---|---|
| 1 | Entry points | **Sub-segmentos de UN pipeline por workflow** (no varios pipelines nombrados). |
| 2 | `/cases/{id}/data` sin fase `analyze` | **409** error de configuración. |
| 3 | Migración Alembic | **Nueva ahora; squash antes del merge** de `feat/re-arch`. |
| 4 | `slug` del pipeline | **Se conserva informativo** (display + export/import), único por workflow. |
| 5 | Repo `find_by_slug` / `list_by_tenant` | **Se eliminan** del contrato (sin deprecación). |
| 6 | Endpoints tenant-level `POST/GET /v1/pipelines` | **Se retiran**; reemplazo `GET\|POST /v1/workflows/{id}/pipeline[/versions]`. `phase-catalog` se queda. |
| 7 | Alcance de «Duplicar workflow» | Copia doctypes + reglas + pipeline/policies + KB refs. **Excluye** docs/casos, sources/destinations (secretos ⇒ `requiresConfiguration`) y miembros. |
| 8 | Ruta standalone `/pipelines` (FE) | **Se borra** (sin redirect). |
| 9 | Tab «Pipeline» en detalle del workflow | **Visible para todos los roles (read-only)**; editar/publicar gateado por acción `manage` (matriz E5). |
| 10 | ADR | Escrito: `docs/adr/0002`. |
| 11 | Sub-segmento `reextract` | **Solo la fase `extract`** (paridad con `field-re-extraction` actual; NO re-clasifica). |

---

## 1. Objetivo y forma final

**Hoy:** `Pipeline` es *tenant-scoped* (`tenant_id` + `slug` único por tenant). Varios workflows comparten el
mismo pipeline por referencia (`workflows.pipeline_id`), con *fallback* al `standard-extraction` del tenant.
Esto causó el BUG 3 crítico de E6 (editar un pipeline compartido reescribía la receta de los hermanos).

**Objetivo:** relación **1:1 workflow ↔ pipeline**. El workflow posee su pipeline; editarlo nunca puede afectar
a otro. Las recetas de sistema compartidas desaparecen; `recipes.py` queda como **plantilla por defecto** que se
**copia** al crear el workflow (*copy-on-create*).

### Un pipeline, varios puntos de entrada (zanjado #1)

Hoy existen recetas de sistema que **no** son workflows, sino **modos de entrada** distintos:

| Receta hoy (slug) | Punto de entrada | Pasa a ser |
|---|---|---|
| `standard-extraction` | upload / ingesta de docs nuevos | pipeline propio, **todas** las fases |
| `field-re-extraction` | "Extraer Campos" (`re_extractor.py:221`) | pipeline propio, **solo `extract`** (zanjado #11) |
| `data-analysis` | `POST /v1/cases/{id}/data` (datos virtuales) | pipeline propio, **desde `analyze`** en adelante |
| `standard-analysis` / `standard-case` / `extract-assess` | pipelines de caso completos | plantillas de copy-on-create |

El motor ya tiene las piezas (`scope` document|case, extract-only E1 vía `initial_artifacts` +
`starting_seq`, arranque en `analyze` E2). Lo nuevo es **seleccionar el sub-segmento desde el pipeline
propio** en lugar de resolver un slug distinto.

> **Alternativa descartada** (revisión 2026-06-11): varios pipelines nombrados por workflow
> (main/reextract/data). Más flexible pero rompe el 1:1 y reintroduce «¿qué receta corre?».

---

## 2. Modelo de datos

### `Pipeline` (`backend/src/workflows/domain/models/pipeline.py`)

| Campo | Cambio |
|---|---|
| `workflow_id: UUID` | **NUEVO** — dueño (FK a `workflows`, **único** ⇒ 1:1, NOT NULL). |
| `tenant_id` | se mantiene (denormalización para queries/authz). |
| `slug`, `name` | se mantienen para display/export (zanjado #4); unicidad nueva = por `workflow_id`. |
| `kind`, `status`, `current_version` | sin cambios. |

`PipelineVersion` y `PhaseSpec`: **sin cambios** (inmutables, append-only — el contrato de determinismo de
Temporal se preserva). El sellado por run (`pipeline_id` + `version`, `workflow_cases.pipeline_version_id`)
sigue igual.

### Migración (zanjado #3: nueva ahora, squash antes del merge)

Nueva migración forward `add_pipeline_workflow_ownership`:

1. `ALTER TABLE pipelines ADD COLUMN workflow_id UUID NULL` (+ FK).
2. **Backfill** (todo en la migración, dev-only):
   - Por cada `workflow` con `pipeline_id`: si su pipeline está **compartido** (referenciado por >1 workflow, o
     es un seed canónico `standard-*`/`field-re-extraction`/`data-analysis`), **clonar** el pipeline + su
     `current_version` a uno nuevo, set `workflow_id`, y **rebind** `workflows.pipeline_id` al clon.
   - Por cada `workflow` sin `pipeline_id`: crear un pipeline propio desde la plantilla por defecto
     **según su `workflow_type`** (v1) y bindear.
   - Borrar los pipelines tenant-level que queden **huérfanos** (sin `workflow_id`). **Efecto verificado:**
     `workflow_cases.pipeline_id`/`pipeline_version_id` son FK `ondelete="SET NULL"` ⇒ los casos dev
     históricos que sellaron versiones de `data-analysis`/`standard-*` pierden el sello (quedan NULL).
     Aceptado: dev-only, datos desechables; en prod habría exigido archivado en vez de borrado.
3. `ALTER COLUMN workflow_id SET NOT NULL` + `UNIQUE(workflow_id)`.
4. Drop del índice único `(tenant_id, slug)`; add `UNIQUE(workflow_id)` (y opcional `INDEX(tenant_id)`).

---

## 3. Backend — capa por capa

### 3.1 Repositorio (`domain/repositories/pipeline.py` + `infrastructure/repositories/sql_pipeline.py`)

- **NUEVO** `find_by_workflow(workflow_id) -> Pipeline | None`.
- `find_by_id(id, tenant_id)` se mantiene (lo usa el handler de versiones / fix IDOR de E6).
- **Eliminar** `find_by_slug` y `list_by_tenant` (zanjado #5) y todos sus usos.

### 3.2 Resolver (`application/pipelines/resolver.py`)

Se vuelve trivial: `resolve_workflow_pipeline(workflow_id)` → `find_by_workflow` → `current_version` →
`WorkflowPipelineNotConfiguredError` (409). **Se elimina** el fallback a `STANDARD_PIPELINE_SLUG`.

### 3.3 Selección de sub-segmento (NUEVO · `application/pipelines/entry_points.py`)

`select_phases(version: PipelineVersion, entry: EntryPoint) -> list[PhaseSpec]` donde
`EntryPoint ∈ {ingest, reextract, data}`:

- `ingest` → todas las fases (run completo actual).
- `reextract` → **solo la(s) fase(s) `extract`** (zanjado #11) → run extract-only.
- `data` → fases desde la primera `analyze` en adelante (`analyze`, gates, `output`, `deliver`).
  Sin `analyze` en el pipeline ⇒ **409** (zanjado #2).

### 3.4 Creator (`application/workflows/creator.py`)

`execute()` pasa a **crear el pipeline propio** dentro de la misma transacción:

1. Elegir plantilla por `workflow_type` (`STANDARD`/`ANALYSIS` → builder correspondiente de `recipes.py`).
2. `Pipeline(workflow_id=…, tenant_id=…, slug=…, kind=…)` + `add_version(v1)` + `current_version=1`.
   **Ojo:** `Workflow.slug` es **nullable** (`str | None`, solo lo setea el flujo W4 de export/import) —
   el slug del pipeline necesita fallback: `workflow.slug or f"wf-{workflow.uuid.hex[:8]}"` + sufijo.
3. `workflow.pipeline_id = pipeline.uuid`.

Quitar la rama `find_by_slug(STANDARD_PIPELINE_SLUG…)`.

### 3.5 Onboarder (`tenants/.../onboarder.py`)

**Dejar de sembrar** pipelines tenant-level (`_seed_pipeline`). Las plantillas viven en `recipes.py` como
código (fuente del copy-on-create). `recipes.py` conserva los *phase builders* y **pierde** los slugs/seeds
compartidos.

### 3.6 Reescribir consumidores de recetas compartidas

| Archivo | Cambio |
|---|---|
| `application/document_sets/re_extractor.py:221` | pipeline propio con `entry=reextract`. |
| `application/workflow_cases/m2m.py` (data) | `case.pipeline_id` = pipeline del workflow; `entry=data`. |
| `application/sources/ingest.py:55` | quitar `DEFAULT_PIPELINE_SLUG`; resolver por workflow. |
| `application/document_sets/dispatcher.py` | resolver por workflow (no slug). |
| `application/workflows/import_export/importer.py` | **append-only sobre el pipeline propio** (ver nota ⬇) |

> **Nota importer (corrección de revisión 2026-06-11):** con `UNIQUE(workflow_id)`, el import **no puede
> crear un pipeline nuevo** para un workflow que ya tiene el suyo (= todos, post copy-on-create). El import
> pasa a **appendear una versión nueva al pipeline propio** del workflow destino, conservando el patrón
> `_PendingPipelineBind` de E6 (avanzar `current_version` solo si `rules.failed == 0`). Desaparecen
> `_is_shared_pipeline`, `_CANONICAL_PIPELINE_SLUGS` y el find-or-create por slug del pipeline.

### 3.7 Duplicar workflow (NUEVO · `application/workflows/duplicate.py`)

`DuplicateWorkflow(source_workflow_id, new_name)` — alcance zanjado #7:

- Flujo: crear workflow nuevo (el copy-on-create de §3.4 le da su pipeline v1) → importar el bundle del
  origen en memoria ⇒ el importer **appendea v2 al pipeline propio** del nuevo (ver nota importer §3.6)
  y avanza `current_version` al resolver reglas. Sin pipelines sueltos en ningún paso.
- Copia: doctypes + reglas + pipeline/policies + KB refs por slug. Excluye: docs/casos/sets,
  sources/destinations (⇒ `requiresConfiguration`), miembros.
- Endpoint: `POST /v1/workflows/{id}/duplicate` (JWT; gated `manage`).

### 3.8 Endpoints (zanjado #6)

- **Retirar** `POST /v1/pipelines` y `GET /v1/pipelines` tenant-level.
- `GET /v1/pipelines/phase-catalog` — sin cambios.
- **NUEVO** `GET /v1/workflows/{id}/pipeline` (+ `/versions`, `?validate_only=`) — mismo 422 del publish.
- Authz: leer = cualquier rol del workflow; editar/publicar = acción **`manage`** (zanjado #9).

---

## 4. Frontend — editor en el detalle del workflow

El editor visual **ya existe** (`src/presentation/pipelines/pipeline-editor.tsx`; store
`application/stores/pipeline-editor-store.ts`; queries `application/hooks/queries/pipelines.ts`).
El trabajo es **embeberlo, scoped al workflow**:

1. **Nueva ruta tab**: `src/app/(protected)/workflows/[wf_slug]/pipeline/{layout,page}.tsx` (espejo de las
   tabs existentes). Recordar: `[wf_slug]` transporta el **UUID** del workflow.
2. **Reusar `pipeline-editor.tsx`** parametrizado por `workflowId`; ajustar store/queries a `workflowId`.
3. **Sidebar** (`presentation/workflows/shared/workflow-sidebar.tsx`): ítem "Pipeline" **visible para
   todos**; controles de edición/publicación gateados por `manage` (zanjado #9 — read-only para el resto).
4. **Botón "Duplicar workflow"** en lista y/o header del detalle → BFF → `POST /v1/workflows/{id}/duplicate`.
5. **Borrar** `src/app/(protected)/pipelines/` (zanjado #8 — sin redirect) + `pipelines-view.tsx` +
   `create-pipeline-dialog.tsx` si quedan sin uso.
6. **BFF routes**: `app/api/workflows/[id]/pipeline/route.ts` y `app/api/workflows/[id]/duplicate/route.ts`.

---

## 5. Secuencia de implementación (cada fase deja la suite verde)

| Fase | Contenido | Gate |
|---|---|---|
| **P0** | Modelo + migración + repo (`workflow_id`, `find_by_workflow`, drop slug-unique). | migración up/down limpia. |
| **P1** | Creator copy-on-create + onboarder deja de sembrar + resolver trivial. | **golden `standard_v1` byte-idéntico**. |
| **P2** | `entry_points.select_phases` + rewire `re_extractor`/`m2m data`/`ingest`/`dispatcher`. | tests de cada entry-point. |
| **P3** | `DuplicateWorkflow` + alinear importer (re-scope = norma) + retirar endpoints tenant-level. | test: duplicado independiente. |
| **P4** | FE: tab editor + sidebar + duplicar + BFF + borrar standalone. | tsc + render/save. |
| **P5** | Regresión + E2E vivo + limpieza `recipes.py`/slugs muertos + repo methods. | suite verde + E2E. |

---

## 6. Pruebas

- **Backend:** resolver (workflow→pipeline propio, 409 sin receta) · creator (v1 copiada, `current_version=1`)
  · `select_phases` por entry-point (ingest completo / reextract solo-extract / data desde analyze / data sin
  analyze ⇒ 409) · `DuplicateWorkflow` (deep-copy, **cero refs compartidas**) · migración backfill (compartido
  → clonado; huérfanos borrados) · importer append-only sobre pipeline propio · **IDOR de versiones**: la
  regresión E6 (`find_by_id` tenant-scoped antes de `get_version` ⇒ 404 cross-tenant) **se muda** al endpoint
  workflow-scoped nuevo — los tests de `test_pipeline_admin_endpoints.py` migran con él.
- **Golden / paridad (CRÍTICO):** `test_standard_v1_regression.py` debe seguir byte-idéntico — la plantilla
  por defecto del creator **es** la receta de hoy.
- **Frontend:** editor embebido renderiza/guarda contra el pipeline del workflow · read-only sin `manage` ·
  flujo duplicar.
- **E2E vivo (Playwright):** editar fases → publicar v2 → correr → comportamiento esperado; **duplicar
  workflow → editar el duplicado → el original NO cambia** (BUG 3 imposible por construcción).

---

## 7. Riesgos vigilados (decisiones: ver §0 — ya no hay abiertas)

1. **Paridad golden** — la plantilla por defecto debe igualar la receta actual; el golden es el guard
   (riesgo bajo: reusamos los mismos `*_phases()`).
2. **Cobertura de `select_phases`** — las 6 recetas actuales deben quedar cubiertas como sub-conjuntos
   (mapeo §1). Workflows reales sin la fase que su entry point necesita ⇒ 409 razonable (zanjado #2).
3. **Squash pre-merge** — recordar consolidar la cadena de migraciones antes de mergear `feat/re-arch`
   (zanjado #3).
4. **Cambio de comportamiento intencional en entry `data`** — hoy `data-analysis@v1` no tiene gates;
   con sub-segmentos, «desde `analyze` en adelante» incluye los gates post-analyze del pipeline propio
   (`confidence_gate`, `human_review`). Es lo deseado (el workflow define su flujo), pero los tests del
   entry `data` deben cubrir ambos pipelines: con y sin gates.

---

## 8. Inventario de archivos tocados (referencia rápida)

**Backend:** `domain/models/pipeline.py` · `domain/repositories/pipeline.py` ·
`infrastructure/repositories/sql_pipeline.py` · `common/database/models/pipeline.py` (ORM
`PipelineORM`/`PipelineVersionORM`; ahí vive el `uq_pipelines_tenant_slug` a dropear) ·
`application/pipelines/resolver.py` · `application/pipelines/entry_points.py` *(nuevo)* ·
`application/workflows/creator.py` · `application/workflows/duplicate.py` *(nuevo)* ·
`application/workflows/import_export/importer.py` · `application/document_sets/re_extractor.py` ·
`application/document_sets/dispatcher.py` · `application/workflow_cases/m2m.py` ·
`application/sources/ingest.py` · `domain/recipes.py` · `tenants/.../onboarder.py` ·
`presentation/.../workflow pipeline endpoints` *(nuevo wrapper; retirar los tenant-level)* ·
`common/database/versions/<migración>` *(nueva)*.

**Frontend:** `app/(protected)/workflows/[wf_slug]/pipeline/{layout,page}.tsx` *(nuevo)* ·
`app/api/workflows/[id]/pipeline/route.ts` *(nuevo)* · `app/api/workflows/[id]/duplicate/route.ts` *(nuevo)* ·
`presentation/pipelines/pipeline-editor.tsx` *(parametrizar)* · `presentation/workflows/shared/workflow-sidebar.tsx` ·
`application/stores/pipeline-editor-store.ts` · `application/hooks/queries/pipelines.ts` ·
`app/(protected)/pipelines/` *(borrar)* · botón duplicar en `workflows/page.tsx`.
