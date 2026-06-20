---
feature: cases-table-upload
type: verification
verified: 2026-06-17
status: pending
overall: pending
---

# cases-table-upload — verificación de estado

## Veredicto

**Solo la base "ya existe" (§2) está implementada; las 8 piezas nuevas del plan (B1, F1–F7, N1) están sin hacer.**
El frontmatter del plan (`status: pending`, `coverage: 0`) es correcto. La premisa central
(`await_documents ⇒ MULTI_DOC_DOSSIER ⇒ naming case-centric`) **sigue intacta** tras los edits
concurrentes de activation-policy/extraction-gate. Dos ítems del plan están **desactualizados por
refactors concurrentes**: N1 (processing-jobs ya salió de la navegación) y la ubicación de los use
cases hermanos en B1.

## Estado por ítem

| Ítem | Estado | Evidencia (file:line) | Gap |
|---|---|---|---|
| **Base §2** ("ya existe": auto-naming, jobs endpoint, 2-step upload, derive_capabilities, hasCapability, FileUploadButton, BackendCaseDocument/mapCaseDocument) | ✅ implementado | `dispatcher.py:210-238` (`_ensure_case` `"{file} · {4hex}"`); `schemas/workflow_processing_job.py:8-12` + `workflow_processing_jobs.py:70-94` (`workflowCaseId?`); `capabilities.py:50,61,92-93`; `workflow.ts:9,53-58`; `http-case.ts:34-50,114-132` | — (confirmado) |
| **B1** rename guard en `WorkflowCaseUpdater` | ❌ ausente | hoy `if self.name is not None: case.name = self.name` sin check (`updater.py:44-45`); sin repos inyectados (`updater.py:22-33`); error `case.name_not_editable` no existe (codegraph + grep, 0 hits); `derive_capabilities` no importado en la capa cases | Inyectar `pipeline_repository` + `workflow_repository`; resolver versión, gate `MULTI_DOC_DOSSIER in derive_capabilities(version)`; nuevo `DomainError` (422) inline; rewire call sites + tests |
| **F1** mapear `documents[]` en list `Case` | ❌ ausente | `Case` solo tiene `documentsCount` (`case.ts:68`); `mapCase` devuelve `documentsCount: countDocuments(raw)` y descarta el array (`http-case.ts:97-112`) | Añadir `documents: CaseDocument[]` a `Case`; mapear `(raw.documents ?? []).map(mapCaseDocument)`; derivar conteo de `.length` |
| **F2** helper `caseNameEditable(wf)` | ❌ ausente | grep `caseNameEditable`/`nameEditable` → 0 hits; `hasCapability` existe pero sin usar para naming (`workflow.ts:53-58`) | Crear selector `caseNameEditable(wf) = hasCapability(wf,"multi_doc_dossier")` |
| **F3** filas expandibles (chevron + sub-rows) | ❌ ausente | header sin columna chevron (`cases-view.tsx:333-358`); `CaseRow` solo pinta el conteo, sin estado expand (`cases-view.tsx:458-575`, doc count `:534-538`). Bloqueado por F1 (sin `documents[]`) | Columna chevron + `expanded` state; render `caseItem.documents` como sub-rows; "Sin documentos" vacío. Patrón a portar: `cases/bottom-panes/rows/workflow-processing-job.tsx:139,233-248` + `cards/document.tsx` |
| **F4** toolbar capability-adaptive | ❌ ausente | toolbar = único `Button "newCase"` sin branch (`cases-view.tsx:224-233`); `FileUploadButton` no importado en cases-view (solo processing-jobs/case-detail) | Branch en `caseNameEditable`: per_upload ⇒ `FileUploadButton` "Subir documentos"; case-centric ⇒ "Nuevo {caseNoun}" + por fila "Añadir documentos" (`FileUploadButton` atado a `row.uuid`) |
| **F5** name gating + inline rename + toast | ❌ ausente | `CreateCaseDialog` siempre pinta el campo name (`create-case-dialog.tsx:67-80`), props sin `caseNameEditable` (`:20-24`); sin rename inline; 0 refs a `name_not_editable` en FE | Pasar flag al dialog (condicionar campo name); rename inline gateado; mapear `case.name_not_editable` → toast |
| **F6** SSE en la list | ❌ ausente | `cases-view` no usa `useProcessingJobEvents` (solo `processing-jobs-view.tsx:275`, `workflow-case-detail-view.tsx:96`) | Suscribir `cases-view`; merge optimista PENDING; refetch en terminal (espejo de `processing-jobs-view.tsx:275`) |
| **F7** i18n | ❌ ausente | (depende de F4/F5; sin strings nuevos) | "Subir documentos", "Añadir documentos", empty-states, toast rename-not-allowed |
| **N1** demote processing-jobs en nav | ⚠️ obsoleto / no aplica | nav **ya excluye** processing-jobs por diseño (`shared/workflow-sidebar.tsx:114-247`); root redirige a cases (`[wfSlug]/page.tsx:15`); no hay ruta processing-jobs; `/documents/page.tsx` es stub redirect; `WorkflowProcessingJobsView` huérfano (0 consumidores) | Re-scope: **no hay nada que mover/demote**. Si se quiere una vista técnica, hay que RECREARLA (ruta + wiring) o eliminar el objetivo y apoyarse en la pestaña Actividad por caso |

