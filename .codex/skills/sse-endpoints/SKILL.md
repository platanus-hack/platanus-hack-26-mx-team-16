---
name: sse-endpoints
description: >
  Implement Server-Sent Events (SSE) endpoints in the Doxiq backend following the project's
  unified pattern: domain Event subclass + channel helper + publisher singleton + thin endpoint
  via stream_sse helper. Use when the user asks to "add an SSE endpoint", "stream events",
  "publish to frontend in real time", "create events stream", "add live updates", or references
  Server-Sent Events / EventSource / Redis Pub/Sub for live updates. Covers the full stack:
  the domain event, where to publish, how to wire the endpoint, the frontend hook that consumes
  it, and the critical tests to write.
---

# SSE Endpoints — Doxiq Backend

The full implementation guide lives in [`product/plans/sse-events/sse-events.md`](../../../product/plans/sse-events/sse-events.md). This skill is the actionable checklist for adding a **new** SSE endpoint without re-reading the spec each time.

---

## When this skill kicks in

Trigger if the user wants to:

- "Add an SSE endpoint for X" / "stream X events to the frontend"
- "Publish a real-time update when Y happens"
- "Notify the browser when ..."
- "Add live updates / events stream / EventSource for ..."

If the user just wants to **publish** an event from a use case to an existing channel, skip to step 3 only.

---

## Architecture (one-line)

```
Use case publishes Event → Redis Pub/Sub channel → stream_sse(...) endpoint → fetch+ReadableStream in browser
```

