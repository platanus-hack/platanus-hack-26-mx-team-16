---
feature: source-webhooks
type: spec
status: implemented
coverage: 90
audited: 2026-06-16
---

# Spec: Webhooks de salida (`webhooks`)

Estado: **diseño cerrado para STANDARD** (decisiones §5, 1–24; sin abiertas).
**Solo STANDARD**; los webhooks ANALYSIS quedan **fuera de alcance** (§9, spec aparte).
Backbone del diseño: un nuevo modelo persistido **`WorkflowEvent`** (§4.1).
UI del cliente (config + auditoría/replay) especificada en **§10**.
Correcciones de hecho aplicadas tras revisión vs. código: columna `error` inexistente
(§2.3/§2.6), `name` vs `file_name` (§2.3), endpoint `PUT` (no `PATCH`, §4.9),
`mimeType` quitado del payload (§4.3), gate dentro del activity (§4.0/§4.6).
Pendiente: detalle de implementación por archivo en §8.

---

## 1. Objetivo

Permitir que cada cliente reciba, en un endpoint HTTP propio (webhook), el
**resultado del procesamiento de sus documentos** sin hacer polling a la API,
incluyendo **tanto las ejecuciones exitosas como las que fallaron**.

El sistema tiene hoy dos tipos de workflow (`WorkflowType`):

- **STANDARD** → su objetivo final es producir `WorkflowDocument`s (extracción
  estructurada por documento). **Este spec se enfoca aquí.**
- **ANALYSIS** → produce `AnalysisResult`/`WorkflowAnalysisRunSummary` + output
  personalizado (`output_schema`). **Fuera de alcance de este spec** (§9; spec aparte).

**Idea central (refinada con el usuario):** lo que viaja al webhook NO es un dict
ad-hoc, sino un **modelo persistido `WorkflowEvent`** que representa un evento de
salida del workflow. Cada `WorkflowEvent` lleva:

- el **id del evento** (`eventId`, idempotencia),
- el **status del `WorkflowDocument`** (EXTRACTED | ERROR),
- los **datos relevantes del documento** (snapshot: extracción con confidence,
  `documentType {id,name}`, `plainText` OCR, validación, y `error` si falló).

Persistir el evento nos da, además del envío: **idempotencia**, **auditoría de
entrega**, **reenvío/replay**, y un único modelo que sirve para **éxitos y
fallos** (y reutilizable a futuro).

> **Alcance:** se construye **ahora** toda la infraestructura compartida
> (`WorkflowEvent`, config por workflow, firma HMAC, cliente HTTP, enums de evento,
> actividad Temporal de dispatch) **solo para STANDARD**. Los webhooks **ANALYSIS**
> quedan **fuera de alcance** y se diseñarán en un **spec aparte**, reutilizando esta
> misma infra (§9).

---

## 2. Contexto del codebase actual (qué EXISTE)

> Convención: respuestas de API en **camelCase** (presenters convierten de
> snake_case vía `convert_to_camel_case`). Backend Clean Architecture/DDD:
> `domain/ → application/ → infrastructure/ → presentation/`.

### 2.1 Tipo de workflow
`backend/src/common/domain/enums/workflows.py:4-6`

```python
class WorkflowType(BaseEnum):
    STANDARD = "STANDARD"
    ANALYSIS = "ANALYSIS"
```

Gating STANDARD/ANALYSIS en `WorkflowDocumentSetDispatcher._validate_workflow_and_case()`
(`backend/src/workflows/application/document_sets/dispatcher.py:152-165`).

### 2.2 Modelo Workflow (NO tiene config de webhook hoy)
Dominio: `backend/src/common/domain/models/processing/workflow.py:13-71`
ORM: `backend/src/common/database/models/workspace.py:11-163` (tabla `workflows`)

- Tiene `synthesis_enabled: bool` (default false) → **patrón de gate a imitar**.
- **NO existe** `webhook_url`, `webhook_enabled`, `webhook_secret`.

### 2.3 WorkflowDocument (fuente del snapshot del evento)
Dominio: `backend/src/common/domain/models/processing/workflow_document.py:1-61`
ORM: `backend/src/common/database/models/workflow_document.py:1-122` (tabla `workflow_documents`)

| Campo (ORM / tabla) | Tipo | Notas |
|---|---|---|
| `uuid` | UUID | mixin → `document.id` |
| `tenant_id` | UUID | tenancy (mixin) |
| `workflow_id` | UUID (**not null**) | ⚠️ antes decía `\| None`; en el ORM es no-nullable |
| `workflow_case_id` | UUID \| None | presente en ORM (lo usa ANALYSIS) |
| `document_id` | UUID \| None | id lógico del documento |
| `document_set_id` | UUID \| None | **clave para re-cargar los docs de un set** |
| `document_type_id` | UUID \| None | null = bucket "Otros" |
| `name` | `str` (String 255) | ⚠️ **la columna es `name`, NO `file_name`** |
| `status` | `WorkflowDocumentStatus` | `EMPTY/UPLOADED/PROCESSING/EXTRACTED/ERROR` |
| `source` | `WorkflowDocumentSource` | `SINGLE/BULK` |
| `extraction` | `dict` (JSONB) | crudo `{field: value}` — **sin confidence** |
| `mapped_extraction` | `dict \| None` (JSONB) | **confidence aquí** (§2.4) |
| `validation` | `list` (JSONB) | `[{field, valid, message}]` |
| `extraction_pages` / `extraction_metadata` | JSONB \| None | metadatos del run (en ORM) |
| `extracted_text` | `str \| None` (Text) | **texto OCR plano** (cortado por `page_range`) |
| `document_index` | int \| None | índice del doc en el set |
| `processing_status` | str \| None | estado interno del pipeline |
| `page_range` | `dict \| None` | `{from_page, to_page}` |
| `created_at` / `updated_at` | datetime | mixin |

