---
feature: cases-table-upload
type: plan
status: implemented
coverage: 100
audited: 2026-06-16
reviewed: 2026-06-17
decisions_closed: 2026-06-17
implemented: 2026-06-17
moved_from: .recon/
backlog: false
---

# Cases table: create + upload + expandable rows — behavior design

Status: **decisions locked — ready to implement** (revisión adversarial 2026-06-17: D1–D6 cerradas,
B1 re-escopado a CREATE+UPDATE, ítems obsoletos corregidos — ver `PLAN-REVIEW.md`) · Route: `/workflows/[wf_slug]/cases`

## Implementación (2026-06-17)

Todo el plan (B1, F1–F7, D1–D6) implementado **+ F8 (barra de progreso del
pipeline en la fila)** y **verificación gráfica COMPLETA** (Playwright).

**F8 — barra de progreso del pipeline (pedido extra de Vic):** la fila muestra
el progreso del pipeline mientras hay un run en vuelo, como la vieja tabla de
WorkflowDocuments. Reusa `ProcessingJobStatusBadge` (`shared/`) alimentado por
`SetView.progressPct/currentStep/status` de `useProcessingJobEvents`, mapeado por
`workflowCaseId` (`liveSetByCase`); in-flight ⇒ barra, si no ⇒ badge de estado.

**Verificación gráfica (Playwright, tenant LlamitAI Dev):** subí
`fixtures/data/recibo_cfe.pdf` → caso auto-nombrado → **barra "Clasificando… 20%"**
en vivo → "Completado" + 1 doc → chevron (≥1 doc) → sub-fila «Cédula de Identidad /
Extraído / p. 1–1». Badge "Procesamiento fallido" en runs FAILED. CTA per_upload,
SSE, delete/bulk-delete y gating del nombre en detalle: OK. (Gotcha: un PNG 1×1
falla OCR al instante; usar PDF real para ver la barra. El worker Temporal estaba
crash-looping con código viejo → `docker restart`.)

**Backend (B1):** `name_editability.py` nuevo (`CaseNameNotEditableError` 422 +
`case_name_is_editable` vía `recipe_has_await_documents`). Guard en
`WorkflowCaseCreator` (B1a) y `WorkflowCaseUpdater` (B1b, rechaza solo si el
name cambia); M2M exento (D3). Endpoint re-cableado (`pipeline_repository` +
`workflow_repository`). Tests: `test_name_editability.py` (6, ambas ramas CREATE
+ UPDATE + no-op) verdes; 103 tests de cases/router sin regresión.

**Frontend (F1–F7):** `Case.documents` mapeado en `mapCase`/`mapCaseDetail` (F1);
`caseNameEditable(wf)` (F2); filas expandibles con sub-rows de documentos, chevron
solo con ≥1 doc (F3/D2); toolbar capability-adaptive — per_upload «Subir
documentos», dossier «Nuevo {caso}» + «Añadir documentos» por fila con
`workflowCaseId` (F4/D5); gating del nombre en el detalle (texto plano en
per_upload) (F5); SSE en la lista con refetch en evento terminal (F6); i18n es/en
(F7). `FileUploadButton` ganó variante `compact`. **tsc limpio** en todo el
changeset (el único error de tsc es pre-existente en `mapped-extraction-list.tsx`,
del reorg concurrente). N1: sin cambio de nav (D1).

## 0. Locked decisions

### Ronda 1 (Vic, 2026-06-16)

1. **Naming** → *derive from capabilities*. `caseNameEditable = capabilities.includes("multi_doc_dossier")`
   (`MULTI_DOC_DOSSIER` se deriva de la fase `await_documents` — **no** hay una capability
   `await_documents` aparte; ver §4.2 para por qué esta capability es *exactamente* la señal
   de un expediente nombrable por el usuario). Else name = file name (read-only).
2. **Upload/CTA** → *capability-adaptive*: per_upload ⇒ primary "Subir documentos" (file→case);
   multi-doc ⇒ primary "Nuevo {caso}" + per-row "Añadir documentos".
3. ~~**processing-jobs page** → keep as demoted technical view~~ → **OBSOLETO** (ver D1): la página
   ya es código muerto (fuera del nav, root redirige a cases, vista huérfana). cases **ya** es el
   default único; no hay nada que "mantener/demote".

