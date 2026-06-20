---
feature: dashboard
type: plan
status: implemented
coverage: 95
audited: 2026-06-16
---

# Spec: Dashboard Data Endpoints

> **Para Claude Code:** Esta spec define los endpoints backend que necesita el dashboard tenant-scoped (`/dashboard`) para reemplazar los mocks del frontend. Cubre los tabs **Overview** y **Processing**. Los tabs Analytics y Validation & Quality fueron removidos del UI.

## Contexto del frontend

El dashboard vive en `frontend/src/app/(protected)/dashboard/page.tsx`. Consume mocks hard-codeados en:
- `presentation/dashboard/overview-chart.tsx` (BarChart 12 meses)
- `presentation/dashboard/recent-documents.tsx` (últimos 5 documentos)
- `presentation/dashboard/processing-tab.tsx` (stat cards, pipeline stages, live processing)

Permiso requerido: `dashboard.view` (ya existe en `common/domain/permissions/namespaces/dashboard.py`).

## Convenciones del proyecto

- Path prefix: `/v1/dashboard`.
- Auth: dependency `get_required_tenant_user` + `check_tenant_permission(..., [DashboardPermission.view])`.
- Response: `ApiJSONResponse` con camelCase (middleware `camel_case.py` convierte automáticamente).
- Architecture: módulo nuevo `src/dashboard/` siguiendo `domain → application → infrastructure → presentation`.
- Repositorios: queries SQL agregadas en `infrastructure/repositories/`, no exponer ORM.

## Endpoints

Tres endpoints en total:
- **2 REST** (uno por tab) — devuelven la data agregada del tab en una sola request.
- **1 SSE** — bus de invalidación push. Detallado en §"Refresh — SSE + eventos de dominio".

Trade-off explícito en los REST: cache y refetch a nivel de tab (granularidad gruesa, pero alineada con la UI real); cualquier sub-sección "fría" cohabita con las "calientes" en el mismo refresh. Aceptable porque el ciclo de refresh está dirigido por SSE (no se gastan requests innecesarios).

### 1. `GET /v1/dashboard/overview`

Toda la data del tab Overview en una respuesta.

**Query params:**
- `throughputMonths` (int, default `12`, máx `24`).
- `recentLimit` (int, default `5`, máx `20`).

**Response:**
```json
{
  "data": {
    "summary": {
      "totalDocuments": { "value": 45231, "deltaPct": 20.1 },
      "documentsProcessed": { "value": 2350, "deltaPct": 180.1 },
      "activeWorkflows": { "value": 12, "deltaPct": 19.0 },
      "processingQueue": { "value": 573, "deltaSinceLastHour": 201 }
    },
    "throughput": [
      { "label": "Jan", "year": 2025, "month": 1, "total": 1200 },
      { "label": "Feb", "year": 2025, "month": 2, "total": 4500 }
    ],
    "recentDocuments": [
      {
        "uuid": "doc-uuid-1",
        "name": "Invoice_2024_001.pdf",
        "workflowSlug": "finance",
        "workflowName": "Finance",
        "status": "EXTRACTED",
        "pageCount": 12,
        "createdAt": "2026-05-18T10:00:00Z",
        "updatedAt": "2026-05-18T10:02:30Z"
      }
    ]
  },
  "datetime": "2026-05-19T12:00:00Z"
}
```

**Queries (todas sobre `workflow_documents`, filtradas por `tenant_id`):**

`summary`:
- `totalDocuments.value` = `COUNT(*)` total del tenant.
- `totalDocuments.deltaPct` = `(count(este_mes) - count(mes_anterior)) / count(mes_anterior) * 100`. Divisor 0 → `null`.
- `documentsProcessed.value` = `COUNT` WHERE `status='EXTRACTED'` AND `updated_at >= start_of_current_calendar_month` (en TZ del tenant). "Procesados este mes" se interpreta como "completaron extracción este mes", de ahí el uso de `updated_at`.
- `documentsProcessed.deltaPct` = ídem, mes calendario actual vs mes calendario anterior.
- `activeWorkflows.value` = `COUNT(DISTINCT workflow_id)` con ≥1 doc en `status IN ('UPLOADED','PROCESSING','EXTRACTED')` cuyo `created_at >= start_of_current_calendar_month`.
- `activeWorkflows.deltaPct` = vs mes calendario anterior.
- `processingQueue.value` = `COUNT` WHERE `status IN ('UPLOADED','PROCESSING')` AHORA.
- `processingQueue.deltaSinceLastHour` = `value - count_de_hace_1h`. Requiere snapshot (ver §"Snapshots opcionales"). Si no hay snapshot → `null`.

