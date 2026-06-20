---
feature: sse-events
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
---

# SSE Events (Server-Sent Events)

Spec unificado para Doxiq. Combina las fortalezas del patrón Tripto (canal por tenant, publisher singleton inyectado, `EventSourceResponse` estándar, contrato simple "señal + refetch") con las nuestras (eventos auto-descritos con `seq`/`ts`, replay desde Postgres, heartbeats, `ready`, cliente SSE robusto con state machine).

> Este spec sustituye a `sse-events-extern.md` (referencia de Tripto, mantener solo como histórico).

---

## 1. Visión general

```
[Use case / Temporal activity / Background task]
   │  event_publisher.publish(event)            ← event.channel + event.model_dump_json()
   ▼
[Redis Pub/Sub]
   │  channel = "<scope>:<id>:<topic>:events"
   ▼
[FastAPI endpoint /v1/<resource>/events]
   │  (1) ownership check  (2) opcional replay desde Postgres por `since_seq`
   │  (3) async generator → frames `event: <type>` + `data: <json>`
   │  (4) heartbeats periódicos + `ready` inicial
   ▼
[Frontend  subscribeSSE]   fetch + ReadableStream → state machine + watchdog + backoff
```

### Decisiones clave

- **Transporte:** Redis Pub/Sub. No persistente; los eventos perdidos se recuperan por replay (Postgres) o refetch.
- **Granularidad de canal:** *por recurso* (ej. workflow, run), no por tenant. Un canal tenant-wide hace fan-out caro y obliga a filtrar en el suscriptor. Aislamiento por tenant se garantiza con el ownership check antes de abrir el stream.
- **Convención de canal:** `"<scope>:<id>:<topic>:events"`. Ej. `workflow:{workflow_id}:rules:events`, `workflow:{workflow_id}:document_sets:events`, `analysis_run:{run_id.hex}:events`. **Nota:** hoy `analysis_run_event.py` emite `f"analysis_run:{run_id.hex}"` sin sufijo `:events` — normalizar como parte de la migración (§8).
- **Envelope rico y self-describing:** `seq`, `ts`, `type`, `payload`, + ids contextuales. El `Event` expone su propio `channel` → el publisher es agnóstico.
- **Response:** `EventSourceResponse` (sse-starlette) **vía un helper común** (`stream_sse(...)`) para no formatear frames a mano.
- **Auth:** JWT (`Authorization: Bearer …`) + header `X-Tenant`. No se usa `EventSource` nativo (no soporta headers).
- **Garantías:** at-most-once en el bus + at-least-once por replay (donde aplica). El cliente debe ser idempotente vs. eventos duplicados (`seq` permite dedupe).

---

## 2. Componentes en el código

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Domain | `src/common/domain/events/base.py` | Clase base `Event` (`seq`, `ts`, `type`, `payload`, prop. `channel`). |
| Domain | `src/<module>/domain/events/<resource>_event.py` | Subclase concreta + helper `channel_for_<resource>(...)`. |
| Infra (común) | `src/common/infrastructure/event_publisher.py` | Protocolo `EventPublisher` + `RedisEventPublisher` (publica en `event.channel`). |
| Infra (común) | `src/common/infrastructure/sse/streaming.py` | Helper `stream_sse(channel, replay=…, heartbeat_s=15)` que emite `ready`, replay, live, heartbeats. |
| Infra (DI) | `src/common/infrastructure/dependencies/common.py` | `RedisClientDep` (existe). `EventPublisherDep` (a añadir, ver §3.3). |
| Application | `src/<module>/application/.../use_case.py` | Llama `event_publisher.publish(event)` después del commit. |
| Presentation | `src/<module>/presentation/endpoints/<resource>_events.py` | Endpoint thin: ownership check → `return stream_sse(...)`. |
| Presentation | `src/<module>/presentation/router.py` | Registra ruta con `response_class=EventSourceResponse`. |
| Frontend | `frontend/src/infrastructure/http/sse.ts` | `subscribeSSE` con state machine, backoff, watchdog. |
| Frontend | `frontend/src/application/hooks/use-<resource>-events.ts` | Hook por dominio que consume `subscribeSSE`. |

---

## 3. Backend — generación de eventos

### 3.1 Base `Event`