> ⚠️ **Correcciones de hecho (verificadas contra el ORM y la migración inicial):**
> - La columna del archivo se llama **`name`** (String 255), **no `file_name`**.
>   `file_name`/`mime_type` existen **solo en el modelo de dominio**
>   (`workflow_document.py` dominio), mapeados vía `from_attributes`; **no hay columna
>   `mime_type`** en la tabla. El presenter mapea `name` → `fileName` para el payload;
>   **`mimeType` se omite del payload** (sin fuente — decisión §5.21).
> - **NO existe la columna `error`** en `WorkflowDocumentORM` ni en la tabla (ver §2.6)
>   → el snapshot de `document.failed` la necesita, **debe añadirse en Fase 1**.
> - `workflow_id` es **no-nullable** en el ORM.

`WorkflowDocumentStatus` (`.../enums/workflows.py:24-32`): `EMPTY, UPLOADED,
PROCESSING, EXTRACTED, ERROR`.

### 2.4 Estructura de `mapped_extraction` (de dónde sale la confidence)
`backend/src/common/domain/entities/workflows/document_processing.py:77-85`

```python
class MappedLeaf(BaseModel):
    value: str | int | float | bool | None = None
    source_text: str | None = None
    page_number: int | None = None
    bbox: list[BBoxHit] = Field(default_factory=list)
    inferred: bool = False

class BBoxHit(BaseModel):
    page_number: int
    polygon: list[dict]
    matched_text: str
    confidence: float | None = None    # <-- confidence por región (lista por campo)
```

> ⚠️ No hay escalar de confidence por campo: está anidada por `bbox` (puede ser
> `None`). El evento deriva un escalar (decisión §5.3).

### 2.5 DocumentType (para el dict mínimo `{id, name}`)
Dominio: `backend/src/common/domain/models/processing/document_type.py:7-22`
ORM: `backend/src/common/database/models/document_type.py:11-81`

- `uuid: UUID` (id) · `name: str` (1–255). El pipeline **no** carga DocumentType;
  hay que resolver `name` por lookup batch (§4.5).

### 2.6 WorkflowDocument: persistencia de éxito y fallo
`backend/src/workflows/presentation/workflows/activities/mark_document_status.py`

La activity `mark_document_status` maneja **ambos** caminos (docstring del archivo:
*"success path … and the failure path (record the error, mark
processing_status='failed')"*):

```python
_DOCSTATUS_TO_LEGACY = {
    DocumentStatus.COMPLETED: WorkflowDocumentStatus.EXTRACTED,
    DocumentStatus.FAILED:    WorkflowDocumentStatus.ERROR,
}
...
if data.error is not None:
    values["error"] = data.error          # <-- el error del doc se persiste
    logger.warning(f"mark_document_status.error document_id=... error=...")
```

> 🔴 **Corrección:** la columna `error` **NO existe** hoy en `WorkflowDocumentORM`
> ni en la tabla `workflow_documents` (verificado contra el ORM y la migración
> inicial; ninguna migración la añade). Por tanto `mark_document_status.py:79`
> (`values["error"] = data.error`) es un **bug latente**: ese `UPDATE` reventaría en
> el camino de fallo (`data.error is not None`). Para emitir `document.failed` con
> datos reales **hay que añadir la columna `error`** (migración Alembic + campo ORM +
> dominio/presenter) en **Fase 1**, lo que de paso arregla el bug.

### 2.7 WorkflowDocumentSet (contexto/envelope del run)
Dominio: `backend/src/common/domain/models/workflow_document_set.py`

| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUID | id del set |
| `workflow_id` / `tenant_id` | UUID | |
| `processing_job_id` | `str` (**not null**) | id del job/run Temporal del set (existe en dominio+ORM); el evento usa el `run_id` pasado al activity — §4.1/§5.14 |
| `file_id` / `file_name` | UUID / str\|None | archivo origen |
| `status` | `WorkflowDocumentSetStatus` | |
| `started_at` / `finished_at` | datetime\|None | |
| **`duration_ms`** | `int \| None` (property) | **"tiempo de ejecución"** (finished−started) |
| `extracted_text` / `classified_pages` | str\|None | URIs S3 de salidas lambda |

### 2.8 Pipeline STANDARD (Temporal) y finalización
Workflow: `backend/src/workflows/presentation/workflows/document_set_processing.py:178-187`
(delegado a `run_extraction_pipeline()` en `pipeline.py`).

**Checkpoint final** (`pipeline.py:455-478`): calcula `final_status` y publica:

```python
if not failed_ids:   final_status, final_type = JobStatus.COMPLETED, DocumentSetEventType.COMPLETED
elif completed:      final_status, final_type = JobStatus.PARTIAL,   DocumentSetEventType.COMPLETED
else:                final_status, final_type = JobStatus.FAILED,    DocumentSetEventType.FAILED
await workflow_self._checkpoint(data, type=final_type, payload={...}, job_status=final_status)
return DocumentProcessingOutput(...)
```

> `pipeline.py` corre **dentro del sandbox determinístico de Temporal**: sin I/O
> HTTP. El dispatch del webhook **debe** ser una *activity* aparte (§4.6).

### 2.9 Patrón de webhook ANALYSIS (referencia — hoy no-op, sin cablear)
- Protocolo no-op: `analysis_run_summary/webhook_dispatcher.py:15-30`
  (`SummaryWebhookDispatcher` + `NoopSummaryWebhookDispatcher`).
- Disparo fire-and-forget: `complete_run.py:89-93`.
- Inyección: `run_worker.py:94-98` — **el dispatcher NO se inyecta hoy** (`None`).
- **No hay** cliente HTTP, firma, ni URL destino. Es esqueleto.

### 2.10 Config de webhook que YA existe (parcial)
- **Secret a nivel TENANT**: `tenant.webhook_signature_key`
  (`whsec_{secrets.token_urlsafe(32)}`), regenerable vía
  `POST /tenants/{id}/settings/webhook-key`.
- **Front (mock, por workflow)**: `data-export-config-form.tsx` recibe
  `workflowSlug`, sección **Webhooks** con secret `whs_...` hardcodeado y botones
  mockeados → **UI objetivo** de la config por workflow.
- `httpx>=0.28.1` ya en `backend/pyproject.toml:17`.
- `enums/webhooks.py` solo define `PaymentWebhookEventStatus` (sin eventos de workflow).

---