`throughput` (bucket mensual):
```sql
SELECT date_trunc('month', created_at) AS bucket, COUNT(*) AS total
FROM workflow_documents
WHERE tenant_id = :tenant_id
  AND created_at >= now() - interval ':months months'
  AND status = 'EXTRACTED'
GROUP BY bucket ORDER BY bucket ASC;
```
Backend rellena meses sin actividad con `total: 0` para mantener la serie continua.

`recentDocuments`:
- ORDER BY `updated_at DESC`, LIMIT `recentLimit`.
- `pageCount`: TBD — `workflow_documents` no tiene un campo `page_count` hoy. Opciones: (a) derivar de `len(extraction_pages)` (ya existe la columna), (b) calcular en OCR y persistir en `extraction_metadata`, (c) devolver `null` en v1. Decisión sugerida: (a) si `extraction_pages` está poblado, sino `null`.
- `status` se serializa tal cual del enum `WorkflowDocumentStatus`. Frontend mapea a etiqueta (`EXTRACTED → "Completed"`, etc.).

---

### 2. `GET /v1/dashboard/processing`

Toda la data del tab Processing en una respuesta.

**Query params:**
- `liveLimit` (int, default `5`, máx `20`).

**Response:**
```json
{
  "data": {
    "summary": {
      "inQueue": 45,
      "processing": 12,
      "completedToday": 234,
      "failed": 8,
      "avgProcessingSeconds": 192
    },
    "stages": [
      { "stage": "UPLOAD",     "label": "Upload",     "count": 15 },
      { "stage": "OCR",        "label": "OCR",        "count": 8 },
      { "stage": "EXTRACTION", "label": "Extraction", "count": 12 },
      { "stage": "VALIDATION", "label": "Validation", "count": 7 },
      { "stage": "COMPLETE",   "label": "Complete",   "count": 234 }
    ],
    "liveProcessing": [
      {
        "uuid": "doc-uuid",
        "name": "Invoice_2024_456.pdf",
        "stage": "EXTRACTION",
        "progressPct": 70,
        "etaSeconds": 120,
        "startedAt": "2026-05-19T11:55:00Z"
      }
    ]
  },
  "datetime": "2026-05-19T12:00:00Z"
}
```

**Queries (todas sobre `workflow_documents`, filtradas por tenant):**

`summary`:
- `inQueue` = `COUNT` WHERE `status = 'UPLOADED'`.
- `processing` = `COUNT` WHERE `status = 'PROCESSING'`.
- `completedToday` = `COUNT` WHERE `status = 'EXTRACTED'` AND `updated_at >= today_start_tenant_tz`.
- `failed` = `COUNT` WHERE `status = 'ERROR'`.
- `avgProcessingSeconds` = `AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))` WHERE `status='EXTRACTED'` y completado hoy. Frontend formatea (`192s → "3.2m"`).

`stages` — mapeo enum → stage del dashboard:
- `WorkflowDocumentStatus.UPLOADED` → `UPLOAD`.
- `WorkflowDocumentStatus.PROCESSING` + `processing_status` indica OCR → `OCR`.
- `WorkflowDocumentStatus.PROCESSING` + `processing_status` indica extracción → `EXTRACTION`.
- `WorkflowDocumentStatus.PROCESSING` + `processing_status` indica validación → `VALIDATION`.
- `WorkflowDocumentStatus.EXTRACTED` → `COMPLETE`.

> **Nota:** `workflow_documents.processing_status` ya existe (String(20), nullable). Las activities Temporal (`mark_document_status.py`, `persist_classified_documents.py`) escriben los valores del enum `DocumentStatus` (lowercase): `"pending"`, `"extracting"`, `"validating"`, `"completed"`, `"failed"`. El SQL repo reconoce `"extracting"` → EXTRACTION y `"validating"` → VALIDATION. `"pending"` y otros valores no reconocidos caen al fallback PROCESSING. No hay paso OCR en el pipeline v1; el bucket OCR queda reservado para futuro (cualquier worker que escriba `"ocr"` poblaría esa etapa automáticamente).