### Ronda 2 (Vic, 2026-06-17) — cierre tras revisión adversarial

> Revisión completa en `PLAN-REVIEW.md`. Estas 6 decisiones cierran las contradicciones y huecos
> que la revisión encontró; el resto de la §7 ya está corregido en línea.

- **D1 — Vista técnica:** *descartar el objetivo*. No se recrea processing-jobs; el debugging a
  nivel-run vive en la pestaña «Actividad» por caso. ⇒ **N1 = sin cambio de nav** (§7 N1, §5, §6.3).
- **D2 — Gate de expand:** *solo casos con ≥ 1 doc* muestran chevron. Un caso 0-doc **no** expande
  ⇒ se **elimina** el empty-state «Sin documentos» de §4.3 (inalcanzable). (§4.3, §7 F3).
- **D3 — Guard de naming:** guardar **JWT CREATE + UPDATE**; **eximir M2M** (carve-out documentado:
  los clientes máquina gestionan su propio naming). En no-dossier ⇒ `DomainError case.name_not_editable`
  (422). El UPDATE rechaza **solo cuando el `name` cambia** (`name != case.name`), para no romper un
  echo no-op de nombre en un PUT de status. (§7 B1).
- **D4 — Carga masiva N→N en dossier:** *mantener excluida*. El usuario crea + nombra cada dossier y
  añade docs por fila. El backend lo soporta (omitir `workflowCaseId`) si luego hace falta. (§4.1).
- **D5 — Invariante de carga en dossier:** en un workflow dossier la toolbar/carga **siempre** adjunta
  un `workflowCaseId`; **nunca** se renderiza un `FileUploadButton` sin caso. El guard de D3 permite
  renombrar las raras filas auto-nombradas (`file · 4hex`) que entren por otra vía (ingesta/email);
  `splitCaseName` ya las renderiza limpio. (§7 F4).
- **D6 — Ciclo de dossier vacío:** test explícito — un dossier recién creado (0 docs) renderiza, **no**
  expande (D2), **no** puede marcarse ready/finalizar, y `EvaluateCaseCompleteness` devuelve
  «incompleto» (no error). (§7 Verify).

### Grounded facts (verified in code)
- `Capability.MULTI_DOC_DOSSIER = "multi_doc_dossier"` (`capabilities.py:50`, era `:49`), derivada
  cuando el pipeline tiene una fase `await_documents` (mapeo `AWAIT_DOCUMENTS → MULTI_DOC_DOSSIER` en
  `derive_capabilities`, `capabilities.py:92-93`, era `:87-88`; `def` en `:61`, era `:60`); FE
  `WorkflowCapability` ya la lista + `hasCapability()` → **`caseNameEditable` computable
  client-side, sin cambio en el read-path backend.** *(Cites corridos ~5 líneas por edits concurrentes
  de activation-policy/extraction-gate; símbolos/valores intactos — preferir el símbolo a la línea.)*
- **El endpoint de LISTA ya serializa el array completo `documents`** con el **mismo presenter** que el
  alta (`WorkflowCasePresenter` → `WorkflowDocumentPresenter`, batch-load `list_by_case_ids`, sin N+1)
  → **F1/F3 confirmados como FE-puro**: sin endpoint nuevo ni fetch lazy. ⚠️ El per-doc de la lista trae
  `documentTypeId` **pero no** un objeto `documentType` (a diferencia de `documentGroups` del detalle) →
  el label de tipo en filas hijas necesita un lookup client-side contra los doctypes ya cargados.
- `WorkflowCaseUpdater` asigna `case.name = name` **siempre que se envía un `name`, sin check de
  editabilidad** (`application/workflow_cases/updater.py:44-45`) → necesita un write-guard.
- List presenter ya serializa el array completo `documents` (`WorkflowCasePresenter.to_dict` →
  `WorkflowDocumentPresenter`); **no emite un campo `documentsCount`** (el conteo se deriva de
  `documents.length`) → **expandable rows need no new endpoint and no lazy fetch**; el FE
  `mapCase` hoy descarta el array.

---


## 1. Goal (from Vic)