## 3. Lo que FALTA (gaps)

1. **🔴 No existe modelo de evento de salida** (`WorkflowEvent`) ni tabla para
   persistir/auditar/reenviar lo que va al webhook.
2. **🔴 No existe destino (URL) del webhook** en ningún modelo. Solo el secret a
   nivel tenant. **Bloqueante.**
3. **🔴 No hay infra de firma/HTTP**: dispatcher ANALYSIS es protocolo no-op; sin
   HMAC, headers, cliente HTTP cableado.
4. **🟡 Confidence no es escalar** (anidada por bbox).
5. **🟡 `document_type.name` requiere un join** que el pipeline no hace.
6. **🟡 Sin idempotencia / reintentos / auditoría** de entrega.
7. **🟡 Tamaño del payload**: `extracted_text` puede ser grande.

---

## 4. Diseño propuesto (STANDARD)

### 4.0 Vista general

```
pipeline STANDARD (sandbox Temporal)
  ... mark_document_status (persiste cada WorkflowDocument: EXTRACTED | ERROR) ...
  checkpoint final  →  final_status ∈ {COMPLETED, PARTIAL, FAILED}
       │   (en estado terminal SIEMPRE se lanza el activity; el gate se evalúa DENTRO — §5.20)
       ▼
  execute_activity("dispatch_document_set_webhook",
                   {document_set_id, tenant_id, workflow_id, final_status, run_id})
       │                                (I/O boundary — fuera del sandbox)
       ▼
  DispatchDocumentSetWebhookActivity → use case DispatchDocumentSetWebhooks
    0. gate (§5.15): si webhook_enabled=false o sin webhook_url → no crea eventos, retorna
    1. carga Workflow (name, type, url/enabled/secret/events) + WorkflowDocumentSet (contexto)
    2. carga WorkflowDocuments del set en estado TERMINAL (EXTRACTED ∪ ERROR), por tenant
    3. batch-fetch DocumentType {id, name}
    4. por cada doc:  crea/recupera un WorkflowEvent (idempotente)  →  arma payload
                      →  firma HMAC  →  POST  →  actualiza delivery_status del evento
    5. fire-and-forget a nivel run: un fallo de entrega NO falla el run (siempre retorna éxito)
```

### 4.1 Modelo `WorkflowEvent` (NUEVO — backbone)
Dominio: `backend/src/common/domain/models/processing/workflow_event.py`
ORM: `backend/src/common/database/models/workflow_event.py` (tabla `workflow_events`)
+ migración Alembic.

Es un registro **append-only** de eventos de salida. Un `WorkflowEvent` por cada
`WorkflowDocument` finalizado (EXTRACTED o ERROR). Persiste el **payload snapshot**
que se entrega y el **estado de entrega** (auditoría + replay).

| Campo | Tipo (ORM) | Notas |
|---|---|---|
| `uuid` | UUID (PK) | de `UUIDTenantTimestampMixin` |
| `tenant_id` | UUID | tenancy (mixin) |
| `event_id` | `String(64)`, unique | **público**, `evt_<uuid>` → header `Doxiq-Id` |
| `event_type` | `String(50)` | `WebhookEventType` (§4.2) |
| `workflow_id` | UUID (FK workflows) | |
| `document_set_id` | UUID \| None (FK) | contexto del run |
| `document_id` | UUID \| None (FK workflow_documents) | doc fuente |
| `processing_job_id` | `String(255)` | **= Temporal `workflow.info().run_id`**, pasado explícitamente en el input del activity (decisión §5.14) → distingue re-ejecuciones. NO se lee del set |
| `document_status` | `String(25)` | **status del WorkflowDocument**: `EXTRACTED`\|`ERROR` |
| `payload` | `JSONB` | snapshot **inmutable** del cuerpo entregado (§4.3) |
| `delivery_status` | `String(20)` | `WorkflowEventDeliveryStatus` (§4.1.1) |
| `attempts` | `Integer`, default 0 | nº de intentos de entrega |
| `last_attempt_at` | DateTime \| None | |
| `delivered_at` | DateTime \| None | timestamp del 2xx |
| `response_status` | `Integer` \| None | último HTTP status del receptor |
| `last_error` | `Text` \| None | último error de entrega |
| `created_at` / `updated_at` | DateTime | mixin |

Constraints / índices:
- **Unique** `(document_id, event_type, processing_job_id)` → **idempotencia por
  run** (decisión §5.12/§5.14): como `processing_job_id` = Temporal `run_id`, un retry
  de la *misma* activity reusa el run_id (no duplica eventos, reusa `event_id`), pero
  una **re-extracción** (nuevo run_id, **incluso SINGLE in-place**) genera un evento
  nuevo con nuevo `event_id` → el cliente se entera del reproceso.
- Índice `(tenant_id, workflow_id, created_at)` y `(delivery_status)` para
  listar/reintentar pendientes (lo usa el job de reenvío §4.8).

> **Por qué persistir el payload completo:** garantiza reproducir exactamente lo
> entregado aunque el `WorkflowDocument` cambie luego (re-extracción), y habilita
> reenvío sin recomputar. Trade-off: duplica algunos datos de `workflow_documents`
> (aceptable; el evento es la fuente de verdad de la entrega).

#### 4.1.1 Enums nuevos
`backend/src/common/domain/enums/webhooks.py`:

```python
class WebhookEventType(BaseEnum):
    DOCUMENT_EXTRACTED = "document.extracted"   # WorkflowDocument.status == EXTRACTED
    DOCUMENT_FAILED    = "document.failed"      # WorkflowDocument.status == ERROR

class WorkflowEventDeliveryStatus(BaseEnum):
    PENDING    = "PENDING"      # creado, no entregado aún
    DELIVERING = "DELIVERING"   # intento en curso
    DELIVERED  = "DELIVERED"    # 2xx del receptor
    FAILED     = "FAILED"       # agotó reintentos / 4xx definitivo
    SKIPPED    = "SKIPPED"      # creado pero NO entregado: tipo no suscrito (gate ON) — §4.9/§5.15
```

