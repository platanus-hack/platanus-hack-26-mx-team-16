---
feature: sse-events
type: plan
status: obsolete
coverage: 5
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

# SSE Events (Server-Sent Events)

Guía sobre cómo está implementado el endpoint SSE del módulo `payments`, cómo se publican y consumen los eventos, y cómo replicar el patrón en otros módulos y desde el frontend.

---

## 1. Visión general

Tripto WS expone un canal **SSE multi-tenant** que permite empujar notificaciones en tiempo real al frontend cuando ocurren cambios en backend (ej. el estado de un `PaymentIntent` cambia tras un webhook de Stripe). El flujo es:

```
[Use case]
   │  event_publisher.publish(channel, SseEvent)
   ▼
[Redis PUB/SUB]   channel = "payments:sse:{tenant_id}"
   ▼
[FastAPI endpoint /v1/payments/events-stream]
   │  pubsub.subscribe(channel) → async generator → ServerSentEvent
   ▼
[Frontend]   fetch(... Accept: text/event-stream) → ReadableStream parser
```

Características clave:

- **Transporte:** Redis Pub/Sub (no streams ni listas).
- **Aislamiento por tenant:** el canal se construye con el `tenant_id` del usuario autenticado, por lo que un cliente nunca recibe eventos de otro tenant.
- **Payload:** entidad de dominio `SseEvent` serializada como JSON camelCase.
- **Autenticación:** JWT (`Authorization: Bearer …`) + header `X-Tenant: <slug>`. Por eso **no se usa `EventSource` nativo** en el frontend (no soporta headers).

---

## 2. Componentes en el código

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Domain | `src/common/domain/entities/common/sse_event.py` | Entidad `SseEvent` (payload base con `event_type` + `timestamp`). |
| Domain | `src/common/domain/services/event_publisher.py` | Interfaz abstracta `EventPublisher[TEvent]`. |
| Infra | `src/common/infrastructure/services/redis_event_publisher.py` | Implementación `RedisEventPublisher` que hace `redis.publish(channel, event.to_json)`. |
| Infra | `src/common/infrastructure/domain_builder.py` | `get_event_publisher()` (singleton vía `lru_cache`) y wiring en `build_async_domain`. |
| Module Infra | `src/payments/infrastructure/helpers/sse_channels.py` | Helper `payments_channel(tenant_id) → "payments:sse:{tenant_id}"`. |
| Application | `src/payments/application/use_cases/payment_intents/provider_persister.py` (y refunds, checkouts) | Llama a `event_publisher.publish(...)` después de mutaciones. |
| Presentation | `src/payments/presentation/endpoints/sse_events.py` | Async generator que se suscribe al canal Redis y emite `ServerSentEvent`. |
| Presentation | `src/payments/presentation/router.py` | Registra la ruta con `response_class=EventSourceResponse`. |

---

## 3. Cómo se generan los eventos

### 3.1 Entidad `SseEvent`

`src/common/domain/entities/common/sse_event.py`

```python
class SseEvent(CamelModel):
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_json(cls, raw: str) -> Self:
        return cls.model_validate_json(raw)

    @property
    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True)
```

`CamelModel` aplica `event_type` → `eventType` al serializar.

> Si necesitas más datos en el payload, **extiende** `SseEvent` (no metas todo en un dict suelto). Mantén el `event_type` como discriminador.

### 3.2 Publicación desde un use case

`src/payments/application/use_cases/payment_intents/provider_persister.py`

```python
async def _publish_transactions_event(self, tenant_id) -> None:
    await self.event_publisher.publish(
        channel=payments_channel(tenant_id),
        event=SseEvent(event_type="payment_intent.updated"),
    )
```

`event_publisher` es inyectado en el use case vía el `DomainContext` (ver `build_async_domain` en `domain_builder.py`, línea ~143).

### 3.3 Cliente Redis singleton

```python
@lru_cache(maxsize=1)
def get_event_publisher() -> EventPublisher:
    redis = Redis.from_url(settings.redis_url, decode_responses=True, encoding="utf-8")
    return RedisEventPublisher(redis_client=redis)
```

Singleton intencional: el publisher se llama tanto desde requests HTTP como desde **workers SAQ**, donde queremos reusar el mismo cliente Redis para evitar problemas de ciclo de conexión.