`liveProcessing`:
- Filtra `status = 'PROCESSING'`, ORDER BY `created_at ASC`, LIMIT `liveLimit`.
- `stage` = mismo mapeo que `stages`. Si v1 (sin `processing_status`) colapsa la etapa a `PROCESSING`, también se reporta así en `liveProcessing`.
- `progressPct`: heurística por etapa (`UPLOAD: 10%, OCR: 40%, EXTRACTION: 70%, VALIDATION: 90%`). **Fallback v1** (cuando `stage = "PROCESSING"` por ausencia de `processing_status`): `50%`. Si en el futuro hay un campo `progress` lineal, usar ese.
- `etaSeconds`: `avg_processing_seconds_global - elapsed_seconds`. Si negativo → `null` (frontend muestra "—").

---

> **Nota — Failed Documents removido del UI.** El bloque "Failed Documents" del tab Processing fue eliminado del frontend. El stat card de "Failed" (count agregado) sigue cubierto por `summary.failed`. Si en el futuro vuelve a aparecer una lista de docs fallidos, agregar entonces un endpoint `GET /v1/dashboard/processing/failed` separado (no contaminar el endpoint principal — la lista necesita paginación).

## Estructura de archivos backend

```
backend/src/dashboard/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── overview.py                 # OverviewData con summary / throughput / recentDocuments
│   │   └── processing.py               # ProcessingData con summary / stages / liveProcessing
│   ├── events/
│   │   ├── __init__.py
│   │   └── dashboard_event.py          # DashboardEvent + channel_for_dashboard()
│   └── repositories/
│       ├── __init__.py
│       └── dashboard_metrics.py        # interfaz abstracta
├── application/
│   └── use_cases/
│       ├── __init__.py
│       ├── get_overview.py             # compone summary + throughput + recent en paralelo
│       └── get_processing.py           # compone summary + stages + live en paralelo
├── infrastructure/
│   └── repositories/
│       └── sql_dashboard_metrics.py    # implementación con SQLAlchemy
└── presentation/
    ├── __init__.py
    ├── router.py                        # add_api_route(...) para los 3 endpoints (2 REST + 1 SSE)
    ├── endpoints/
    │   ├── __init__.py
    │   ├── get_overview.py
    │   ├── get_processing.py
    │   └── stream_dashboard_events.py  # SSE
    └── presenters/
        ├── __init__.py
        └── dashboard.py                 # presenters domain → dict (snake_case; el middleware convierte a camelCase)
```

**Otros archivos backend a tocar** (no en `src/dashboard/` — son fan-outs en activities/use cases existentes):

- `backend/src/workflows/presentation/workflows/activities/update_document_set_status.py` — publicar `DashboardEvent("DOCUMENT_COMPLETED" | "DOCUMENT_FAILED")` después del commit.
- Activity de pipeline que actualiza `processing_status` (si existe; si no, crear o instrumentar dentro de los activities relevantes) — publicar `DashboardEvent("DOCUMENT_STATUS_CHANGED")`.
- Use case que crea `workflow_document` (single drop-zone) — publicar `DashboardEvent("DOCUMENT_CREATED")`.

**Nota de implementación:** cada use case REST (`GetOverview`, `GetProcessing`) ejecuta sus sub-queries (3 cada uno) en paralelo con `asyncio.gather(...)` para que la latencia sea `max(t1, t2, t3)` y no la suma.

Registrar `dashboard_router` en `config/main.py` con prefix `/v1/dashboard`.

## Frontend — cambios necesarios

```
frontend/src/
├── domain/
│   ├── entities/dashboard/             # nuevas entidades TS (Overview, Processing)
│   └── repositories/dashboard.ts       # interfaz con getOverview() / getProcessing()
├── infrastructure/repositories/
│   └── http-dashboard.ts                # impl HTTP
├── application/hooks/
│   ├── queries/dashboard.ts             # useDashboardOverview() / useDashboardProcessing()
│   └── use-dashboard-events.ts          # SSE subscription → invalidate queries
└── presentation/dashboard/
    ├── overview-chart.tsx               # recibe throughput[] vía prop
    ├── recent-documents.tsx             # recibe recentDocuments[] vía prop
    └── processing-tab.tsx               # consume useDashboardProcessing()
```

`page.tsx` invoca:
- `useDashboardEvents()` una sola vez (mount-time) — abre la conexión SSE y se encarga de invalidar el cache cuando llegan eventos.
- `useDashboardOverview()` para el tab Overview y pasa `summary`, `throughput`, `recentDocuments` a los componentes hijos como props.
- `useDashboardProcessing()` para el tab Processing.

Esto evita que cada subcomponente tenga su propio query y mantiene un único loading state coherente por tab.

## Refresh — SSE + eventos de dominio