### 4.2 Eventos y disparo (decisión §5.2 + §5.4)
**Un `WorkflowEvent` + un POST por cada `WorkflowDocument` finalizado**, mapeando
status → tipo de evento:

| `WorkflowDocument.status` | `event_type` |
|---|---|
| `EXTRACTED` | `document.extracted` |
| `ERROR` | `document.failed` |

- Se dispara para **todos** los estados terminales del set
  (**COMPLETED, PARTIAL y FAILED**), porque ahora también queremos enviar los
  fallos. Si el set quedó FAILED total, igual se emiten los `document.failed`.
- **Gate** único: `workflow.webhook_enabled AND workflow.webhook_url`.
- Solo se consideran docs en estado **terminal** (`EXTRACTED` o `ERROR`); los que
  quedaron en `PROCESSING/EMPTY/UPLOADED` (caso anómalo) se omiten + log.

> 🔁 **Revisión vs. decisión inicial:** el primer acuerdo fue "COMPLETED+PARTIAL,
> solo docs EXTRACTED". El nuevo requerimiento (`WorkflowEvent` + enviar fallos)
> lo **reemplaza**: ahora se emiten también `document.failed` y se dispara en
> cualquier estado terminal del set. (§5.4)

### 4.3 Payload del evento (snapshot persistido en `WorkflowEvent.payload`)
Cuerpo **camelCase** (reusa `convert_to_camel_case`); `extraction` se envuelve en
`RawJson` para **preservar los nombres de campo** del documento.

```jsonc
{
  "eventId": "evt_<uuid>",                    // = WorkflowEvent.event_id, header Doxiq-Id
  "event": "document.extracted",              // o "document.failed"
  "occurredAt": "2026-06-01T12:00:00Z",       // = documentSet.finishedAt
  "workflow": { "id": "<uuid>", "name": "Facturación", "type": "STANDARD" },
  "documentSet": {
    "id": "<uuid>",
    "fileName": "lote_facturas.pdf",
    "status": "COMPLETED",                      // = final_status (JobStatus.value): COMPLETED | PARTIAL | FAILED — NO el WorkflowDocumentSetStatus
    "startedAt": "2026-06-01T11:59:48Z",
    "finishedAt": "2026-06-01T12:00:00Z",
    "durationMs": 12000                         // WorkflowDocumentSet.duration_ms
  },
  "document": {
    "id": "<uuid>",                             // WorkflowDocument.uuid
    "status": "EXTRACTED",                      // EXTRACTED | ERROR  (WorkflowEvent.document_status)
    "fileName": "factura_001.pdf",
    "pageRange": { "fromPage": 1, "toPage": 2 },
    "documentType": { "id": "<uuid>", "name": "Factura" },   // o null ("Otros")
    "extraction": {                             // RawJson; null/parcial cuando ERROR
      "total":   { "value": 1234.5, "confidence": 0.99 },
      "client":  { "value": "ACME", "confidence": 0.97 },
      "dueDate": { "value": null,   "confidence": null }
    },
    "plainText": "FACTURA N° 001 ...",          // extracted_text (OCR) inline; null si no hay
    "validation": [ { "field": "total", "valid": true, "message": null } ],
    "error": null,                              // null en éxito
    "createdAt": "2026-06-01T11:59:50Z",
    "updatedAt": "2026-06-01T12:00:00Z"
  }
}
```

**Variante `document.failed`** (mismo envelope, `document` cambia):

```jsonc
"document": {
  "id": "<uuid>", "status": "ERROR",
  "fileName": "factura_007.pdf",
  "pageRange": { "fromPage": 7, "toPage": 7 },
  "documentType": { "id": "<uuid>", "name": "Factura" },   // o null
  "extraction": null,                          // o parcial si hubo extracción previa
  "plainText": "....",                         // si alcanzó a haber OCR; si no, null
  "validation": [],
  "error": { "code": "EXTRACTION_FAILED", "message": "..." },   // WorkflowDocument.error
  "createdAt": "...", "updatedAt": "..."
}
```

### 4.4 Derivación de la confidence por campo (decisión §5.3)
Para cada campo de `mapped_extraction` se emite `{ value, confidence }`:

- `value` = `MappedLeaf.value`.
- `confidence` = **mínimo** de `bbox[].confidence` no nulos, o `None` si no hay
  bbox / todos `None` / `inferred == True`. ("Mínimo" = la más conservadora.)
- **Fallback** si `mapped_extraction is None` pero `extraction` (crudo) existe:
  `{ value: <crudo>, confidence: null }` por campo.
- En `document.failed`: `extraction` puede ser `null` si nunca se extrajo.

> Helper: `build_extraction_payload(mapped_extraction, extraction) -> dict | None`.

### 4.5 Resolución de `documentType` `{id, name}`
En el use case: recolectar `document_type_id` no nulos → **batch lookup** al
`DocumentTypeRepository.find_by_ids(ids, tenant_id)` → mapa `{id: name}`.
`document_type_id is None` → `"documentType": null`.

### 4.6 Punto de inserción Temporal (decisión §5.7)
1. **Activity** `dispatch_document_set_webhook`
   (`workflows/presentation/workflows/activities/dispatch_document_set_webhook.py`).
   Input: `DispatchDocumentSetWebhookInput{ document_set_id, tenant_id,
   workflow_id, final_status, run_id }` (`run_id = workflow.info().run_id`, decisión
   §5.14 → se persiste como `WorkflowEvent.processing_job_id`). Re-carga el resto de DB
   (nada más se threadea por el sandbox).
2. **Constante** `DISPATCH_DOCUMENT_SET_WEBHOOK_ACTIVITY` en `document_set_processing.py:69-75`.
3. **Invocación** en `pipeline.py`, tras el checkpoint final (`:465`) y antes del
   `return` (`:478`):