### 3.4 Garantías y semántica

- **At-most-once:** Redis Pub/Sub no persiste; si nadie está suscrito, el mensaje se pierde. Por diseño los eventos SSE son **señales para refrescar datos**, no la fuente de verdad.
- **Errores no propagan:** `RedisEventPublisher.publish` captura excepciones y las loggea como warning. Una falla publicando **no rompe el use case**.

---

## 4. Cómo se consumen (endpoint SSE)

### 4.1 Endpoint

`src/payments/presentation/endpoints/sse_events.py`

```python
async def payment_events_stream(
    request: Request,
    redis_client: RedisDep,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
):
    tenant_id = current_tenant_user.tenant_id
    channel = payments_channel(tenant_id)

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if await request.is_disconnected():
                break
            if message["type"] != "message":
                continue
            event = SseEvent.from_json(message["data"])
            yield ServerSentEvent(data=event.to_json, event=event.event_type)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
```

Notas:

- `RedisDep` toma el cliente del `app.state.redis_client` (ver `dependencies/rate_limit.py`).
- `get_required_tenant_user` exige JWT válido **y** header `X-Tenant`. Si falla cualquiera, el endpoint responde 401/400 antes de abrir el stream.
- El generador es asíncrono → FastAPI lo envuelve con `EventSourceResponse`.
- Cada `ServerSentEvent(data=…, event=…)` se traduce a un frame SSE:
  ```
  event: payment_intent.updated
  data: {"eventType":"payment_intent.updated","timestamp":"…"}
  ```
- Cierre limpio: si el cliente se desconecta, el generador rompe y el `finally` desuscribe y cierra el `pubsub`.

### 4.2 Registro de la ruta

`src/payments/presentation/router.py`

```python
from fastapi.sse import EventSourceResponse

payments_router = APIRouter(prefix="/payments", tags=["payments"])

payments_router.add_api_route(
    path="/events-stream",
    endpoint=payment_events_stream,
    methods=["GET"],
    summary="Payment Events Stream (SSE)",
    response_class=EventSourceResponse,
)
```

URL final: `GET /v1/payments/events-stream`.

---

## 5. Guía: implementar un endpoint SSE en otro módulo

Asumamos que queremos un stream de eventos para `messaging` (ej. nuevas conversaciones).

### Paso 1 — Definir el helper de canal

`src/messaging/infrastructure/helpers/sse_channels.py`

```python
from uuid import UUID


def messaging_channel(tenant_id: UUID) -> str:
    return f"messaging:sse:{tenant_id}"
```

> **Convención:** `<modulo>:sse:<tenant_id>`. Cada módulo posee su propio prefijo y nunca lee canales de otro módulo.

### Paso 2 — (Opcional) Especializar el evento

Si necesitas más payload, subclasea `SseEvent`:

```python
class ConversationEvent(SseEvent):
    conversation_id: UUID
```

Si solo necesitas señal "algo cambió, refresca", reusa `SseEvent` con un `event_type` específico.

### Paso 3 — Publicar desde el use case

Inyecta `event_publisher: EventPublisher` en tu use case (ya está disponible vía `DomainContext`):

```python
await self.event_publisher.publish(
    channel=messaging_channel(tenant_id),
    event=SseEvent(event_type="conversation.created"),
)
```

Llama después de la mutación, **fuera de transacciones críticas** (publicar antes de comitear puede notificar de algo que aún no es visible para queries).

### Paso 4 — Crear el endpoint

`src/messaging/presentation/endpoints/sse_events.py`

```python
from fastapi import Depends, Request
from fastapi.sse import ServerSentEvent

from src.common.domain.entities.common.sse_event import SseEvent
from src.common.domain.entities.tenants.tenant_user import TenantUser
from src.common.infrastructure.dependencies.common import RedisDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.messaging.infrastructure.helpers.sse_channels import messaging_channel


async def messaging_events_stream(
    request: Request,
    redis_client: RedisDep,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
):
    channel = messaging_channel(current_tenant_user.tenant_id)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if await request.is_disconnected():
                break
            if message["type"] != "message":
                continue
            event = SseEvent.from_json(message["data"])
            yield ServerSentEvent(data=event.to_json, event=event.event_type)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
```

### Paso 5 — Registrar la ruta

`src/messaging/presentation/router.py`

