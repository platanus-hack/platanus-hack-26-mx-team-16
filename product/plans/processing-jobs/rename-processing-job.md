---
feature: processing-jobs
type: plan
status: implemented
coverage: 98
audited: 2026-06-16
---

# Mini-spec · Rename `document_set` → `processing_job`

> **Estado:** **IMPLEMENTADO 2026-06-12** · **mecánico, sin cambio de comportamiento**. **E7 ya
> está implementado** (F0–F4 + ADR 0003): este rename fue como fase standalone post-E7. Branch
> `feat/re-arch`, dev-only ⇒ migración barata. Ver §9 para decisiones resueltas y estado de gates.

## 1. Motivación

`WorkflowDocumentSet` no es un "conjunto de documentos": es el **registro técnico de procesar UN
archivo** (`file_id` singular) con semántica de *job con reintentos* — `status`, `attempts`, `error`,
`trigger` (USER/RETRY/ORPHAN_SWEEPER/SYSTEM), `duration_ms`, `last_seq`. Además: la re-extracción
**reutiliza la misma fila** (`REEXTRACT#{set}_seq{n}`), y el contrato M2M público **ya lo llama job**
(`POST /v1/extract` → `job_id`, `GET /v1/jobs/{id}`). El rename alinea DB ↔ dominio ↔ API pública en
una sola palabra. E7 (ya implementado) lo degradó formalmente a registro técnico bajo el caso
universal — este rename completa esa historia poniéndole el nombre correcto.

## 2. Mapa de renames

| Capa | Hoy | Queda |
|---|---|---|
| Tabla | `workflow_document_sets` | `processing_jobs` |
| Modelo dominio | `WorkflowDocumentSet` | `ProcessingJob` |
| Enums | `WorkflowDocumentSetStatus` / `…Trigger` | `ProcessingJobStatus` / `ProcessingJobTrigger` |
| Repo | `WorkflowDocumentSetRepository` | `ProcessingJobRepository` |
| Paquete app | `application/document_sets/` | `application/processing_jobs/` |
| **Campo string Temporal-ID** | `processing_job_id` (¡miente: es el workflow ID de Temporal!) | **`temporal_workflow_id`** |
| FK en `workflow_documents` | `document_set_id` | `processing_job_id` (UUID → `processing_jobs.uuid`) |
| Campo Temporal input | `DocumentProcessingInput.document_set_uuid` | `processing_job_uuid` |
| Módulos eventos SSE | `document_set_events.py` / `document_set_event_inputs.py` | `processing_job_events.py` / `…_inputs.py` |
| Rutas JWT (5) | `/{workflow_id}/document-sets[...]` | `/{workflow_id}/jobs[...]` (re-extract incluido) |
| FE query keys | `queryKeys.documentSets` | `queryKeys.processingJobs` |
| FE componentes/i18n | `document-sets/*`, claves i18n | `processing-jobs/*` (es/en) |
| Logs | `workflow_document_set.*`, `orphan_sweeper… document_set` | `processing_job.*` |

**Los dos renames de campo van en el MISMO commit** — `processing_job_id` cambia de significado
(string Temporal → FK UUID en docs); hacerlos por separado dejaría una ventana con dos sentidos.

## 3. Lo que NO cambia (verificado contra código)

- **Contrato M2M público: CERO cambio** — `/v1/extract`, `GET /v1/jobs/{id}`, `job_id` ya usan la
  palabra destino (ese es el punto).
- **Semántica seq/replay SSE**, `starting_seq` de re-extracción, `document_index`, `page_range`.
- **Estado del intérprete / golden**: verificado que `PipelineState`/artefactos **no** contienen claves
  `document_set` ⇒ los fingerprints golden no deberían moverse. Gate: golden byte-idéntico; si se
  mueve, investigar antes de re-grabar (no re-grabar a ciegas).
- Comportamiento: ninguno (rename puro).

## 4. Migración

Una migración: `op.rename_table("workflow_document_sets", "processing_jobs")` + renames de columnas
(`processing_job_id`→`temporal_workflow_id`; `workflow_documents.document_set_id`→`processing_job_id`)
+ renombrar índice `ix_workflow_document_sets_status` y FKs/constraints derivados. Downgrade espejo.
Se squashea con el resto de la cadena antes del merge (mismo acuerdo que ADR 0002).

## 5. Gotchas operativos (dev)

1. **Payloads Temporal**: `DocumentProcessingInput.document_set_uuid` viaja serializado — runs vivos en
   dev con el shape viejo fallan al replay. **Drenar/terminar runs dev antes de desplegar** (gotcha
   conocido: no editar backend con flujos E2E vivos).
2. **Eventos almacenados** (`workflow_events` para replay FE): payloads viejos guardan claves con el
   naming anterior. Dev-only ⇒ se acepta reset/limpieza de eventos viejos; NO se escribe shim de compat.
3. Dashboards/grep de logs cambian de prefijo (`workflow_document_set.*` → `processing_job.*`).

## 6. Superficie y secuencia