Key files (already exist — reuse, don't re-create):

| Concern | File |
|---|---|
| `Event` base | `backend/src/common/domain/events/base.py` |
| `EventPublisher` protocol + `RedisEventPublisher` | `backend/src/common/infrastructure/event_publisher.py` |
| `stream_sse(...)` helper | `backend/src/common/infrastructure/sse/streaming.py` |
| `EventPublisherDep`, `RedisClientDep` | `backend/src/common/infrastructure/dependencies/common.py` |
| Frontend `subscribeSSE` | `frontend/src/infrastructure/http/sse.ts` |

---

## Step-by-step: add a new SSE endpoint

### 1. Define the domain event (DDD)

`backend/src/<module>/domain/events/<resource>_event.py`:

```python
from typing import Literal
from uuid import UUID

from src.common.domain.events.base import Event

# Discriminator: keep as `Literal[...]`, NOT a Python Enum.
# Reason: it's a string union that travels over the wire; an Enum
# adds `.value` indirection without type-safety gain.
MyResourceEventType = Literal[
    "RESOURCE_CREATED",
    "RESOURCE_UPDATED",
    "RESOURCE_DELETED",
]

# Channel naming convention: "<scope>:<id>:<topic>:events".
# Always co-locate the channel helper with the event class.
def channel_for_my_resource(resource_id: UUID) -> str:
    return f"my_resource:{resource_id.hex}:events"


class MyResourceEvent(Event):
    type: MyResourceEventType
    resource_id: UUID

    @property
    def channel(self) -> str:
        return channel_for_my_resource(self.resource_id)
```

If a subset of types should close the stream (terminal events), add a constant **here** in the domain module:

```python
RESOURCE_TERMINAL_EVENT_TYPES: frozenset[MyResourceEventType] = frozenset(
    {"RESOURCE_DELETED"}
)
```

The presentation layer imports it; the domain owns the knowledge.

### 2. Publish from a use case (after commit)

Use cases call `publisher.publish(event)`. The publisher is **always injected**, never instantiated:

```python
from src.common.infrastructure.event_publisher import EventPublisher

@dataclass
class CreateMyResource(UseCase):
    repository: MyResourceRepository
    publisher: EventPublisher  # injected by the endpoint

    async def execute(self, ...) -> MyResource:
        resource = await self.repository.persist(...)
        await self.publisher.publish(
            MyResourceEvent(
                seq=int(time.time() * 1000),
                ts=datetime.now(UTC),
                type="RESOURCE_CREATED",
                resource_id=resource.uuid,
                payload={"uuid": str(resource.uuid)},
            )
        )
        return resource
```

**Rules:**

- Publish **after** `session.commit()` — never inside a transaction.
- Keep `payload` small (signal + ids). Frontend refetches the REST endpoint for full data.
- The publisher is fire-and-forget: failures log a warning, don't break the use case.

#### From a FastAPI background task

`BackgroundTasks` runs outside the request scope, so DI doesn't reach it. Pass the publisher (and `redis_client` if needed) **as positional args** from the endpoint:

```python
background_tasks.add_task(
    my_background_fn,
    resource_id,
    tenant.uuid,
    http_request.app.state.database_config,
    http_request.app.state.event_publisher,  # singleton from lifespan
)
```

Mirror pattern: see `parser_scheduler.run_parser_in_background`.

### 3. Add the endpoint (thin orchestrator)

`backend/src/<module>/presentation/endpoints/<resource>_events.py`:

```python
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import RedisClientDep, get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.sse.streaming import stream_sse
from src.<module>.domain.events.<resource>_event import (
    RESOURCE_TERMINAL_EVENT_TYPES,  # if applicable
    channel_for_my_resource,
)


async def stream_my_resource_events(
    resource_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> EventSourceResponse:
    # 1. Ownership check FIRST — raises 404 before opening the stream.
    resource = await app_context.domain.my_resource_repository.find_by_id(
        resource_id, tenant.uuid
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    # 2. Hand off to the helper. Endpoint stays thin.
    return stream_sse(
        channel=channel_for_my_resource(resource_id),
        redis_client=redis_client,
        request=request,
        close_after=RESOURCE_TERMINAL_EVENT_TYPES,  # omit if stream is open-ended
    )
```

#### With Postgres replay (late subscribers)

If late subscribers must catch up via `since_seq`, build a `replay` callable that yields presented dicts:

```python
since_seq: int = Query(default=0, ge=0)

replay_events = await MyResourceEventReplayer(
    resource_id=resource_id,
    tenant_id=tenant.uuid,
    since_seq=since_seq,
    repository=app_context.domain.my_resource_event_repository,
).execute()

async def replay():
    for ev in replay_events:
        yield MyResourceEventPresenter(instance=ev).to_dict

return stream_sse(
    channel=channel_for_my_resource(resource_id),
    redis_client=redis_client,
    request=request,
    replay=replay,
    filter_fn=lambda ev: ...,  # optional, per-event predicate
)
```

`stream_sse` automatically dedupes live events whose `seq` was in the replay window.

### 4. Register the route

`backend/src/<module>/presentation/router.py`:

```python
from sse_starlette.sse import EventSourceResponse
from src.<module>.presentation.endpoints.<resource>_events import stream_my_resource_events

my_resource_router.add_api_route(
    "/{resource_id}/events",
    stream_my_resource_events,
    methods=["GET"],
    summary="SSE — my resource events",
    response_class=EventSourceResponse,
)
```

URL convention: `GET /v1/<resource>/<id>/events`.

### 5. Frontend hook

`frontend/src/application/hooks/use-<resource>-events.ts`:

```ts
import { useEffect } from "react";
import { subscribeSSE } from "@/src/infrastructure/http/sse";

export function useMyResourceEvents(resourceId: string, onEvent: (ev: MyResourceEnvelope) => void) {
  useEffect(() => {
    if (!resourceId) return;
    return subscribeSSE(
      `${API}/v1/my-resource/${resourceId}/events`,
      {
        onEvent: ({ type, data }) => {
          if (type === "ready" || type === "heartbeat") return;
          onEvent(JSON.parse(data));
        },
      }
    );
  }, [resourceId, onEvent]);
}
```

For replay-aware streams, pass a URL **factory** so the URL recomputes on reconnect:

```ts
let lastSeq = 0;
return subscribeSSE(
  () => `${API}/v1/my-resource/${resourceId}/events?since_seq=${lastSeq}`,
  { onEvent: (ev) => { lastSeq = Math.max(lastSeq, ev.seq); ... } }
);
```

The `subscribeSSE` client already handles: state machine (`idle/connecting/connected/reconnecting`), exponential backoff, watchdog for zombie connections, AbortSignal cleanup. Don't reinvent.

### 6. Tests (critical)

Write at least these — see `tests/common/infrastructure/sse/test_streaming.py` for patterns:

- **Domain** (`tests/<module>/domain/events/test_<resource>_event.py`):
  - `channel_for_my_resource(uuid)` returns the canonical string.
  - Terminal-types frozenset (if any) contains exactly the expected types.
- **Application** (use case):
  - Publishes with the right `event.channel` after commit.
  - Failure path still publishes a terminal event (no UI lock-up).
- **Endpoint** (only for non-trivial logic):
  - Ownership check → 404 when resource doesn't belong to tenant.
  - Replay function yields dicts in the expected order.

Use the `python-testing` skill to scaffold these — it knows the project's `expects` + AAA conventions.

---

## Anti-patterns (do NOT do this)

| Wrong | Right |
|---|---|
| `Redis.from_url(...)` + `RedisEventPublisher(redis=...)` inside a function | Receive `EventPublisher` as a parameter (singleton from `app.state.event_publisher`) |
| `StreamingResponse` with manual `f"event:...\ndata:...\n\n"` strings | `stream_sse(...)` returning `EventSourceResponse` |
| `Enum` for the event type discriminator | `Literal[...]` (matches the wire format string directly) |
| Putting business logic in the SSE handler | Endpoint = ownership check + `return stream_sse(...)`. Logic lives in use cases. |
| Publishing inside a transaction (before commit) | Publish **after** `await session.commit()` |
| Tenant-wide channel (`tenant:{id}:events`) | Per-resource channel (`workflow:{id}:rules:events`); ownership check enforces isolation |
| Big `payload` (full entity) | Signal-only payload (`{ids, status}`); frontend refetches the REST endpoint |
| Native browser `EventSource` | `subscribeSSE` (need `Authorization`/`X-Tenant` headers) |

---

## Checklist (paste into PR description)

```
Backend
- [ ] Event subclass + channel helper in `domain/events/`
- [ ] (If terminal events) frozenset constant co-located with event
- [ ] Publisher injected in use case / background task (not constructed)
- [ ] Publish AFTER commit
- [ ] Endpoint: ownership check → return stream_sse(...)
- [ ] Route registered with response_class=EventSourceResponse
- [ ] URL: GET /v1/<resource>/<id>/events

Frontend
- [ ] Hook in `application/hooks/use-<resource>-events.ts`
- [ ] AbortController cleanup on unmount / tenant change
- [ ] (If replay) URL factory with `since_seq`

Tests
- [ ] Channel helper produces canonical string
- [ ] Use case publishes on the right channel after commit
- [ ] Endpoint returns 404 when ownership fails
- [ ] (If replay) replayer yields events in order
```

---

## Reference: `stream_sse` signature

```python
def stream_sse(
    *,
    channel: str,                              # Redis pub/sub channel (event.channel)
    redis_client: Redis,                       # from RedisClientDep
    request: Request,                          # for is_disconnected()
    replay: ReplayFn | None = None,            # () -> AsyncIterator[dict]
    filter_fn: FilterFn | None = None,         # (dict) -> bool
    close_after: Collection[str] | None = None, # event types that close the stream
    heartbeat_s: float = 15.0,
) -> EventSourceResponse:
    ...
```

What it does, in order:

1. Yields `event: ready / data: {}` immediately so the client knows the stream is open.
2. Iterates `replay()` (if given), tracking `seq` values.
3. Loops on Redis pub/sub: each idle period of `heartbeat_s` yields a `heartbeat` frame.
4. Drops live events whose `seq` was already in the replay window.
5. Drops events for which `filter_fn(ev)` is False.
6. Closes the stream after delivering an event whose type is in `close_after`.
7. Detects client disconnects via `request.is_disconnected()` and tears down the pubsub cleanly.

---

## Common gotchas

- **`app.state.redis_client` uses `decode_responses=True`** — `pubsub.get_message()["data"]` is a `str`. The helper still handles `bytes` defensively for forward compatibility.
- **Background tasks lose the request scope** — they cannot use `Depends`. Pass `event_publisher`/`redis_client` as plain args from the endpoint.
- **Per-resource seq vs. global seq:** `stream_sse` dedupes by a flat `set[int]`. If your stream uses per-set `seq` namespaces (like `document_sets`), implement the per-namespace dedupe inside `filter_fn` instead.
- **Don't add `EventSourceResponse` middleware globally** — it's a per-route response class. The header `X-Accel-Buffering: no` is set inside `stream_sse` to disable nginx buffering.
- **`close_after` is a `Collection[str]`, not `frozenset[Literal[...]]`** at the helper level — invariance of `frozenset` would prevent passing a typed subset; the helper accepts the wider `Collection` and trusts the caller.