```python
if final_status in (JobStatus.COMPLETED, JobStatus.PARTIAL, JobStatus.FAILED):
    await workflow.execute_activity(
        DISPATCH_DOCUMENT_SET_WEBHOOK_ACTIVITY,
        DispatchDocumentSetWebhookInput(
            document_set_id=data.document_set_uuid,
            tenant_id=data.tenant_id,
            workflow_id=data.workflow_id,
            final_status=final_status.value,
            run_id=workflow.info().run_id,   # -> WorkflowEvent.processing_job_id (§5.14)
        ),
        start_to_close_timeout=timedelta(seconds=60),
        # retry_policy SOLO cubre fallos de infra (DB): la entrega HTTP nunca lanza
        # fuera del activity (§5.16); el activity siempre retorna exito.
        retry_policy=DEFAULT_RETRY_POLICY,
    )
```

4. **Registro** en `run_worker.py` (instanciar con `session_maker` + cliente HTTP
   + dispatcher real) y añadir a `worker.run(activities=[...])`.
5. La activity chequea el gate (`webhook_enabled and webhook_url`) — **semántica mixta
   (decisión §5.15)**:
   - **Gate off** (`webhook_enabled = false` o sin `webhook_url`) → **NO se crean**
     eventos (+ log) y retorna.
   - **Gate on, tipo no suscrito** (`event_type ∉ webhook_events`) → se **crea** el
     `WorkflowEvent` y se marca `SKIPPED` (auditoría); no se entrega.
6. **Fire-and-forget estricto (decisión §5.16):** la activity **captura toda excepción
   de entrega/proceso**, la persiste en el `WorkflowEvent` (`DELIVERED`/`FAILED`) y
   **siempre retorna éxito**. Un endpoint caído nunca falla el run; el `retry_policy`
   del activity solo se dispara ante fallos de infra (DB), nunca por resultados HTTP.

> Dispatcher real `HttpWorkflowWebhookDispatcher` en
> `workflows/infrastructure/services/webhooks/`, implementa el protocolo
> `WorkflowWebhookDispatcher` (`workflows/application/document_sets/webhook_dispatcher.py`,
> nuevo, espejo de `SummaryWebhookDispatcher`).

### 4.7 Firma HMAC y headers (decisión §5.6)
Estilo Svix sobre `httpx`. Por request:

```
POST <webhook_url>
Content-Type: application/json
User-Agent: Doxiq-Webhooks/1.0
Doxiq-Id:        evt_<uuid>                 # = WorkflowEvent.event_id
Doxiq-Timestamp: <unix_seconds>
Doxiq-Signature: v1,<base64( HMAC_SHA256(key, signed_content) )>
```

- `signed_content = f"{event_id}.{timestamp}.{raw_body}"`.
- `key` = **base64-decode** del `webhook_secret` sin prefijo `whsec_` (estilo Svix
  estricto, decisión §5.6/§5.17) → los clientes pueden reusar librerías Svix tal cual.
- Receptor: rechazar si `|now - timestamp| > 5 min`; comparación en tiempo constante.
- Util compartido: `common/application/helpers/webhooks/signing.py`
  → `sign_payload(secret, body, event_id, ts) -> str`.

### 4.8 Reintentos, idempotencia, entrega y replay (decisión §5.8)
- **Idempotencia**: `event_id` persistido y estable; unique `(document_id,
  event_type, processing_job_id)`. Crear eventos es idempotente **por run** (un
  retry de la misma activity reusa los existentes; una re-extracción crea evento
  nuevo — §5.12). El receptor deduplica por `Doxiq-Id`.
- **Reintentos de entrega (inmediatos)**: cada POST con **3 intentos**, backoff
  exponencial (~1s/2s/4s) (decisión §5.23). 2xx → `DELIVERED`; 5xx/timeout →
  reintentar; 4xx (salvo 429) → `FAILED`. Cada intento actualiza
  `attempts/last_attempt_at/response_status/last_error` en el `WorkflowEvent`.
- **Fire-and-forget a nivel run**: un fallo de entrega NO falla el documento ni el
  set; queda registrado como `WorkflowEvent.delivery_status = FAILED`.
- **Reenvío automático programado (decisión §5.13)**: un job periódico
  (`RetryPendingWorkflowEvents`) escanea eventos `FAILED`/`PENDING` (índice por
  `delivery_status`) y los reintenta con backoff exponencial hasta un tope de
  **8 `attempts`** y/o una ventana máxima de **24 h** (decisión §5.19), tras lo cual
  quedan en `FAILED` definitivo. Programación: cron/worker periódico (ver `run_worker.py` /
  scheduler existente). Marca `DELIVERING` mientras intenta para evitar carreras
  entre el dispatch inmediato y el job.

### 4.9 Config POR WORKFLOW (decisión §5.1)
Campos nuevos en `Workflow` + `WorkflowORM` (tabla `workflows`) + migración:

| Campo | Tipo (ORM) | Default | Notas |
|---|---|---|---|
| `webhook_url` | `String(2048)`, nullable | `None` | endpoint destino (https) |
| `webhook_enabled` | `Boolean`, not null | `false` | **gate** (análogo a `synthesis_enabled`) |
| `webhook_secret` | `String(255)`, nullable | `None` | firma por workflow, `whsec_{token_urlsafe(32)}` |
| `webhook_events` | `JSONB`, not null | `["document.extracted","document.failed"]` | suscripción de eventos |

- Gate efectivo: `webhook_enabled AND webhook_url`. **Semántica de creación
  (decisión §5.15, "mixto"):** gate **off** → **no** se crea evento; gate **on** pero
  `event_type ∉ webhook_events` → se **crea** y se marca `SKIPPED`. `webhook_events`
  guarda los **`.value`** de `WebhookEventType` (`"document.extracted"`/
  `"document.failed"`); el filtro compara contra `WorkflowEvent.event_type` (también
  `.value`).
- `webhook_secret` se genera al activar por primera vez o vía endpoint regenerar.
- Prefijo estándar **`whsec_`** (igual al tenant/Svix); el mock del front usa
  `whs_` → se actualiza (§8 Fase 4).
- `tenant.webhook_signature_key` se mantiene; STANDARD firma con el secret **del workflow**.

**API de config** (presentation):
- ⚠️ **Corrección:** la ruta de update **ya existe** como **`PUT /workflows/{id}`**
  (`update_workflow` + `WorkflowUpdater` + `UpdateWorkflowRequest`, `router.py:108`) —
  **no** `PATCH`. Extenderla: agregar `webhookUrl/webhookEnabled/webhookEvents` a
  `UpdateWorkflowRequest` y pasarlos por `WorkflowUpdater` (o añadir un PATCH dedicado
  si se prefiere update parcial).