After unifying to a single workflow type, the **cases table** should let the user:

1. **Create cases** *and* **upload documents** from the same table (the experience the
   old documents table / now `processing-jobs-view` has).
2. **Name the case**: if the pipeline "has `case.name` activated" → name is editable;
   otherwise the case name defaults to the **file name**. *("has `case.name` activated" es
   interpretado/derivado — ver §4.2; **no existe** un campo literal `case.name` en el pipeline,
   ver §2.C. La señal real es la capability `multi_doc_dossier`.)*
3. **Expand each row** to reveal the list of its `WorkflowDocuments`.

## 2. What already exists (verified, not assumed)

The unification (ADR 0002/0003, E7) already did most of the heavy lifting:

| Piece | Status | Location |
|---|---|---|
| Cases list page + view | ✅ real, on `HttpCaseRepository` (not mock) | `cases-view.tsx`, `hooks/queries/cases.ts` |
| Create case (name only) | ✅ wired end-to-end | `CreateCaseDialog` → `useCreateCaseMutation` → `POST /v1/workflows/{id}/cases` (handler `presentation/endpoints/workflow_case.py:78`, registrado en `router.py:389`, `WorkflowCaseCreator`) |
| List endpoint **embeds documents** | ✅ already returns them (array `documents` completo; **no** emite `documentsCount`) | `WorkflowCaseLister` batch-loads `list_by_case_ids`; `WorkflowCasePresenter(documents=…)` |
| Upload component w/ case target | ✅ `workflowCaseId?` + `onDispatched` | `shared/file-upload-button.tsx` |
| Upload → process pipeline | ✅ 2-step: `POST /v1/documents/upload` → `POST /v1/workflows/{id}/jobs {fileId, workflowCaseId?}` | `WorkflowProcessingJobDispatcher` |
| Per-upload case auto-name | ✅ `"{file_name} · {4hex}"` via `_ensure_case` | `dispatcher.py` |
| `splitCaseName()` renders `file · ref` as title + mono ref | ✅ | `cases-view.tsx` |
| Live SSE progress | ✅ reused on detail view | `useProcessingJobEvents` (`/api/v1/workflows/{id}/jobs/events`) |
| Expandable parent→children rows pattern | ✅ fully built | `processing-jobs-table` (chevron + `expanded` state + inline child rows) |
| Capabilities derived from pipeline | ✅ presenter expone lista ordenada; `hasCapability()` helper | `derive_capabilities()` → `set[Capability]` (`capabilities.py:60`), `entities/workflow.ts` |
| Inline name edit | ✅ on detail view | `workflow-case-detail-view.tsx` (`nameInputRef`) |
| Per-workflow case noun | ✅ | `caseNoun()` helper |

**What is genuinely MISSING:**

- **A.** Mapping the already-returned `documents` onto the list `Case` entity (FE `mapCase`
  drops them) + an **expand toggle** in `CaseRow` (the pattern exists in processing-jobs).
- **B.** An **upload affordance on the cases list** (toolbar + per-row), reusing
  `FileUploadButton`. Plus SSE on the list so uploads animate live.
- **C.** **Pipeline-driven `case.name` editability** — *does not exist at all today*. There is
  no `case.name` capability, no naming policy field, y **tres** caminos de escritura aceptan un
  `name` sin check: `WorkflowCaseUpdater` (UPDATE), `WorkflowCaseCreator` (alta JWT) y
  `FindOrCreateCaseM2M` (alta M2M). The user's premise needs a real contract en CREATE + UPDATE
  (§4, §7 B1a/B1b/B1c).

## 3. Two workflow archetypes (the design hinges on this)

Because capabilities are derived from the pipeline, a workflow is effectively one of two
shapes for this table:

- **Document-centric (straight-through / `per_upload`)** — recipe has only document-scope
  phases; `finalize_closes_case` closes the case at FINALIZE. Here **the case ≈ the file**.
  One upload → one case, auto-named from the file. Creating an *empty* case is meaningless
  (a case with no document does nothing).