`src/common/domain/events/base.py` (ya existe en el repo — tal cual):

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """Generic envelope. Concrete subclasses set `channel` and add fields."""

    seq: int                     # monotónico por recurso (ms epoch o secuencia DB)
    ts: datetime
    payload: dict                # requerido; usa {} explícito si no hay datos

    model_config = ConfigDict(extra="forbid")

    @property
    def channel(self) -> str:    # cada subclase la implementa
        raise NotImplementedError("Event subclasses must override the `channel` property")
```

> **Nota deliberada:** la base **no** declara `type`. Cada subclase lo añade como `Literal[...]` para que el chequeo de tipos sea estricto y el wire format incluya el discriminador correcto. `extra="forbid"` evita campos rebeldes en el envelope.

### 3.2 Subclase concreta

`src/workflows/domain/events/analysis_rule_event.py`

```python
AnalysisRuleEventType = Literal[
    "REPARSE_STARTED", "REPARSE_COMPLETED", "REPARSE_FAILED", "HEARTBEAT",
]


def channel_for_workflow_rules(workflow_id: UUID) -> str:
    return f"workflow:{workflow_id}:rules:events"


class AnalysisRuleEvent(Event):
    type: AnalysisRuleEventType
    workflow_id: UUID
    rule_id: UUID

    @property
    def channel(self) -> str:
        return channel_for_workflow_rules(self.workflow_id)
```

> **Convención:** el helper `channel_for_X(...)` vive junto al evento. **Nunca** se construye el string del canal en otro lugar.

### 3.3 Publisher (singleton)

`src/common/infrastructure/event_publisher.py`

```python
@dataclass
class RedisEventPublisher:
    redis: Redis

    async def publish(self, event: Event) -> None:
        try:
            await self.redis.publish(event.channel, event.model_dump_json())
            logger.debug("sse.event.published", channel=event.channel, seq=event.seq)
        except Exception:
            logger.warning("sse.event.publish_failed", channel=event.channel, exc_info=True)
```

Inyección:

```python
@lru_cache(maxsize=1)
def get_event_publisher() -> EventPublisher:
    # NB: el cliente del publisher es separado del cliente del subscriber
    # (`app.state.redis_client`) para no compartir el mismo socket entre
    # publish y pubsub.subscribe — Redis recomienda conexiones distintas.
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    return RedisEventPublisher(redis=redis)


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]
```

> El singleton se reutiliza en HTTP requests, background tasks **y workers Temporal** — evita abrir conexiones Redis nuevas por cada publicación.
>
> Nunca capturar `RedisEventPublisher.publish` dentro de una transacción crítica: errores se loggean como warning y **no** rompen el use case.

### 3.4 Cuándo publicar

- **Después** de `await session.commit()`. Publicar antes notifica algo que aún no es visible para queries.
- **Una sola vez** por mutación (idempotente). Si la mutación ya publicó, no republicar en handlers superiores.
- Eventos pequeños: `payload` solo lleva lo mínimo para que el cliente decida qué refetch hacer (ids, status, seq). No metas blobs grandes.

### 3.5 Numeración `seq` y replay

- Para streams **transitorios** (rules, runs): `seq = int(time.time() * 1000)` es suficiente (no hay replay, solo dedupe en cliente si reconecta rápido).
- Para streams **con replay** (document sets): `seq` es la columna autoincremental de la tabla de eventos persistidos en Postgres. Ej. `workflow_document_set_events.seq` (BIGINT, monotónico por workflow). El replayer lee `WHERE seq > since_seq ORDER BY seq`.

---

## 4. Backend — endpoint SSE

### 4.1 Helper común

> **Prerrequisito:** añadir `sse-starlette` a `backend/pyproject.toml` (hoy no está). Si por algún motivo no se quiere la dependencia, fallback a `StreamingResponse` con el mismo helper — el contrato externo no cambia.

`src/common/infrastructure/sse/streaming.py`

```python
import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import Request
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

ReplayFn = Callable[[], AsyncIterator[dict[str, Any]]]
FilterFn = Callable[[dict[str, Any]], bool]