- `POST /v1/workflows/{id}/webhook-secret`: regenera y devuelve el secret (espejo de
  `webhook_key_regenerator.py`).
- **NUEVO `GET /v1/workflows/{id}/events`**: lista paginada de `WorkflowEvent` (filtro
  por `delivery_status`) → alimenta el delivery log de la UI (§10).
- **NUEVO `POST /v1/workflows/{id}/events/{eventId}/replay`**: re-dispara la entrega de
  un evento (replay **manual**, distinto del job automático §4.8); marca `DELIVERING`.
- Presenter de Workflow (`presenters/workflow.py`, hoy ya expone `synthesisEnabled`
  como análogo) añade `webhookUrl/webhookEnabled/webhookEvents` (y `webhookSecret`
  solo en settings). Presenter nuevo para `WorkflowEvent` (el listado **no** trae el
  `payload` completo; detalle aparte).

---

## 5. Decisiones

### Resueltas (confirmadas con el usuario)
1. **✅ Config POR WORKFLOW.** `webhook_url/enabled/secret/events` en `Workflow`
   (+ migración). Coincide con `DataExportConfigForm`. (§4.9)
2. **✅ Granularidad: 1 evento + 1 POST por documento.** El dispatch ocurre en la
   finalización del set, iterando los docs terminales → un `WorkflowEvent` + POST
   c/u. (§4.2/§4.6)
3. **✅ Confidence: escalar derivado por campo** `{value, confidence}`,
   `min(bbox)` o `null`. (§4.4)
4. **✅ Enviar también los fallos vía `WorkflowEvent`.** *(reemplaza el acuerdo
   inicial "solo EXTRACTED")*: se emiten `document.extracted` (EXTRACTED) y
   `document.failed` (ERROR); se dispara en COMPLETED/PARTIAL/FAILED. (§4.1/§4.2)
5. **✅ Modelo persistido `WorkflowEvent`** como backbone (event id + status del
   doc + datos relevantes + estado de entrega). Habilita idempotencia, auditoría y
   replay. (§4.1)

### Resueltas (decisión técnica del autor)
6. **✅ Firma:** HMAC-SHA256 estilo Svix, headers `Doxiq-Id/Timestamp/Signature`,
   `signed_content = id.ts.body`, **key = base64-decode del token sin `whsec_`**
   (Svix estricto, decisión §5.17), tolerancia 5 min, `httpx`. (§4.7)
7. **✅ Inserción Temporal:** activity dedicada que re-carga `WorkflowDocument`s de
   DB (`document_set_id` + `tenant_id`, status terminal). (§4.6)
8. **✅ Idempotencia/reintentos:** `event_id` persistido + unique
   `(document_id, event_type, processing_job_id)`; reintento por-POST acotado;
   estado de entrega en el evento. (§4.8)
9. **✅ Casing:** camelCase reusando `convert_to_camel_case`; `extraction` en
   `RawJson`. (§4.3)
10. **✅ `plainText` inline** con guarda de tamaño. (§6)
11. **✅ Alcance: solo STANDARD.** Infra compartida (WorkflowEvent, signing, cliente
    HTTP, enums, config por workflow) reutilizable; **ANALYSIS se diseña en un spec
    aparte**, fuera de alcance de este spec. (§9)

### Resueltas (confirmadas con el usuario — 2ª ronda)
12. **✅ Re-extracción: re-emitir por run.** Unique
    `(document_id, event_type, processing_job_id)`; cada reproceso genera un
    `WorkflowEvent` nuevo con nuevo `event_id`. (§4.1)
13. **✅ Replay: reenvío automático programado.** Job periódico
    `RetryPendingWorkflowEvents` reintenta `FAILED`/`PENDING` con backoff y tope.
    (§4.8)

### Resueltas (confirmadas con el usuario — 3ª ronda)
14. **✅ `processing_job_id` = Temporal `run_id`.** Se pasa `run_id =
    workflow.info().run_id` en el input del activity y se persiste como
    `WorkflowEvent.processing_job_id` (no se lee del set). Garantiza que el unique
    `(document_id, event_type, processing_job_id)` difiere en cada re-extracción
    (incluso SINGLE in-place), mientras un retry de Temporal del mismo run reusa el
    run_id (idempotencia real). (§4.1/§4.6)
15. **✅ `SKIPPED` mixto por caso.** Gate off (`webhook_enabled=false` o sin URL) →
    **no** se crea evento. Gate on pero tipo no suscrito → se **crea** + `SKIPPED`.
    (§4.1.1/§4.6/§4.9/§6)
16. **✅ Fire-and-forget estricto.** El activity captura toda excepción de entrega, la
    persiste en el `WorkflowEvent` y **siempre retorna éxito**; el `retry_policy` solo
    cubre infra (DB). La entrega HTTP nunca falla el run ni dispara retry de Temporal.
    (§4.6/§4.8)
17. **✅ Clave HMAC: base64-decode estilo Svix estricto** (no utf-8). Permite a los
    clientes reusar librerías Svix; se documenta el decode en las docs públicas. (§4.7)

18. **✅ Contenido de `document.failed`: incluir lo que haya.** Si existe extracción
    parcial y/o `plainText` (OCR alcanzó a correr) se incluyen; si no, `null`. Máxima
    señal de debug; aplica la guarda de tamaño de §6. (§4.3/§4.4)
19. **✅ Topes del job de reenvío: 8 intentos / 24 h** como constantes firmes, tras lo
    cual el evento queda `FAILED` definitivo. Configurabilidad por workflow queda como
    TODO futuro. (§4.8)

### Resueltas (confirmadas con el usuario — 4ª ronda)
20. **✅ Gate: siempre lanzar el activity + gatear DENTRO.** En estado terminal el
    pipeline siempre lanza `dispatch_document_set_webhook`; el gate
    (`webhook_enabled`/`url`) se evalúa dentro del activity (no en el sandbox), que
    retorna rápido si no aplica. Evita cargar la config del workflow en el sandbox.
    (§4.0/§4.6)