## Drift / sorpresas

**Premisa `await_documents ⇒ multi_doc_dossier` — INTACTA.** Los edits concurrentes
(`capabilities.py`/`phase_configs.py`/`pipeline_interpreter.py`, activation-policy/extraction-gate)
**no rompieron** la premisa. `git diff HEAD~5 capabilities.py` muestra solo 2 cambios: un comentario
de clarificación (`:81-84`) y el swap del read source `version.activation_policy` →
`activation_dict_from_version(version)` (`:115`, que solo afecta HUMAN_REVIEW/QA, no
MULTI_DOC_DOSSIER). El mapeo `if PhaseKind.AWAIT_DOCUMENTS in kinds: add(MULTI_DOC_DOSSIER)` sigue
vivo (`capabilities.py:92-93`); `PhaseKind.AWAIT_DOCUMENTS` sin renombrar (`pipelines.py:54`); FE
`WorkflowCapability` aún lista `multi_doc_dossier` (`workflow.ts:9`).

Otras sorpresas:
- **Citas de línea del plan corridas ~5 líneas** por los comentarios añadidos: enum en `:50` (plan
  dice `:49`), mapeo en `:92-93` (plan `:87-88`), `def derive_capabilities` en `:61` (plan `:60`).
  Símbolos/valores exactos; solo drift de números. No bloqueante. Para B1: el guard
  `MULTI_DOC_DOSSIER in derive_capabilities(version)` ahora depende transitivamente de que
  `activation_dict_from_version` no lance.
- **B1 mal-ubica los use cases hermanos:** el plan implica que `RequestCaseReady`/
  `EnsureCaseRunStarted`/`EvaluateCaseCompleteness` viven en `updater.py`; en realidad están en
  `ready.py:67` / `case_run_starter.py:75` / `completeness.py:49`. El patrón de inyección de repos a
  copiar es real (`ready.py:73-76`, `completeness.py:55-56`), solo en otros archivos.
- **N1 obsoleto (refactor Re-IA 2026-06):** processing-jobs ya **no es ruta navegable**;
  `/documents/page.tsx` es redirect-stub y `WorkflowProcessingJobsView` es código muerto. El "patrón
  processing-jobs-table a portar" en realidad vive dentro de cases
  (`cases/bottom-panes/rows/workflow-processing-job.tsx`), no en la vista huérfana.
- **F1 es cambio puro de FE-mapping, no de contrato:** `BackendCase` ya declara `documents?:
  BackendCaseDocument[]` (`http-case.ts:68`) — el array puede viajar; solo el mapeo lo descarta
  (siempre que el list endpoint serialice `documents`).
- **Docstring stale:** `workflow_processing_jobs.py:5-6` aún dice "STANDARD omit / ANALYSIS provide
  workflowCaseId" — desactualizado vs el diseño universal-case; el comportamiento del código sí
  coincide con el plan.

## Qué falta implementar (orden, menor blast-radius primero)

1. **F1** — añadir `documents: CaseDocument[]` a `Case` + mapearlo en `mapCase` (FE, sin contrato). Desbloquea F3.
2. **F2** — helper `caseNameEditable(wf)` (FE, 1 selector). Desbloquea F4/F5.
3. **B1** — rename guard en `WorkflowCaseUpdater` (inyectar repos + `DomainError` 422 + tests; rewire call sites). Único cambio backend.
4. **F3** — filas expandibles (chevron + sub-rows) portando `workflow-processing-job.tsx` + `cards/document.tsx`.
5. **F4** — toolbar capability-adaptive (`FileUploadButton` per_upload vs "Nuevo {caseNoun}" + "Añadir documentos" por fila).
6. **F5** — name gating en `CreateCaseDialog` + rename inline + toast `case.name_not_editable`.
7. **F6** — SSE en la list (`useProcessingJobEvents`, optimismo PENDING, refetch terminal). Pieza FE de mayor esfuerzo.
8. **F7** — i18n de strings nuevos.
9. **N1** — **re-scope**: ningún cambio de nav requerido (ya excluido por diseño). Decidir si se recrea una vista técnica o se descarta el objetivo.