async def _frames(
    pubsub: PubSub,
    request: Request,
    *,
    replay: ReplayFn | None,
    filter_fn: FilterFn | None,
    heartbeat_s: float,
) -> AsyncIterator[ServerSentEvent]:
    yield ServerSentEvent(event="ready", data="{}")

    replayed_seqs: set[int] = set()
    if replay is not None:
        async for ev in replay():
            replayed_seqs.add(ev["seq"])
            yield ServerSentEvent(event=ev.get("type", "message"), data=json.dumps(ev))

    while True:
        if await request.is_disconnected():
            return
        # `get_message(timeout=X)` retorna None al expirar; no hace falta wait_for.
        msg = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=heartbeat_s
        )
        if msg is None:
            yield ServerSentEvent(event="heartbeat", data="{}")
            continue
        raw = msg["data"]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if ev.get("seq") in replayed_seqs:
            continue
        if filter_fn is not None and not filter_fn(ev):
            continue
        yield ServerSentEvent(event=ev.get("type", "message"), data=raw)


def stream_sse(
    *,
    channel: str,
    redis_client: Redis,
    request: Request,
    replay: ReplayFn | None = None,
    filter_fn: FilterFn | None = None,
    heartbeat_s: float = 15.0,
) -> EventSourceResponse:
    async def gen() -> AsyncIterator[ServerSentEvent]:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for frame in _frames(
                pubsub,
                request,
                replay=replay,
                filter_fn=filter_fn,
                heartbeat_s=heartbeat_s,
            ):
                yield frame
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return EventSourceResponse(
        gen(),
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx: no buffer
        },
    )