21. **✅ `mimeType` quitado del payload.** No existe columna fuente (`mime_type` es
    solo-dominio sin columna ORM) → se omite del evento para no prometer un campo
    siempre `null`. (§2.3/§4.3)
22. **✅ Sección UI (config + auditoría/replay).** Se especifica en **§10** la UI del
    cliente: form real (URL/enabled/event types/secret) **y** delivery log con replay
    sobre `WorkflowEvent`. Requiere endpoints nuevos (§4.9) + ruta BFF. (§10)

### Resueltas (confirmadas con el usuario — 5ª ronda)
23. **✅ Reintento por-POST inmediato: 3 intentos, backoff exp (~1s/2s/4s).** Acotado;
    lo no entregado pasa al job programado (§5.19). (§4.8)
24. **✅ Umbral de `plainText`: 5 MB.** Sobre ese tamaño se omite con
    `plainTextOmitted: true` (futuro: URI S3). (§6)

### Abiertas
- Ninguna. Todas las decisiones de STANDARD están cerradas (1–24). Lo pendiente es la
  implementación (§8). **ANALYSIS queda fuera de alcance** (§9, spec aparte).

---

## 6. Edge cases

- **Set FAILED total**: ahora SÍ dispara → emite `document.failed` por cada doc ERROR.
- **Set PARTIAL**: mezcla de `document.extracted` y `document.failed`.
- **`mapped_extraction is None`** pero `extraction` OK: fallback (§4.4).
- **`document_type_id is None`** ("Otros"): `documentType: null`.
- **Gate off** (`webhook_enabled` false o `webhook_url` vacío): **no se crean** eventos
  + warning (decisión §5.15). `SKIPPED` se reserva para tipo no suscrito con gate on.
- **`webhook_secret` vacío al disparar**: generar al activar; validar en la activity.
- **Retry de Temporal** re-ejecuta la activity: idempotente por unique
  `(document_id, event_type, processing_job_id)` → no duplica eventos; reintenta
  solo los no `DELIVERED`.
- **`extracted_text` muy grande**: si el body supera **5 MB** (decisión §5.24) se omite
  `plainText` con `"plainTextOmitted": true` (futuro: URI S3 desde
  `documentSet.extractedText`).
- **Endpoint del cliente caído / 5xx persistente**: reintentos acotados → evento
  queda `FAILED` (replay posterior). No bloquea el run.
- **SSRF**: validar `webhook_url` (solo `https`, sin IPs privadas/loopback) al
  guardar y antes de enviar.
- **Tenancy**: filtrar `WorkflowDocument`/`DocumentType`/`WorkflowEvent` por `tenant_id`.
- **Re-extracción** (BULK borra+recrea / SINGLE in-place): **re-emitir por run**
  (§5.12). BULK genera nuevos doc uuids → nuevos eventos naturalmente; SINGLE
  reusa el `document_id` pero el nuevo `processing_job_id` hace que el unique
  `(document_id, event_type, processing_job_id)` no choque → se crea un
  `WorkflowEvent` nuevo con nuevo `event_id`. El cliente recibe el reproceso.
- **Reloj / dos timestamps distintos**: `occurredAt` (en el body) = tiempo de negocio
  del evento (`documentSet.finishedAt`, persistido en el checkpoint final antes del
  dispatch); `Doxiq-Timestamp` (header) = tiempo de **envío** real (reloj de la
  activity), usado solo para la ventana de frescura de 5 min. No son el mismo valor.
  `workflow.now()` solo aplica en el sandbox.

---

## 7. ERD (resumen de lo nuevo)

```
workflows (existente)
  + webhook_url, webhook_enabled, webhook_secret, webhook_events

workflow_events (NUEVO)
  uuid (PK), tenant_id, event_id (uq), event_type, document_status,
  processing_job_id,
  workflow_id → workflows.uuid,
  document_set_id → workflow_document_sets.uuid,
  document_id → workflow_documents.uuid,
  payload (jsonb), delivery_status, attempts, last_attempt_at,
  delivered_at, response_status, last_error, created_at, updated_at
  UNIQUE (document_id, event_type, processing_job_id)
  INDEX (delivery_status)  -- job de reenvío
```

---

## 8. Plan de implementación

### Fase 0 — Infra compartida
1. `enums/webhooks.py`: `WebhookEventType` (`document.extracted`,
   `document.failed`) + `WorkflowEventDeliveryStatus`.
2. `common/application/helpers/webhooks/signing.py`: HMAC + headers.
3. Cliente HTTP compartido (`httpx.AsyncClient`) con timeout + reintento por-POST.

### Fase 1 — Modelos + migraciones
4. `WorkflowEvent` dominio + `WorkflowEventORM` (tabla `workflow_events`) +
   repositorio (`create`, `find_by_id`, `list_by_set`, `mark_delivered/failed`) +
   builder + presenter. **Migración Alembic.**
5. `Workflow`: `webhook_url/enabled/secret/events` (dominio + ORM + builder +
   updater + presenter). **Migración Alembic.**
6. **Añadir** la columna `error` (JSONB \| None) en `WorkflowDocumentORM` + migración
   Alembic + campo dominio/presenter (**NO existe hoy** — §2.6). Esto además arregla el
   bug latente de `mark_document_status.py:79` (`values["error"]` contra columna
   inexistente).

### Fase 2 — Config por workflow (API + front)
7. Endpoints: **extender `PUT /workflows/{id}`** (`UpdateWorkflowRequest` +
   `WorkflowUpdater`) con `webhookUrl/webhookEnabled/webhookEvents` +
   `POST .../webhook-secret`. (No es PATCH — §4.9.)
8. Front (ver **§10**): reemplazar el mock de `DataExportConfigForm` por la config real
   (form URL/enabled/event types/secret → `PUT /workflows/{id}` vía **ruta BFF**;
   regenerar secret `whsec_`), i18n `DataExportConfig`. Añadir el **delivery log**
   (lista de `WorkflowEvent` con estados/attempts/last_error + acción **replay**) sobre
   los endpoints nuevos `GET .../events` y `POST .../events/{eventId}/replay` (§4.9).