El dashboard se actualiza **push** vía SSE. El proyecto ya tiene la infra completa (`stream_sse`, `RedisEventPublisher`, `subscribeSSE`) — ver skill `sse-endpoints` y `product/plans/sse-events/sse-events.md`.

**Patrón:** SSE NO entrega los datos del dashboard, solo señales "algo cambió". El frontend usa cada señal para **invalidar** el cache de TanStack Query y refetchea el REST (`/v1/dashboard/overview` o `/v1/dashboard/processing`). Esto mantiene:
- REST stateless (cacheable, paginable, debuggable con curl).
- SSE como bus de invalidación ligero (payloads pequeños, sin lógica de presentación).
- Eventos de dominio como única fuente de verdad: las mismas transiciones que mutan `workflow_documents` ya publican eventos en el pipeline existente; agregamos un fan-out tenant-scoped.

### Canal y eventos

```python
# backend/src/dashboard/domain/events/dashboard_event.py
from typing import Literal
from uuid import UUID
from src.common.domain.events.base import Event

DashboardEventType = Literal[
    "DOCUMENT_CREATED",     # un workflow_document nuevo
    "DOCUMENT_STATUS_CHANGED",  # cualquier transición de status
    "DOCUMENT_FAILED",      # transición a ERROR (también dispara STATUS_CHANGED)
    "DOCUMENT_COMPLETED",   # transición a EXTRACTED (también dispara STATUS_CHANGED)
]

# Canal tenant-wide. Ownership se enforza en el endpoint (no en el canal).
def channel_for_dashboard(tenant_id: UUID) -> str:
    return f"tenant:{tenant_id.hex}:dashboard:events"


class DashboardEvent(Event):
    type: DashboardEventType
    tenant_id: UUID
    # Hint para refetch selectivo en el frontend
    affects: list[Literal["overview", "processing"]]

    @property
    def channel(self) -> str:
        return channel_for_dashboard(self.tenant_id)
```

**Payload mínimo** — solo lo necesario para que el frontend decida qué refetchear:

```json
{
  "seq": 1716124800123,
  "ts": "2026-05-19T12:00:00Z",
  "type": "DOCUMENT_STATUS_CHANGED",
  "tenant_id": "...",
  "affects": ["overview", "processing"],
  "payload": {
    "documentId": "...",
    "fromStatus": "PROCESSING",
    "toStatus": "EXTRACTED"
  }
}
```

### Mapeo evento de dominio → DashboardEvent

Los publishers existentes ya emiten eventos en cada transición de `workflow_documents`. En lugar de duplicar publicaciones en cada use case, **fan-out en una sola capa**: agregamos una publicación adicional al `DashboardEvent` canal junto al evento de dominio original.

| Use case existente | Evento de dominio actual (`DocumentSetEventType`) | DashboardEvent a publicar |
|---|---|---|
| Crear `workflow_document` (single drop-zone) | (ninguno; agregar) | `DOCUMENT_CREATED` |
| Activity `update_document_set_status` cuando completa un doc | el `DocumentSetEventType` que indica doc completado (verificar el valor exacto en `common/domain/enums/document_set_events.py`) | `DOCUMENT_COMPLETED` |
| Activity de pipeline cuando un doc falla | el `DocumentSetEventType` que indica doc fallido | `DOCUMENT_FAILED` |
| Activity que actualiza `processing_status` (OCR/EXTRACTION/VALIDATION) | (ninguno; agregar) | `DOCUMENT_STATUS_CHANGED` con `affects: ["processing"]` |

> **Implementación:** verificar los valores exactos de `DocumentSetEventType` antes de hacer el match. `DocumentSetEvent` (la clase) ya carga `document_id` opcional en su payload — perfecto para alimentar el `payload.documentId` del `DashboardEvent`.

**Regla:** cada vez que un activity Temporal toca `workflow_documents.status` o `processing_status`, publica el `DashboardEvent` correspondiente **después del commit**. La publicación es fire-and-forget (los warnings se loguean, no rompen el pipeline).

`affects: ["overview", "processing"]` permite optimizar:
- `DOCUMENT_CREATED` → afecta ambos (Overview `recentDocuments` + Processing `inQueue`).
- Cambios de `processing_status` (sub-stage) → solo `["processing"]` (Overview no lo necesita).
- `DOCUMENT_COMPLETED` → ambos.

### Endpoint SSE

```
GET /v1/dashboard/events
```

Implementación (siguiendo el patrón del skill `sse-endpoints` al pie de la letra):