```

> **Por qué `EventSourceResponse` en lugar de `StreamingResponse`:** sse-starlette ya implementa el wire format (CRLF, `:` comments, `retry:`, etc.) y maneja el cierre limpio del cliente sin el bug recurrente que vemos al pollear `request.is_disconnected()` desde un loop manual (ver el comentario en `analysis_rule.py` sobre `is_disconnected()` espurio).

### 4.2 Endpoint thin

```python
async def stream_workflow_rule_events(
    workflow_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> EventSourceResponse:
    workflow = await app_context.domain.workflow_repository.find_by_id(workflow_id, tenant.uuid)
    if workflow is None:
        raise HTTPException(404, "Workflow not found")

    return stream_sse(
        channel=channel_for_workflow_rules(workflow_id),
        redis_client=redis_client,
        request=request,
    )
```

Con replay (document sets):

```python
return stream_sse(
    channel=document_set_channel(workflow_id),
    redis_client=redis_client,
    request=request,
    replay=lambda: replayer.iter_since(since_seq=since_seq, workflow_case_id=workflow_case_id),
    filter_fn=lambda ev: workflow_case_id is None or ev.get("workflow_case_id") == str(workflow_case_id),
)
```

### 4.3 Registro de la ruta

```python
workflows_router.add_api_route(
    "/{workflow_id}/analysis-rules/events",
    stream_workflow_rule_events,
    methods=["GET"],
    summary="SSE — analysis rule events for a workflow",
    response_class=EventSourceResponse,
)
```

URL final: `GET /v1/workflows/{workflow_id}/analysis-rules/events`.

### 4.4 Aislamiento por tenant

- El **ownership check** (`workflow_repository.find_by_id(workflow_id, tenant.uuid)`) debe ser la **primera** acción del endpoint y devolver 404 si no pertenece al tenant. Esto evita que un tenant se suscriba a canales de otro aunque conozca el `workflow_id`.
- No hace falta meter `tenant_id` en el nombre del canal porque el recurso (workflow / run) ya está scopeado a tenant en BD.
- Excepción: streams *tenant-wide* (notificaciones, billing) → `tenant:{tenant_id}:notifications:events`.

---

## 5. Frontend — consumo

### 5.1 Cliente central (`subscribeSSE`)

`frontend/src/infrastructure/http/sse.ts` ya implementa:

- `fetch` + `ReadableStream` (no `EventSource` nativo: necesitamos headers).
- State machine: `idle` → `connecting` → `connected` → `reconnecting`.
- Backoff exponencial (`base 2s`, `max 30s`).
- **Watchdog**: si no llegan bytes en `connectionWatchdogMs` (default 50s, ≥ 2× heartbeat), fuerza reconexión.
- `AbortSignal` para cancelar al desmontar el componente o cambiar de tenant.
- `urlOrFactory`: si pasas función, se recomputa la URL en cada reconexión (útil para `since_seq` actualizado).

### 5.2 Hook por dominio

```ts
useEffect(() => {
  let lastSeq = 0;
  return subscribeSSE(
    () => `${API}/v1/workflows/${workflowId}/document-sets/events?since_seq=${lastSeq}`,
    {
      onEvent: ({ type, data }) => {
        const ev = JSON.parse(data) as DocumentSetEventEnvelope;
        if (ev.seq) lastSeq = Math.max(lastSeq, ev.seq);
        dispatch(ev);
      },
      onStateChange: setConnState,
      reconnectBaseDelay: 2000,
      connectionWatchdogMs: 35000,
    },
  );
}, [workflowId]);
```

### 5.3 Patrón "señal + refetch" vs. "actualización en vivo"

- **Señal:** evento minimal (`{type, ids}`), el front invalida queries de TanStack/SWR. Usar para flujos donde la consistencia se obtiene por refetch barato.
- **Vivo:** evento con `payload` rico (status, parsed_checks, etc.), el front actualiza el store directamente. Usar cuando refetch sería costoso o crearía flicker.
- **Regla:** si dudas, empieza por señal. Solo enriquece el `payload` cuando el refetch sea medible y problemático.

### 5.4 Cambio de tenant / logout

El AbortController del `subscribeSSE` debe abortarse en:
- desmontaje del componente,
- cambio de `tenantId`,
- logout / refresh de token.

---

## 6. Checklist para añadir un nuevo stream

### Backend
- [ ] Subclase de `Event` con `Literal` en `type`, ids contextuales y `channel` self-describing.
- [ ] Helper `channel_for_<resource>(...)` co-ubicado con el evento.
- [ ] Publicación **post-commit** en el use case usando `EventPublisherDep`.
- [ ] (Si aplica) tabla Postgres `<resource>_events` con `seq BIGINT` autoincremental por scope, índice `(scope_id, seq)`, retention policy.
- [ ] Endpoint thin: ownership check → `return stream_sse(...)`.
- [ ] Registro con `response_class=EventSourceResponse`.
- [ ] Test: integración que publique y consuma 1 evento; test de heartbeat; test de ownership 404.

### Frontend
- [ ] Tipos del envelope en `domain/events/<resource>-event.ts` (mirror del backend, camelCase).
- [ ] Hook `use-<resource>-events.ts` con `urlOrFactory` + `since_seq` si hay replay.
- [ ] Reducer / dispatcher idempotente vs. `seq` duplicado.
- [ ] Cancelación al desmontar / cambiar tenant.

---

## 7. Operación y troubleshooting

- **Logs:**
  - Backend: `sse.event.published` (debug), `sse.event.publish_failed` (warning), `sse.stream.opened` / `closed` (info).
  - Frontend: `onStateChange` → loggear transiciones a Sentry.
- **Health:** `/health` valida Redis. Si está degradado los SSE no llegan pero el resto de la API sigue.
- **Pruebas locales:**
  ```bash
  redis-cli PUBLISH "workflow:<wf_uuid>:rules:events" \
    '{"seq":1714000000000,"ts":"2026-05-03T12:00:00Z","type":"REPARSE_STARTED","workflow_id":"…","rule_id":"…","payload":{}}'
  ```
- **Anti-patrón:** lógica de negocio en el handler SSE. El handler **solo** suscribe, replay, filtra, reenvía. Toda la lógica vive en use cases que publican.
- **Anti-patrón:** instanciar `RedisEventPublisher(redis=Redis.from_url(...))` en cada background task. Usa `get_event_publisher()`.

---

## 8. Migración desde el estado actual

Doxiq hoy tiene 3 streams escritos con 3 estilos distintos:

| Stream | Endpoint actual | Cambia a |
|---|---|---|
| `stream_workflow_rule_events` | `StreamingResponse` + `pubsub.listen()` con `wait_for(listener.__anext__(), heartbeat)` | `stream_sse(channel=…)` |
| `stream_analysis_run_events` | `StreamingResponse` + `pubsub.get_message(timeout)` | `stream_sse(channel=…)` |
| `stream_document_set_events` | `StreamingResponse` + `DocumentSetEventReplayer` + filter inline | `stream_sse(channel=…, replay=…, filter_fn=…)` |

Adicionalmente:
- `analysis_run_event.channel_for_run` → renombrar el output a `f"analysis_run:{run_id.hex}:events"` para alinear con la convención `…:events`. Cambio coordinado backend + hook frontend.
- `parser_scheduler.run_parser_in_background` deja de instanciar `Redis.from_url(...)` + `RedisEventPublisher(...)`; en su lugar recibe el publisher singleton (pasado por argumento desde el endpoint, igual que ya hace con `database_config`).

Pasos:
1. Añadir `sse-starlette` al `pyproject.toml` (no está hoy).
2. Añadir `src/common/infrastructure/sse/streaming.py` (helper). El base `Event` ya existe en `src/common/domain/events/base.py`.
3. Añadir `get_event_publisher()` singleton en `dependencies/common.py` y `EventPublisherDep`.
4. Refactor `parser_scheduler.py` y demás call-sites para usar el publisher singleton en lugar de instanciar `RedisEventPublisher(redis=Redis.from_url(...))` por task.
5. Renombrar canal de `analysis_run` para añadir sufijo `:events`.
6. Sustituir cada endpoint por la versión thin con `stream_sse`.
7. Frontend: `subscribeSSE` ya cubre el contrato. Verificar que cada hook (`use-analysis-rule-events`, `use-document-set-events`, equivalente para runs) parsee el envelope con `seq`/`ts` y aplique dedupe.

---

## 9. Recomendaciones adicionales (más allá del unify)

Pensadas para llevar el spec a "production-grade".

### 9.1 Persistencia de eventos universal
Hoy solo `document_sets` tiene replay. Considerar tabla genérica `domain_events(scope, scope_id, seq, type, payload, ts)` particionada por `scope`, con TTL por tipo. Costo: una tabla más; beneficio: cualquier stream nuevo gana replay gratis.

### 9.2 Outbox pattern para garantía de entrega
Publicar a Redis dentro del `commit` no es transaccional → si Redis cae justo ahí, el evento se pierde. Patrón:
1. Use case escribe la mutación + fila en `event_outbox` en la **misma** transacción.
2. Worker lee `event_outbox` y publica a Redis (con retry y `published_at`).

Esto da at-least-once real entre BD y bus.

### 9.3 Backpressure y límite de conexiones por tenant
Cada SSE consume 1 conexión Redis (pubsub) + 1 socket HTTP. Añadir middleware que limite N streams concurrentes por tenant (default 20) y cierre el más antiguo si se excede. Métrica: `sse.connections.active{tenant=...}`.

### 9.4 Heartbeat adaptativo
15 s funciona en local; detrás de Cloudflare/ALB con `idle_timeout=60s` es ajustado. Hacer `heartbeat_s` configurable por settings (default 15) y documentar el match con el proxy en producción.

### 9.5 Compatibilidad de versión
Cuando un evento cambie de schema, **no romper consumidores viejos**:
- Solo añadir campos opcionales.
- Romper requiere bump del `type` (`document_set.completed.v2`) y endpoint nuevo.
- Documentar en `domain/events/CHANGELOG.md`.

### 9.6 Telemetría
Métricas Prometheus:
- `sse_events_published_total{channel,type}`
- `sse_events_dropped_total{reason}`  (publish failed, no subscribers)
- `sse_streams_active{endpoint}`
- `sse_stream_duration_seconds_bucket{endpoint}`
- `sse_replay_window_size{endpoint}`

Tracing: cada `publish` debe propagar `trace_id` en el envelope para correlacionar con el use case que lo emitió.

### 9.7 Tests
- **Unit:** parser de frames, dedupe por `seq`, filter_fn.
- **Integración:** levantar Redis (testcontainers) + cliente, verificar replay + live + heartbeat.
- **E2E frontend:** mock SSE server (MSW + ReadableStream) y verificar state machine + watchdog en Vitest.
- **Contract test:** snapshot del JSON envelope por cada `EventType` para detectar breaking changes.

### 9.8 Seguridad
- Rate-limit por IP/tenant en el endpoint de stream (prevenir abuso de conexiones).
- Validar tamaño del `payload` antes de publicar (`< 8 KB`).
- Nunca incluir PII innecesaria en el payload — el cliente refetch tiene auth fresca; el bus no debería ser otro lugar donde audits vivos.

### 9.9 Documentación viva
- Cada subclase de `Event` debe tener docstring con: para qué stream, qué consumidor frontend, ejemplo de `payload`.
- Generar tabla automática (`scripts/dump_sse_catalog.py`) que liste `event_type → channel → ejemplo` para que diseño/QA puedan consultar sin leer código.