### Fase 3 — Dispatch STANDARD (Temporal)
9. Protocolo `WorkflowWebhookDispatcher` + `NoopWorkflowWebhookDispatcher`
   (`workflows/application/document_sets/webhook_dispatcher.py`).
10. `HttpWorkflowWebhookDispatcher` (`infrastructure/services/webhooks/`): firma +
    entrega + actualización del `WorkflowEvent`.
11. Use case `DispatchDocumentSetWebhooks`: carga Workflow + Set + Documents
    (terminales, por tenant) + batch DocumentType; crea `WorkflowEvent`s
    (idempotente); arma payload (confidence §4.4, documentType §4.5, error §4.3);
    delega entrega; fire-and-forget.
12. Activity `dispatch_document_set_webhook` + constante + invocación en
    `pipeline.py` (post-checkpoint, gate `webhook_enabled`/`url`, terminal states)
    + registro en `run_worker.py`.

### Fase 4 — Reenvío automático + calidad
13. Job programado `RetryPendingWorkflowEvents` (§4.8): escanea `delivery_status ∈
    {PENDING, FAILED}` con backoff y tope (`attempts ≤ 8` / ventana 24 h); marca
    `DELIVERING` para evitar carreras con el dispatch inmediato. Registrar como
    actividad/worker periódico en `run_worker.py` o el scheduler existente.
14. Validación SSRF de `webhook_url`; guarda de tamaño de `plainText`.
15. Tests: unit (confidence, firma, armado payload éxito+fallo, fallback
    mapped_extraction null), use case (repos mockeados, gate, tenancy, idempotencia
    unique por run, batch DocumentType, job de reenvío), e2e (set
    COMPLETED/PARTIAL/FAILED + re-extracción re-emite).
16. Docs públicas (`docs.llamit.ai/webhooks`): formato del evento (extracted +
    failed), verificación de firma (**key = base64-decode del secret sin `whsec_`**,
    compatible con librerías Svix), idempotencia por `Doxiq-Id`, tolerancia de timestamp.

---

## 9. ANALYSIS — fuera de alcance

> Los webhooks para workflows **ANALYSIS** **no** se implementan en este spec; se
> diseñarán en un **spec aparte**. La infraestructura compartida de §4/§8 (modelo
> `WorkflowEvent`, `signing.py`, cliente HTTP, enums, config por workflow) queda
> pensada para reutilizarse allí.
>
> Preferencia ya acordada para ese spec futuro: ANALYSIS emitirá **solo** el evento de
> summary (`analysis_run.completed`), **sin** eventos `document.*` por documento.

---

## 10. UI del cliente: configuración + auditoría (decisión §5.22)

> **Alcance:** especifica la UI que el cliente usa para (A) **configurar** el webhook
> por workflow y (B) **auditar/reenviar** entregas. Reusa el componente existente
> `DataExportConfigForm` (hoy mock) y agrega una vista de entregas nueva.
> Diseño visual según `DESIGN.md` (teal, near-flat, *Inspection Bench*).
>
> **Estado hoy (verificado en el front):** existe ~5% — el mock solo muestra el secret
> (`whs_…`, read-only) + copiar/regenerar (`console.log`). **Falta:** input URL, toggle
> enabled, selección de event types, ruta BFF de update, y **toda** la UI de auditoría.

### 10.1 Dónde vive
- Panel lateral (`WorkflowSidebar`, `Sheet`) del step `DATA_EXPORT`, en
  `app/(protected)/workflows/[wf_slug]/workflow/page.tsx`.
- Componente: `presentation/workflows/workflow/data-export-config-form.tsx`.

### 10.2 Form de configuración (sección "Webhooks")
Campos (mapeados a §4.9):
- **Endpoint URL** (`webhookUrl`): input `https://…`; validación cliente (https) +
  servidor (SSRF §6). Vacío ⇒ gate off.
- **Habilitado** (`webhookEnabled`): switch (gate, análogo a `synthesisEnabled`).
- **Eventos** (`webhookEvents`): checkboxes `document.extracted` / `document.failed`
  (los `.value` de `WebhookEventType`); guarda el subconjunto suscrito.
- **Secret** (`webhookSecret`): mostrar enmascarado/solo-lectura con **copiar** y
  **regenerar** (prefijo **`whsec_`**, no `whs_`); avisar que regenerar invalida firmas.
- **Guardar** → `PUT /workflows/{id}` (webhookUrl/Enabled/Events) vía **ruta BFF**
  (`app/api/.../route.ts`, patrón obligatorio cliente→BFF→`serverHttp`); regenerar →
  `POST /workflows/{id}/webhook-secret`.

### 10.3 Delivery log (auditoría + replay) — NUEVO
Tab/vista que lista los `WorkflowEvent` del workflow (vía `GET /workflows/{id}/events`):
- Columnas: `occurredAt`/`createdAt`, `eventType`, documento (`fileName`),
  **estado** (`deliveryStatus`: `PENDING/DELIVERING/DELIVERED/FAILED/SKIPPED`, con badge),
  `attempts`, `responseStatus`, `lastError` (tooltip).
- **Filtro** por `deliveryStatus` (usa el índice de §4.1) + paginación.
- **Acción "Reenviar"** por evento (y bulk para `FAILED`) →
  `POST /workflows/{id}/events/{eventId}/replay` (replay **manual**, distinto del job
  automático §4.8). Deshabilitada para `DELIVERED`.
- Detalle de evento: `payload` entregado, headers de firma, historial de intentos.
  (El listado **no** trae el `payload` completo; se pide en el detalle.)

### 10.4 Notas
- **Seguridad/BFF**: todo el tráfico cliente→backend pasa por rutas BFF; el secret se
  inyecta server-side y no se expone el host del backend (CLAUDE.md).
- **i18n**: ampliar el namespace `DataExportConfig` (es/en).
- **Backend requerido**: los endpoints `GET .../events` y `POST .../events/{id}/replay`
  (§4.9) son net-new respecto al dispatch de §4.6.