```python
async def stream_dashboard_events(
    request: Request,
    redis_client: RedisClientDep,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> EventSourceResponse:
    check_tenant_permission(current_tenant_user, permissions=[DashboardPermission.view])
    return stream_sse(
        channel=channel_for_dashboard(current_tenant_user.tenant.uuid),
        redis_client=redis_client,
        request=request,
        # Sin close_after — stream open-ended mientras el tab esté abierto.
        # Sin replay — el dashboard es "fire-and-forget"; al reconectar,
        # el frontend invalida queries y refetchea el estado actual.
    )
```

Ownership: el tenant del usuario autenticado es el único canal al que puede suscribirse — no hay riesgo de cross-tenant leak. No hay parámetros, no hay `since_seq`.

### Frontend hook

```ts
// frontend/src/application/hooks/use-dashboard-events.ts
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { subscribeSSE } from "@/src/infrastructure/http/sse";

export function useDashboardEvents() {
  const qc = useQueryClient();

  useEffect(() => {
    // URL relativa — la API se accede vía el proxy de Next, igual que otros hooks SSE del proyecto
    // (ver use-document-set-events.ts, use-doctype-events.ts).
    return subscribeSSE("/api/v1/dashboard/events", {
      onEvent: ({ type, data }) => {
        if (type === "ready" || type === "heartbeat") return;
        const event = JSON.parse(data);
        const affects: string[] = event.affects ?? ["overview", "processing"];
        for (const section of affects) {
          qc.invalidateQueries({ queryKey: ["dashboard", section] });
        }
      },
    });
  }, [qc]);
}
```

Se monta una sola vez en `page.tsx` del dashboard. Cuando llega un evento, TanStack invalida la query correspondiente → React Query refetchea automáticamente.

### Estrategia de cache en el frontend

```ts
useQuery({
  queryKey: ["dashboard", "overview", { throughputMonths, recentLimit }],
  queryFn: () => repo.getOverview({ throughputMonths, recentLimit }),
  staleTime: 30_000, // fallback si SSE se cae
});

useQuery({
  queryKey: ["dashboard", "processing", { liveLimit }],
  queryFn: () => repo.getProcessing({ liveLimit }),
  staleTime: 10_000, // fallback si SSE se cae
});
```

- **SSE conectado**: invalidación push instantánea, `staleTime` no se usa.
- **SSE caído** (red intermitente, reconectando): el `staleTime` actúa como fallback — al hacer cualquier interacción, refetchea.
- No usar `refetchInterval` — la fuente de verdad es SSE.

### Por qué este diseño y no polling 5s

| Aspecto | Polling 5s | SSE + eventos |
|---|---|---|
| Latencia de actualización | hasta 5s | <100ms tras la transición |
| Requests/min por usuario | 12 | 0 (en idle) |
| Carga DB | constante | proporcional a actividad real |
| Complejidad backend | trivial | ya existe la infra (reuso 100%) |
| Trabajo nuevo | hooks + interval | DashboardEvent + 4 puntos de publish + endpoint + hook |

El "trabajo nuevo" del lado SSE es contenido: el endpoint es ~15 líneas, el hook ~20, y las publicaciones se piggyback en los activities que ya escriben `workflow_documents`.

## Snapshots opcionales (para `deltaSinceLastHour`)

`processingQueue.deltaSinceLastHour` requiere comparar el estado actual con el de hace una hora. Dos opciones:

**Opción A — On-the-fly (no recomendada):** ejecutar queries con `created_at < now() - 1h AND status_change_at > now() - 1h` y joins complejos. Caro.

**Opción B — Snapshot table (recomendada):**
- Nueva tabla `dashboard_metric_snapshots` (`tenant_id`, `taken_at`, `metric_key`, `value INTEGER`).
- Job Temporal cron cada 15 min que escribe los snapshots por tenant.
- El endpoint lee el snapshot más cercano a `now() - 1h` y resta.

Si la opción B es muy invasiva para v1, **devolver `deltaSinceLastHour: null`** y el frontend oculta el subtexto. Documentar como TODO.

## Performance & escalabilidad

- Crear índice compuesto `(tenant_id, status, created_at)` en `workflow_documents`. El índice existente `ix_wf_docs_workflow_status` cubre `(workflow_id, status)` — sirve para queries por workflow pero **NO** cubre el patrón tenant-scoped del dashboard. El índice nuevo es requerido.
- Todas las queries deben filtrar por `tenant_id` PRIMERO (row-level scoping). El `get_required_tenant_user` dependency ya provee el `tenant_id`.
- Para tenants grandes (>1M docs), las queries de `totalDocuments` y `throughput` pueden tardar. Considerar **materialized view** refrescada cada 5 min para esos números.
- `liveProcessing` está naturalmente acotado por `liveLimit` (≤20).