```python
from fastapi.sse import EventSourceResponse
from src.messaging.presentation.endpoints.sse_events import messaging_events_stream

messaging_router.add_api_route(
    path="/events-stream",
    endpoint=messaging_events_stream,
    methods=["GET"],
    summary="Messaging Events Stream (SSE)",
    response_class=EventSourceResponse,
)
```

### Checklist

- [ ] Canal con prefijo del módulo + `tenant_id`.
- [ ] Endpoint usa `get_required_tenant_user` para aislamiento por tenant.
- [ ] `response_class=EventSourceResponse`.
- [ ] `finally` con `unsubscribe` + `aclose` para no dejar conexiones colgadas.
- [ ] Comprobación `request.is_disconnected()` en cada iteración.
- [ ] Publicaciones tras commit de transacción.
- [ ] Eventos pequeños (señal + id), no payloads grandes — el frontend hace fetch al endpoint REST para los datos.

---

## 6. Guía: consumir SSE desde el frontend

> **Importante:** no se puede usar `EventSource` nativo del navegador, porque no permite mandar headers `Authorization` ni `X-Tenant`. En `tripto-web` consumimos SSE con `fetch` + `ReadableStream`.

Referencia: `tripto-web/src/common/infrastructure/repositories/http-sse-stream.ts`.

### 6.1 Conexión y parsing manual

```ts
const headers = {
  Authorization: `Bearer ${accessToken}`,
  'X-Tenant': tenantSlug,
  Accept: 'text/event-stream',
};

const response = await fetch(`${BACKEND}/v1/payments/events-stream`, {
  method: 'GET',
  headers,
  signal, // AbortSignal para cancelar el stream
});

if (!response.ok || !response.body) return;

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (!signal.aborted) {
  const { value, done } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true })
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n');

  let sep = buffer.indexOf('\n\n');
  while (sep !== -1) {
    const rawFrame = buffer.slice(0, sep);
    buffer = buffer.slice(sep + 2);
    handleFrame(rawFrame); // parsea las líneas `data:` y emite el evento
    sep = buffer.indexOf('\n\n');
  }
}
```

### 6.2 Parseo de un frame

Un frame SSE típico:

```
event: payment_intent.updated
data: {"eventType":"payment_intent.updated","timestamp":"2026-05-03T12:00:00Z"}

```

Las líneas `data:` se concatenan y se parsean como JSON; el resultado tiene la forma `{ eventType, timestamp, …extras }` (camelCase).

### 6.3 Patrón recomendado: SSE como invalidador

No tratar el evento como fuente de datos; al recibirlo, **invalidar/refrescar** las queries afectadas (TanStack Query, SWR, Riverpod, etc.):

```ts
onEvent(({ eventType }) => {
  if (eventType.startsWith('payment_intent.')) {
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
  }
});
```

Esto mantiene el contrato simple en backend (señal + id) y evita problemas de consistencia.

### 6.4 Reconexión

Como Redis Pub/Sub es at-most-once, en una desconexión pueden perderse eventos. Patrón sugerido:

1. Al (re)conectar, hacer un **fetch inicial** del estado actual.
2. Mantener el stream abierto con backoff exponencial al reintentar.
3. Cancelar con el `AbortSignal` cuando el componente se desmonta o el usuario cambia de tenant.

### 6.5 Cambio de tenant

El canal está atado al `tenant_id` del JWT/header en el momento de abrir el stream. Si el usuario cambia de tenant en el frontend hay que **abortar el stream actual y abrir uno nuevo**.

---

## 7. Operación y troubleshooting

- **Logs:** `RedisEventPublisher` loggea `sse.event.published` (debug) y `sse.event.publish_failed` (warning).
- **Health:** `/health` ya valida conexión Redis; si está degradada, los eventos no llegan pero el resto de la API sigue funcionando.
- **Pruebas locales:** publicar manualmente con `redis-cli`:
  ```bash
  redis-cli PUBLISH "payments:sse:<tenant_uuid>" \
    '{"eventType":"payment_intent.updated","timestamp":"2026-05-03T12:00:00Z"}'
  ```
  Cualquier cliente conectado al endpoint debe recibir el frame.
- **Anti-patrón:** no metas lógica de negocio en el handler SSE — solo suscribe, traduce y reenvía. Toda la lógica vive en use cases que publican.