- **Case-centric (`multi_doc_dossier`, derivada de la fase `await_documents`)** — the case
  is a **dossier** the user *creates and names up front*, then *adds* documents to over time
  and corre análisis a nivel-caso.
  ⚠️ **Ojo:** correr fases a nivel-caso (ANALYZE/ENRICH/ASSESS) **no** implica case-centric
  *para naming* — un workflow `per_upload` también puede tener esas fases con el caso
  auto-creado del archivo (`_ensure_case`, auto-nombrado `file · 4hex`). La señal de "caso
  nombrable por el usuario" es **solo** `await_documents` (= `MULTI_DOC_DOSSIER`): la fase que
  hace que el caso exista y espere documentos. Por eso F2 gatea exactamente sobre esa capability.

## 4. Recommended behavior

### 4.1 Toolbar / primary CTA — capability-adaptive

- **Document-centric:** primary CTA = **"Subir documentos"** (multi-file). Each file →
  one case (dispatcher mints the `per_upload` case, auto-named from the file). This *is* the
  old documents-table experience, now expressed as cases. A secondary "Crear {caseNoun} vacío"
  is hidden (or demoted) because it has no use here.
- **Case-centric:** primary CTA = **"Nuevo {caseNoun}"** → dialog with an editable **name** (el
  nombre **sigue siendo requerido**; `CreateCaseDialog` no tiene file-input). Cada fila existente
  recibe una acción **"Añadir documentos"** (sube con el `workflowCaseId` de esa fila).
  *(D4: **no** hay carga masiva "N archivos → N cases" en dossier; el backend lo soporta si luego
  hace falta. Se descarta el "drop files al crear" del diseño previo — se añaden docs por fila.)*

A single multi-file `FileUploadButton` covers both; only the `workflowCaseId` differs
(absent = new case per file; present = into that row).

### 4.2 Case name — driven by capability (locked) — see §0 #1

`caseNameEditable` se computa **client-side** desde `workflow.capabilities`
(**sin cambio en el read-path del backend** — ver §0 grounded facts y F2):

```
caseNameEditable(wf) = hasCapability(wf, "multi_doc_dossier")
```

- **editable** cuando el workflow tiene `multi_doc_dossier` (i.e. su pipeline tiene una fase
  `await_documents`) → el name es un campo real en el create dialog e inline-renamable en la
  fila/detalle.
- **auto / read-only (= file name)** en cualquier otro caso (document-centric) → el name es el
  nombre del archivo (`splitCaseName` ya lo renderiza limpio); el input se oculta/deshabilita y
  el rename lo rechaza `WorkflowCaseUpdater` (guard B1).

**Por qué exactamente `multi_doc_dossier` (no un "case-centric" más amplio):** de las
capabilities derivadas (`derive_capabilities`, `capabilities.py:60-100`), `AWAIT_DOCUMENTS` es
la **única** fase que significa "el caso existe y espera a que el usuario agregue documentos" →
el único shape donde el usuario *crea y nombra* el expediente antes de que existan documentos.
Las demás capabilities a nivel-caso (`ANALYSIS`/`ENRICHMENT`/`LAYER2_CONFIDENCE`/`FAN_OUT`)
coexisten en workflows `per_upload` donde el caso = el archivo (auto-nombrado), y ahí nombrar no
es una acción del usuario. Gatear sobre `multi_doc_dossier` también alinea con la affordance
"Crear {caseNoun} vacío" de §4.1 (crear un caso vacío solo tiene sentido si el pipeline espera
documentos). Cumple la regla de Vic ("si el pipeline tiene `case.name` → editable, else file
name") **sin añadir un knob nuevo al editor de pipelines**. Opciones consideradas (toggle
explícito / template con tokens) en §6 — descartadas.

### 4.3 Expandable rows

- Add a leading **chevron** column **solo en casos con ≥ 1 doc** (**D2**). Un caso 0-doc no expande
  (no hay empty-state «Sin documentos» — un dossier vacío recién creado simplemente no tiene chevron).
- **Data is already in the list payload** — map `BackendCase.documents` through `mapCase`
  onto the `Case` entity (hoy `mapCase` descarta el array; solo sobrevive un conteo). No new
  endpoint, no extra fetch (confirmado: mismo presenter que el detalle, ver §0 grounded facts).
  El conteo junto al chevron = `documents.length`; **`documentsCount` es un campo FE-derivado**
  (`documents.length`) — el **backend** no lo emite (no confundir: el FE sí lo expone).