## Trade-offs y caveats

- **Pipeline stages exactos requieren `processing_status` poblado.** Si los workers Temporal no lo están escribiendo, v1 colapsa a 3 etapas. Trabajo paralelo: instrumentar los workers para escribir `OCR`/`EXTRACTION`/`VALIDATION` en cada transición. Ver `src/workflows/`.
- **`avgProcessingSeconds` con base "today"** puede dar pocos datos en horarios tempranos. Alternativa: rolling 24h. Decisión inicial: today, revisar si UX se queja.
- **Throughput 12 meses** puede mostrar gaps si el tenant es nuevo. Frontend muestra 0 en barras vacías — diseño OK.
- **Permission scope**: `dashboard.view` por ahora es binario. Si en el futuro se quiere separar Overview vs Processing (ej. solo ops ve Processing), agregar `dashboard.view.processing` y refactorizar.

## Verificación

1. Login con un tenant que tenga ≥10 `workflow_documents` mezclando estados.
2. `GET /v1/dashboard/overview?throughputMonths=6&recentLimit=5` → respuesta única con `summary` (4 stats), `throughput` (6 buckets) y `recentDocuments` (5 items).
3. `GET /v1/dashboard/processing?liveLimit=5` → respuesta única con `summary` (5 stats), `stages` (≥3 elementos) y `liveProcessing` (≤5).
4. Sanity check: `summary.inQueue + summary.processing + summary.failed + summary.completedToday` aproxima al COUNT total del tenant en últimas 24h.
5. `GET /v1/dashboard/events` con `Accept: text/event-stream` (vía `curl --no-buffer ...`) → primer frame `event: ready`, heartbeat cada 15s.
6. Crear un documento → en <1s llega `DOCUMENT_CREATED` por SSE → frontend invalida queries → `recentDocuments` actualiza en pantalla.
7. Forzar un error en extracción → llega `DOCUMENT_FAILED` → `summary.failed` incrementa al instante.
8. Cerrar la pestaña del browser → conexión SSE se cierra (verificar en logs del backend).
9. Apagar Redis temporalmente → la suscripción Redis falla → `stream_sse` cierra la conexión → `subscribeSSE` reintenta con backoff exponencial. Mientras Redis esté caído, no llegan eventos y los datos quedan stale; cualquier interacción del usuario triggerea el refetch del REST gracias al `staleTime`.

## Manifiesto de archivos

**Backend — crear:**
- `backend/src/dashboard/**` (~12 archivos según árbol arriba, incluyendo `domain/events/dashboard_event.py` y `presentation/endpoints/stream_dashboard_events.py`).

**Backend — modificar:**
- `backend/config/main.py` — registrar `dashboard_router`.
- `backend/src/workflows/presentation/workflows/activities/update_document_set_status.py` — publicar `DashboardEvent("DOCUMENT_COMPLETED" | "DOCUMENT_FAILED")` después del commit.
- Activity/use case que actualiza `processing_status` — publicar `DashboardEvent("DOCUMENT_STATUS_CHANGED")` con `affects: ["processing"]`.
- Use case que crea `workflow_document` desde single drop-zone — publicar `DashboardEvent("DOCUMENT_CREATED")`.
- (Opcional) `backend/src/common/database/migrations/...` — snapshot table si se elige opción B para `deltaSinceLastHour`.

**Frontend — crear:**
- `frontend/src/domain/entities/dashboard/**`.
- `frontend/src/domain/repositories/dashboard.ts`.
- `frontend/src/infrastructure/repositories/http-dashboard.ts`.
- `frontend/src/application/hooks/queries/dashboard.ts` (2 hooks: `useDashboardOverview`, `useDashboardProcessing`).
- `frontend/src/application/hooks/use-dashboard-events.ts` (SSE → invalidate cache).

**Frontend — modificar:**
- `frontend/src/app/(protected)/dashboard/page.tsx` — orquestar los 2 hooks REST + 1 hook SSE.
- `frontend/src/presentation/dashboard/overview-chart.tsx` — recibir data por props.
- `frontend/src/presentation/dashboard/recent-documents.tsx` — recibir data por props.
- `frontend/src/presentation/dashboard/processing-tab.tsx` — consumir hook.