~78 archivos src + 28 tests backend · ~21 archivos FE · 5 rutas JWT + BFF/axios del FE que las consume.

| Paso | Contenido | Gate |
|---|---|---|
| R0 | Migración + ORM + modelo/enums/repo dominio | migración up/down limpia |
| R1 | Aplicación (paquete, dispatcher, re_extractor, sweeper, runner) + presenters/rutas + módulos SSE | suite backend verde + **golden byte-idéntico** |
| R2 | FE (query keys, componentes, i18n es/en, rutas BFF). **Incluye retirar la rama inerte `WorkflowDocumentsTable`** de document-sets (`isStandard=true` fijo — pendiente cosmético heredado de E7 F2; este es su momento natural) | tsc OK + lista/replay/re-extract en vivo |
| R3 | Limpieza de tests (28) + smoke E2E upload→COMPLETED | suite completa verde |

## 7. Fuera de alcance

Cualquier cambio de columnas más allá del rename (no se añade ni borra nada) · compat de payloads
viejos (dev-only) · squash de la cadena de migraciones (pendiente global pre-merge, heredado de
ADR 0002/0003). El nesting bajo caso y el retiro de `workflow_type` **ya los hizo E7** — no son parte
de esto.

## 8. Relación

Cierra el rename anunciado en `product/plans/re-architecture/unified-workflow.md` §3 (E7, ya implementado — ADR 0003).
Decisión de naming discutida 2026-06-11/12: `processing_job` gana por coherencia interna↔externa
(M2M ya dice `job_id`/`/v1/jobs`) y porque `attempts`/`trigger` describen un *job*, no un *run*;
segunda opción era `ingestion_job`. OJO: los slugs de `recipes.py` NO se tocan — E7 F2 los repurposó
como claves del registry `pipeline_template_for_slug` (siguen vivos como identificadores de plantilla).

## 9. Implementación (2026-06-12)

**Decisiones resueltas con Vic durante la implementación** (el mapa §2 no las anticipó):

1. **Se mantiene el prefijo `workflow_`** (no se dropea): tabla `workflow_processing_jobs`, clase
   `WorkflowProcessingJob(ORM)`, `WorkflowProcessingJobRepository`. Esto además elimina el conflicto
   tabla-vs-módulo de endpoint (ambos quedan `workflow_processing_jobs`). Los nombres SIN prefijo
   hoy (`DocumentSetEvent*`, enums) quedan `ProcessingJob*`.
2. **`workflow_events` tenía DOS columnas en conflicto**: el FK `document_set_id` y su propia
   `processing_job_id` (clave de idempotencia del `uq_workflow_events_doc_type_job` — a veces el
   Temporal run_id, a veces un sintético `case:<id>:task:<id>`). Resolución:
   `document_set_id → processing_job_id` (FK, uniforme con `workflow_documents`) **y** la clave de
   idempotencia `processing_job_id → idempotency_key` (nombre honesto; ya es convención en el módulo
   `source_delivery`).
3. **Activities renombradas + golden re-grabado**: los 3 strings de activity (`update_workflow_*`,
   `publish_*`, `dispatch_*`) cambian; `activity_sequence.json` se re-grabó a mano cambiando SOLO
   esos strings **y** los valores de event-type `document_set.* → processing_job.*` que el
   fingerprint de `publish_*` embebe. `final_state.json` y `canned_results.json` quedan
   **byte-idénticos** (gate §3 honrado: investigado, no re-grabado a ciegas).

**Residuales deliberados (NO bugs):** (a) migraciones históricas en `versions/` conservan nombres
viejos (se squashean pre-merge, acuerdo ADR 0002); (b) presenter M2M `m2m_job.py` conserva las claves
de wire `job_id` y `document_set_id` (contrato público §3 CERO cambio); (c) **el payload de webhook
cambió la clave top-level `document_set → processing_job`** (camelCase `processingJob`) — dev-only,
sin shim; (d) `backend/fixtures/admin/*.sql` (metadata Directus) conserva nombres viejos por
replayabilidad — **regenerar si se usa el admin contra el schema renombrado**.

**Gates verdes:** migración up/down limpia (`a7b8c9d0e1f2 → b8c9d0e1f2a3`, dev DB restaurada a
original); backend suite de la superficie del rename **1405 verde** (fallos restantes = `tests/api/*`
E2E live-server + `integration/llm` — pre-existentes, no tocan ningún token del rename); golden
verificado; FE `tsc` 0 + vitest (fallos restantes en `run-summary/` — pre-existentes, i18n test
harness). Verificación adversarial (3 agentes) = PASS, 0 missed.

**Pendiente operativo (deploy dev):** drenar/terminar runs Temporal vivos → `just migrate-backend`
(upgrade head) → rebuild + `up -d` de `api` y `temporal-worker` (no `restart`: no relee env). Los
payloads Temporal/eventos viejos con el shape anterior fallan al replay (dev-only, aceptado §5).
Squash de la cadena de migraciones sigue pendiente (global pre-merge).