- Cada fila hija muestra: nombre de archivo, **tipo de doc** (lookup client-side por `documentTypeId`
  — el per-doc de la lista **no** trae el objeto `documentType`), badge de status (`doc-status-config`
  — confirmar que los strings del enum casan con sus keys), page range / índice (splits BULK), y link
  al detalle del doc. **Renderizar todas las clases `CaseDocumentSource`** que devuelva el payload
  (`EXTERNAL_DATA`/`TOOL`/`SPLIT_CHILD` incluidos) — "if relevant" no era implementable; se opta por
  mostrar lo que ya viaja, que es lo coherente con "data already there".

### 4.4 Live progress

Subscribe `cases-view` to `useProcessingJobEvents` (as detail/processing-jobs do):
optimistic PENDING case/doc rows on upload → animate status → react-query refetch on
terminal (`COMPLETED/PARTIAL/FAILED`). Gives the "upload and watch it process" feel.

## 5. El `processing-jobs` page — ya es código muerto (D1)

⚠️ **Actualizado 2026-06-17:** la premisa original ("mantener como vista técnica demoted") está
**obsoleta**. Un refactor Re-IA concurrente ya **retiró processing-jobs por completo**: no está en el
nav (`shared/workflow-sidebar.tsx`), el root del workflow redirige a cases (`[wfSlug]/page.tsx:15`),
`/documents/page.tsx` es un redirect-stub y `WorkflowProcessingJobsView` es **huérfano (0 consumidores)**.

cases **ya** es el default único — no hay nada que "demote". **D1: descartar el objetivo** de la vista
técnica; el debugging a nivel-run vive en la pestaña «Actividad» por caso. El patrón de filas
parent→children a portar para F3 vive **dentro de cases** (`cases/bottom-panes/rows/workflow-processing-job.tsx`
+ `cards/document.tsx`), **no** en la vista huérfana.

## 6. Opciones consideradas (resueltas — ver §0)

> Estas eran las preguntas abiertas; **ya están decididas en §0**. Se conservan como registro
> de las alternativas y por qué se descartaron. **No son opciones vivas.**

1. **Naming mechanism** → **(A) derivar editabilidad de capabilities — ELEGIDA** (§0 #1).
   Descartadas: (B) toggle/fase `case.name` explícito en el editor de pipelines (Capability
   real + macro `apply_capability` + UI) — sobra, porque `multi_doc_dossier` ya es la señal;
   (C) *template* de nombre con tokens `@slug.path` auto-rellenados desde un campo extraído
   (la más pesada — back-fill async tras EXTRACT_FIELDS) — fuera de alcance.
2. **Upload / CTA model** → **(A) CTA primario capability-adaptive — ELEGIDA** (§0 #2).
   Descartada: (B) mostrar siempre Upload + Crear-vacío + add por fila.
3. **processing-jobs page fate** → ~~mantener como vista técnica demoted~~ → **D1: descartar el
   objetivo** (la página ya es código muerto; ver §5 y §0 ronda 2). Sin cambio de nav.

## 7. Implementation plan (decisions locked)

Ordered, smallest-blast-radius first. Most is FE; backend is one guard.

### Backend — name-editability boundary (guard CREATE + UPDATE)

> **Corrección 2026-06-17:** el diseño previo llamaba a esto "un rename guard" en el updater. Es
> **insuficiente**: la editabilidad del nombre tiene **tres** caminos de escritura, **dos de ellos de
> alta**. Ocultar el campo `name` en el FE (F5) es necesario pero **no** protege la API — un cliente
> puede POSTear un case con nombre en un workflow per_upload. Por eso B1 pasa de window-dressing a un
> límite real de backend. **Helper a usar:** `recipe_has_await_documents(version)`
> (`recipe_resolver.py:46`, ya en el paquete `cases`, ya importado por `ready.py`/`case_run_starter.py`/
> `m2m.py`) — semánticamente idéntico a `MULTI_DOC_DOSSIER in derive_capabilities(version)` pero más
> ligero y sin cruzar de capa. **No** importar `derive_capabilities` en la capa de aplicación de cases.

- **B1a — guard del alta JWT (D3).** `WorkflowCaseCreator` (`creator.py`) acepta hoy un `name` requerido
  sin check (ya inyecta `workflow_repository`). Inyectar `pipeline_repository`, resolver la receta y, si
  **no** `recipe_has_await_documents(version)`, rechazar con el nuevo `DomainError case.name_not_editable`
  (422). *(En per_upload el nombre lo pone `_ensure_case` desde el archivo; el alta con nombre explícito
  no aplica.)*
- **B1b — guard del rename UPDATE.** `WorkflowCaseUpdater` (`updater.py:44-45`) hace hoy
  `if self.name is not None: case.name = self.name` sin check, e inyecta **solo** `case_repository` +
  `document_repository`. Inyectar `pipeline_repository` + `workflow_repository`; resolver la receta
  **desde el caso** (no la versión vigente del workflow — pueden divergir para un caso pre-sellado) con
  `resolve_case_recipe(case, tenant_id, …)` **igual que `ready.py` / `completeness.py`**; gatear con
  `recipe_has_await_documents(version)`. **Rechazar solo cuando el `name` realmente cambia**
  (`name != case.name`) para no romper un echo no-op del nombre en un PUT de status.
- **B1c — M2M exento (carve-out · D3).** `FindOrCreateCaseM2M` (`m2m.py:100,127`) **no** se guarda: los
  clientes máquina gestionan su propio naming. **Documentar el carve-out** para que no sea un hueco
  silencioso.
- **Patrón / ubicación (corrección):** los use cases hermanos que inyectan repos **no** están en
  `updater.py`; viven en `ready.py` / `case_run_starter.py` / `completeness.py` — copiar de ahí. El
  `DomainError` nuevo va **inline** siguiendo la convención `case.*` (`case.not_complete`, `case.locked`,
  …), **no** en `processing.py`.
- **Call-site rewire:** pasar `pipeline_repository` + `workflow_repository` desde `app_context.domain`
  en el endpoint `update_case` (`workflow_case.py:155`) **y** en el de alta.
- **Tests:** ambas ramas para CREATE y UPDATE (dossier permite; per_upload rechaza 422) + el no-op
  (mismo nombre no rechaza).
- *(Sin cambio en el read-path: `caseNameEditable` se computa en FE desde `workflow.capabilities`.)*

### Frontend — data (2 small)
- **F1 — map documents onto list `Case`.** `entities/case.ts`: añadir `documents: CaseDocument[]`
  a `Case` (hoy `Case` solo tiene `documentsCount`). En `http-case.ts` `mapCase`: mapear
  `raw.documents` con `(raw.documents ?? []).map(mapCaseDocument)`. Reutiliza
  `BackendCaseDocument`/`mapCaseDocument`, que **ya existen** (`http-case.ts:34-50`, `:114-132`).
  Derivar el conteo de `documents.length` (`countDocuments` ya hace ese fallback) — el backend
  no emite `documentsCount`.
  ⚠️ `CaseDetail` **no** tiene un `documents` plano: expone `documentGroups: CaseDocumentGroup[]`
  (el array plano vive *dentro* de cada `CaseDocumentGroup`), así que no copies esa forma — el
  `documents` de `Case` es un campo nuevo.
- **F2 — `caseNameEditable` helper.** selector pequeño:
  `caseNameEditable(wf) = hasCapability(wf,"multi_doc_dossier")` (ver §4.2 para por qué
  exactamente esa capability).
  ⚠️ **Gatear sobre un workflow CARGADO.** `capabilities?` es opcional y `hasCapability` cae a
  `false`; si `useWorkflowQuery` está loading/errored (`workflow === undefined`) el helper degrada
  silenciosamente a read-only y un usuario dossier pierde la capacidad de nombrar. Mismo camino por
  el gotcha de slug→422 (API por UUID). Mientras carga/error, **deshabilitar el CTA de crear** o
  mostrar loading — **no** tratar el workflow como per_upload por defecto.

### Frontend — UI (cases-view.tsx + pieces)
- **F3 — expandable rows.** Columna chevron **solo cuando `documents.length ≥ 1`** (**D2**) + estado
  `expanded` por fila; al expandir, render `caseItem.documents` como sub-rows. **Portar el markup de
  `cases/bottom-panes/rows/workflow-processing-job.tsx`** (vive dentro de cases) **+ `cards/document.tsx`**
  — **no** de `WorkflowProcessingJobsView` (huérfano). Mostrar nombre de archivo, tipo de doc (lookup por
  `documentTypeId`), status (`doc-status-config`), page-range/índice, link al detalle. **Sin empty-state**:
  un caso 0-doc no tiene chevron. Bloqueado por F1 (sin `documents[]` no hay nada que expandir).
- **F4 — capability-adaptive toolbar.**
  - per_upload (sin `multi_doc_dossier`): primary = `FileUploadButton` (sin `workflowCaseId`) "Subir documentos";
    demote/hide "Nuevo {caseNoun}".
  - case-centric: primary = "Nuevo {caseNoun}" (`CreateCaseDialog`, name editable) + por fila "Añadir documentos"
    (`FileUploadButton` atado al `workflowCaseId` de esa fila, en el menú de acciones de la fila).
  - `{caseNoun}` = salida de `caseNoun(workflow, locale, count)` (string i18n, no literal; firma 3-arg verificada).
  - ⚠️ **Invariante D5:** en un workflow dossier la carga **siempre** lleva `workflowCaseId` (toolbar y
    por-fila) — **nunca** se renderiza un `FileUploadButton` sin caso aquí. El path "subir sin caso →
    `_ensure_case` auto-nombra" es exclusivo de per_upload.
- **F5 — name gating.** `CreateCaseDialog`: renderizar el campo `name` **solo** cuando `caseNameEditable`
  (case-centric); pasar el flag por props (hoy el dialog siempre lo pinta, `create-case-dialog.tsx:67-80`).
  Rename inline en filas/detalle gateado por el mismo flag; mapear el backend `case.name_not_editable` a un
  toast. F5 es **defensa FE** del invariante; el guard real es backend (B1). El rename solo dispara cuando
  el nombre cambia (alineado con B1b).
- **F6 — live SSE on the list.** Subscribe `cases-view` to `useProcessingJobEvents`; merge optimistic PENDING
  rows on upload, animate status, react-query refetch on terminal (mirror `processing-jobs-view`). Highest-effort FE piece.
- **F7 — i18n.** "Subir documentos", "Añadir documentos", empty-states, rename-not-allowed toast.

### Nav
- **N1 — sin cambio de nav (D1).** ~~demote processing-jobs~~ → **obsoleto**: processing-jobs ya **no
  es ruta navegable** (fuera de `shared/workflow-sidebar.tsx`, root redirige a cases, vista huérfana —
  ver §5). cases ya es el default único. No hay nada que mover/demote ni que añadir. Si en el futuro se
  quisiera una vista técnica cross-case de runs, sería **trabajo net-new** (ruta + wiring), fuera de
  alcance por D1.

### Verify
- Backend: unit tests para B1a (CREATE) y B1b (UPDATE), ambas ramas (dossier permite / per_upload 422)
  + el no-op (mismo nombre no rechaza). FE: `tsc` 0; lint.
- **D6 — ciclo de dossier vacío:** test explícito de que un dossier recién creado (0 docs) renderiza,
  **no** expande (D2), **no** puede marcarse ready/finalizar, y `EvaluateCaseCompleteness` devuelve
  «incompleto» (no error) — verificar contra `completeness.py`, no descubrir en prod.
- Graphical: Playwright on tenant **LlamitAI Dev** for a per_upload workflow (upload→case→expand) and a
  multi_doc_dossier workflow (create named case→add docs→expand). Gotcha: workflow API is by **UUID**, not slug.
- Memory gotcha: **do not edit backend while live E2E flows are running.**

### Notes / non-goals
- `_ensure_case` per-upload auto-name (`file · 4hex`) is unchanged; `splitCaseName` already renders it.
- No new list/expand endpoint. No pipeline-editor change (naming is derived, not a toggle).
- Ubicación del doc: **ya correcta** en `product/plans/cases-table-upload/`. (La nota previa de
  mover a `docs/plans/` era errónea — `docs/` es el sitio Astro de live-docs; los planes viven en
  `product/plans/<feature>/` per CLAUDE.md.)
