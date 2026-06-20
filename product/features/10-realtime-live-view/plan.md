---
feature: realtime-live-view
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §1–§6; 06-data-model/plan.md §2.2/§2.4/§3; 05-agent-team/plan.md §4; 12-api/plan.md §1/§4; 13-frontend/spec.md §; common/infrastructure/sse/streaming.py; config/tasks.py; frontend/src/infrastructure/http/sse.ts
---

# Owliver — Live view del pentest (SSE, replay-then-tail) — plan de implementación (CÓMO)

> El entregable medular **no** es "un endpoint SSE": es la garantía de que quien
> abre el stream **tarde** (form → scan → click "ver en vivo") **no ve la pantalla
> vacía**. Eso se logra con una sola invariante operativa: **Postgres es la verdad**
> (`scan_events` con `seq` monótono por scan como única fuente de orden), **Redis es
> solo el tail** (pub/sub at-most-once, sin replay). El endpoint hace
> **replay-then-tail**: primero relee `scan_events WHERE seq > cursor ORDER BY seq`,
> luego se engancha al canal `scan:{id}:events`. El cliente deduplica por `seq`, así
> que el solape replay↔tail es inofensivo.
>
> Principio operativo: **PG primero, Redis después.** El worker persiste cada
> `ScanEvent` con `seq` creciente **antes** de publicarlo; ningún evento llega por
> tail sin estar ya disponible para replay. Esta feature **no inventa transporte
> nuevo**: reutiliza `stream_sse` (`src/common/infrastructure/sse/streaming.py`) y el
> subscriber `subscribeSSE` (`frontend/src/infrastructure/http/sse.ts`), ambos ya
> probados en el repo; solo añade el **emisor por seq**, la **ruta** y el **hook del
> theater**.

## 0. Estado de las dependencias

Esta feature se monta sobre infra que **ya existe** en el repo y sobre contratos que
[06-data-model](../06-data-model/plan.md) congela en la hora 0. No se reinventa nada
de lo siguiente:

- **Helper SSE `stream_sse`** — `backend/src/common/infrastructure/sse/streaming.py`.
  Ya implementa **exactamente** el patrón que esta feature necesita: emite un frame
  `ready` al abrir, ejecuta un callback `replay: () -> AsyncIterator[dict]`
  **antes** del tail, se suscribe a un `channel` Redis y hace tail con
  `pubsub.get_message(timeout=heartbeat_s)`, emite un frame `heartbeat` en cada idle,
  acepta `filter_fn` (predicado de dedupe del lado servidor) y `close_after`
  (conjunto de `type` terminales que cierran el stream tras entregarse). Los headers
  anti-buffer ya están puestos: `Cache-Control: no-cache, no-transform`,
  `Connection: keep-alive`, `X-Accel-Buffering: no`. **El comentario del propio
  helper ya dice "clients dedupe by `seq`"** — el diseño de 10 es el caso de uso para
  el que se escribió.
- **Cliente Redis compartido en el worker** — `backend/config/tasks.py`: `startup(ctx)`
  inyecta `ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=True)`
  y lo pasa a `build_async_bus(..., redis_client=ctx.get("redis"))`. **Ese mismo
  cliente** es el que el `ScanEventEmitter` (05) usa para `publish`. (Mismo cliente
  que el `CancelToken` de 04, ver [05-agent-team](../05-agent-team/plan.md) §0.)
- **Cliente Redis en la API** — `backend/src/common/infrastructure/dependencies/common.py`:
  `get_redis_client(request)` devuelve `request.app.state.redis_client`, expuesto como
  `RedisClientDep = Annotated[Redis, Depends(get_redis_client)]`. **Es el que la ruta
  SSE inyecta** para suscribirse al canal.
- **Router pattern** — `add_api_route(path, endpoint, methods)` sobre un `APIRouter`
  (`src/auth/presentation/router.py` es la referencia exacta). El endpoint `stream`
  ya está **declarado** por [12-api](../12-api/plan.md) §1.1 (`endpoints/stream_scan.py`);
  esta feature **aporta su cuerpo**.
- **Contrato `ScanEvent` + tabla `scan_events`** — `src/scans/domain/contracts/events.py`
  y `ScanEventORM` (`UNIQUE (scan_id, seq)`) los congela
  [06-data-model](../06-data-model/plan.md) §2.2/§2.4; el `ScanEventRepository`
  (hoy 06 documenta `append` con `seq` monótono) también es de 06 §2.4. **Aquí no se
  redefinen**: se importan. 10 **además requiere** a 06 un lector por cursor
  (`seq > since_seq`) y la reserva del `seq`; ese pedido se detalla en §2.2.
- **Auth por cookie** — el BFF de login **Google** (`src/app/api/auth/login/route.ts`,
  boilerplate SaaS) setea la cookie HttpOnly `SameSite=Lax`; patrón de set/forward ya
  probado. La dependency `current_user` (variante por-cookie) la posee el módulo `auth`/12;
  aquí se **consume**.
- **Subscriber SSE de frontend** — `frontend/src/infrastructure/http/sse.ts` ya
  exporta `subscribeSSE(urlOrFactory, opts)`: usa `fetch` (no `EventSource` nativo)
  con reconexión exponencial, **acepta una URL-factory** para recomputar
  `?since_seq=` en cada reintento, tiene watchdog de conexión (≥2× heartbeat) y un
  `parseEvent` que ya entiende los campos `event:`/`data:` e ignora comentarios
  `:`-heartbeat. **El hook del theater envuelve esto, no reimplementa el parser.**

> **Gap real a cerrar (no existe hoy):** el `stream_sse` actual emite
> `ServerSentEvent(event=..., data=...)` **sin** campo `id:` SSE. La spec (§3) pide que
> cada frame lleve `id: {seq}` para cerrar el ciclo de replay vía `Last-Event-ID` ante
> un `EventSource` nativo; el transporte real del repo (`subscribeSSE`) lleva el cursor
> por `?since_seq=` (§4.4), pero emitir `id: {seq}` es igualmente correcto, barato y deja
> el endpoint compatible con ambos clientes. Esto se resuelve **sin tocar la firma
> pública del helper** (ver §4.3): el replay y el tail ya entregan dicts con `seq`, y se
> añade `id=str(ev["seq"])` al construir el `ServerSentEvent`.
> Es la **única** modificación al helper compartido y se cubre con test.

## 1. Decisión de módulos — dónde vive cada pieza

El live view cruza tres capas que ya tienen dueño; esta feature **no crea un módulo
nuevo**, sino que coloca cada pieza en su capa natural:

| Pieza | Ubicación | Dueño / razón |
|---|---|---|
| Emisión de eventos (`ScanEventEmitter`) | `src/scans/worker/events.py` | Es código del **worker** ([05-agent-team](../05-agent-team/plan.md) §1 ya lo lista). El emisor sabe el `seq` siguiente y tiene el cliente Redis de `ctx`. 10 fija su **contrato** (orden PG→Redis, nombre de canal, shape); 05 lo **instancia** en el flujo. |
| Cuerpo del endpoint `GET /scans/{id}/stream` | `src/scans/presentation/endpoints/stream_scan.py` | [12-api](../12-api/plan.md) §1.1 ya declara el archivo; aquí se llena con el `require_scan_access` + `stream_sse(replay=…, channel=…)`. |
| Replay desde PG (`scan_event_replay`) | `src/scans/infrastructure/sse/replay.py` (**net-new**) | Factory que devuelve el `ReplayFn` (async-iterator de `scan_events WHERE seq > cursor`). Vive en `infrastructure` del módulo `scans` porque toca la DB. |
| `stream_token` efímero (un solo uso) | `src/scans/infrastructure/sse/stream_token.py` (**net-new**) | Token de query para scans privados sin cookie (§5.2). Redis con TTL + `GETDEL`. |
| Helper SSE genérico (`stream_sse`) | `src/common/infrastructure/sse/streaming.py` (**existente, +id:**) | Compartido; solo se le añade el campo `id:` (§4.3). |
| Hook del theater (`useScanStream`) | `frontend/src/application/hooks/use-scan-stream.ts` (**net-new**) | Capa `application` (hooks), espeja `application/hooks/queries`. Envuelve `subscribeSSE`. |
| BFF de paso del stream | `frontend/src/app/api/scans/[id]/stream/route.ts` (**net-new**) | Cumple la regla del repo (browser nunca pega al backend directo); reescribe a `/v1/scans/{id}/stream` propagando cookie. Detalle en §6.1. |

> **Por qué el emisor en `worker/` y el replay en `presentation`/`infrastructure`:**
> el **productor** (worker) y el **consumidor** (API) son procesos distintos
> (`saq` vs `uvicorn`). Lo único que comparten es **Postgres** (`scan_events`) y el
> **canal Redis** (`scan:{id}:events`). El emisor nunca importa nada de la API y
> viceversa; el acoplamiento es solo el shape `ScanEvent` de 06 y el nombre de canal,
> que se centraliza en un único helper (§3.1).

## 2. Mapa de archivos a crear

```
backend/src/
  common/infrastructure/sse/
    streaming.py                      # EXISTENTE — +id:{seq} en _frames (§4.3)
  scans/
    domain/contracts/events.py        # EXISTENTE (06) — ScanEvent congelado; aquí solo se consume
    worker/
      events.py                       # 05 lo posee; 10 fija el CONTRATO del emisor (§3)
    infrastructure/sse/
      channels.py                     # NET-NEW: scan_events_channel(scan_id) -> "scan:{id}:events"
      replay.py                       # NET-NEW: make_scan_event_replay(repo, scan_id, since_seq) -> ReplayFn
      stream_token.py                 # NET-NEW: mint/consume token efímero (Redis TTL + GETDEL)
    presentation/endpoints/
      stream_scan.py                  # 12 declara; 10 aporta el cuerpo (replay-then-tail)
frontend/src/
  app/api/scans/[id]/stream/route.ts  # NET-NEW: BFF de paso (cookie → backend, sin buffer)
  application/hooks/
    use-scan-stream.ts                # NET-NEW: hook EventSource (envuelve subscribeSSE)
  domain/scans/scan-event.ts          # NET-NEW: tipo TS ScanEvent (espeja events.py)
```

### 2.1 Contrato `ScanEvent` (de 06, **referido, no redefinido**)

`src/scans/domain/contracts/events.py` (congelado hora 0–2 por
[06-data-model](../06-data-model/plan.md) §2.2) tiene esta forma **1:1 con la tabla
`scan_events`** (spec §2):

```python
class ScanEvent(BaseModel):
    seq: int                          # monótono por scan — ÚNICA fuente de orden
    type: Literal[                    # discriminante evento → UI (enum ScanEventType, 06)
        "agent_status", "tool_start", "tool_end", "finding",
        "phase", "score", "done", "error",
    ]
    agent: str                        # carril emisor: worker | owasp | agentic
    tool: str | None = None           # típico en tool_start/tool_end
    severity: str | None = None       # presente en finding
    message: str                      # texto legible
    ts: datetime
    payload: dict[str, Any] | None = None
    progress: int | None = None       # 0–100, en phase (y opc. score) → barra header
```

> **Reglas del shape (spec §2):** `done` lleva `payload={"outcome": "success" |
> "cancelled"}` — la **cancelación es un `done` con `outcome:cancelled`**, no un
> `type` aparte (alineado con `POST /scans/{id}/cancel`, [12-api](../12-api/plan.md)
> §1). `error` es el otro terminal. `score` lleva `web_score`/`agentic_score`
> **parciales** en `payload` para refrescar los gauges en vivo. `finding` lleva
> `severity` + `payload.category` para insertar el hallazgo en la UI sin esperar al
> reporte. El front, ante `progress` ausente en un `phase`, **mantiene el último
> valor** (§6.2).

### 2.2 Tabla / repositorio (de 06, **referido**)

`scan_events` (`ScanEventORM`, 06 §2.4): `scan_id` FK, `seq int`, `ts`, `type`
(enum-`String`), `agent`, `tool?`, `severity?`, `message`, `payload JSONB`,
**`UNIQUE (scan_id, seq)`** (06 §3.3 — habilita el replay determinista). El
`ScanEventRepository` lo congela 06 §2.4; lo único que 06 documenta **literalmente**
hoy es **`append` con `seq` monótono** (más un test de replay-por-scan). 10 **necesita
además** dos capacidades de lectura/reserva y las **requiere a 06** (no las da por
existentes con firma fija):

| Capacidad que 10 necesita del `ScanEventRepository` | Estado en 06 | Uso en 10 |
|---|---|---|
| `append(event: ScanEvent) -> None` | **declarado** en 06 §2.4 (`seq` monótono) | el emisor del worker persiste **antes** de publicar (§3) |
| reservar el `seq` siguiente (p. ej. `next_seq(scan_id) -> int`) | **a confirmar con 06** — hoy 06 solo documenta el `append` monótono | el emisor reserva el `seq` siguiente; si 06 deriva el `seq` dentro de `append`, el emisor no necesita este método |
| leer `seq > since_seq ORDER BY seq` (p. ej. `replay(...)` o `list_since(...)`) | **a confirmar con 06** — 06 tiene un test de replay-por-scan, pero no fija la firma pública | el `ReplayFn` del endpoint (§4.1) |

> **Acción de coordinación con 06:** 10 **pide a 06 que declare explícitamente** en el
> ABC `domain/repositories/scan_event.py` (a) cómo se reserva el `seq` (método propio o
> dentro de `append`) y (b) un lector por cursor `seq > since_seq` ASC (sea `replay(...)`
> o `list_since(...)`). Mientras 06 no fije esas firmas, 10 **no las asume**: el
> `make_scan_event_replay` (§4.1) envuelve cualquiera de las dos formas (async-iterator
> o lista) en un `AsyncIterator[dict]`, y el emisor (§3) usa `next_seq` solo si 06 lo
> expone; si no, deriva el `seq` localmente (`_seq += 1`, ver §3 inv. 2). **La firma
> exacta la fija 06; 10 consume lo que 06 publique.**

## 3. El publisher del worker — `ScanEventEmitter` (contrato que 10 fija)

El emisor lo **instancia** el `WorkerFlow` (05 §4) y lo pasa cerrado a cada tool
wrapper (05 §2). 10 fija su **contrato de orden e idempotencia**:

```python
# src/scans/worker/events.py  (05 lo posee; 10 fija el contrato)
@dataclass
class ScanEventEmitter:
    scan_id: str
    repo: ScanEventRepository          # de 06 — persistencia/replay (la VERDAD)
    redis: Redis                       # ctx["redis"] del worker (config/tasks.py)
    _seq: int = 0

    async def emit(self, type_: str, *, agent: str, message: str,
                   tool: str | None = None, severity: str | None = None,
                   payload: dict | None = None, progress: int | None = None) -> None:
        self._seq += 1                                   # seq monótono por scan
        event = ScanEvent(seq=self._seq, type=type_, agent=agent, tool=tool,
                          severity=severity, message=message, ts=utcnow(),
                          payload=payload, progress=progress)
        await self.repo.append(event)                    # 1) POSTGRES PRIMERO (verdad + replay)
        await self.redis.publish(                        # 2) REDIS DESPUÉS (tail)
            scan_events_channel(self.scan_id),
            event.model_dump_json(),
        )
    # azúcares: agent_status / tool_start / tool_end / finding / phase / score / done / error
```

Invariantes (spec §1):

1. **PG antes que Redis, siempre.** El `append` se completa antes del `publish`. Si
   el `publish` falla, el evento **sigue** en `scan_events` y un cliente lo recupera
   por replay en su próxima (re)conexión — nunca al revés. Un evento publicado pero
   no persistido sería invisible al replay: ese orden está **prohibido**.
2. **`seq` lo asigna el emisor, no la DB.** Un único emisor por scan reserva
   `_seq += 1`; aunque emitan varios carriles (worker / subagente OWASP / agéntico),
   **todos pasan por el mismo emisor** (cerrado en el flujo), así que el `seq` es
   globalmente monótono por scan. El `UNIQUE (scan_id, seq)` de 06 es la red de
   seguridad: un doble-emit del mismo `seq` revienta en `append` (bug, no silencioso).
3. **`done`/`error` son los últimos `seq`.** El flujo (05 §4) emite `done` con
   `payload.outcome` o `error` como evento final; el endpoint los usa como
   `close_after` (§4.2).

### 3.1 Nombre de canal centralizado — `channels.py`

```python
# src/scans/infrastructure/sse/channels.py  (NET-NEW)
def scan_events_channel(scan_id: str) -> str:
    return f"scan:{scan_id}:events"
```

Lo importan **tanto** el emisor (worker) **como** el endpoint (API). Un solo punto de
verdad para el nombre del canal evita el clásico "publican en `scan:{id}` y se
suscriben a `scan:{id}:events`".

## 4. El endpoint `GET /scans/{id}/stream` — replay-then-tail

### 4.1 El `ReplayFn` (cierra el hueco sin duplicados)

```python
# src/scans/infrastructure/sse/replay.py  (NET-NEW)
def make_scan_event_replay(repo: ScanEventRepository, scan_id: str,
                           since_seq: int) -> ReplayFn:
    async def replay() -> AsyncIterator[dict[str, Any]]:
        async for event in repo.replay(scan_id, since_seq):   # seq > since_seq ORDER BY seq
            yield event.model_dump(mode="json")               # dict con seq/type/... para stream_sse
    return replay
```

El replay **siempre** lee con `seq > since_seq` ordenado por `seq` ASC. Es la pieza
que reconstruye **todo lo que el cliente se perdió** entre el inicio del scan (o su
última desconexión) y el `SUBSCRIBE`.

### 4.2 El cuerpo del endpoint

```python
# src/scans/presentation/endpoints/stream_scan.py  (12 declara; 10 llena)
async def stream_scan(
    scan_id: UUID,
    request: Request,
    since_seq: int = 0,                                   # ?since_seq= (fallback del cursor)
    redis: Redis = Depends(get_redis_client),            # request.app.state.redis_client
    app_context: AppContext = Depends(get_app_context),
    scan: Scan = Depends(require_scan_access),            # 12 §4 — 404 anti-IDOR, o stream_token (§5.2)
) -> EventSourceResponse:
    cursor = resolve_cursor(request, since_seq)          # §4.4: Last-Event-ID || since_seq || 0
    repo = app_context.domain.scan_event_repository      # repos cuelgan de DomainContext, no de AppContext
    return stream_sse(
        channel=scan_events_channel(str(scan_id)),
        redis_client=redis,
        request=request,
        replay=make_scan_event_replay(repo, str(scan_id), cursor),
        filter_fn=None,                                  # dedupe del lado CLIENTE (§4.5)
        close_after=frozenset({"done", "error"}),        # terminales → cierran el stream
        heartbeat_s=20.0,                                # spec §3.2 (~20s)
    )
```

- **`replay` antes que tail**: lo garantiza el propio `_frames` del helper (emite
  `ready`, luego agota `replay()`, luego entra al loop de `pubsub.get_message`). Es
  el orden que el test `test_frames__yields_replay_events_before_live` ya blinda.
- **`close_after={"done","error"}`**: cuando un evento terminal sale por tail, el
  stream se cierra tras entregarlo (test `test_frames__close_after_terminates...`).
  Si el scan **ya terminó** antes de conectarse el cliente, el `done`/`error` sale
  por **replay** y el cliente cierra al verlo (§6.2) — no se queda colgado esperando
  un tail que nunca llegará.
- **`heartbeat_s=20.0`**: spec §3.2; el watchdog del cliente (`sse.ts`,
  `connectionWatchdogMs` default 50000) está cómodo a ≥2×.

### 4.3 El frame lleva `id: {seq}` (única edición al helper compartido)

El `id:` SSE es el campo estándar de cursor por evento. Un **`EventSource` nativo** lo
rastrea y lo reenvía como `Last-Event-ID` al reconectar **por sí solo**; el transporte
real de este repo (`subscribeSSE`, §4.4) usa `fetch` y **no** lo reenvía
automáticamente, así que su cursor efectivo lo lleva la URL-factory `?since_seq=`. Aun
así emitimos `id: {seq}` porque (a) hace el endpoint correcto y compatible con cualquier
cliente `EventSource` nativo y (b) es barato. Hoy `_frames` no lo emite. Edición mínima
en `streaming.py`, **sin cambiar la firma pública**:

```python
# replay branch
yield ServerSentEvent(event=str(ev.get("type", "message")),
                      id=_seq_id(ev), data=json.dumps(ev))
# tail branch
yield ServerSentEvent(event=event_type, id=_seq_id(ev), data=raw)

def _seq_id(ev: dict) -> str | None:
    seq = ev.get("seq")
    return str(seq) if seq is not None else None
```

`_seq_id` devuelve `None` cuando el evento no tiene `seq` (p. ej. otros consumidores
del helper como processing-jobs), así que **no rompe a los demás callers**: el `id:`
solo aparece cuando hay `seq`. Cubierto por `test_frames__emits_seq_as_sse_id`.

### 4.4 Resolución del cursor — `resolve_cursor`

Precedencia (spec §3.1):

```
resolve_cursor(request, since_seq):
  hdr = request.headers.get("Last-Event-ID")            # solo un EventSource NATIVO lo reenvía solo
  if hdr is not None and hdr.isdigit(): return int(hdr) # reconexión: retoma justo donde quedó
  return since_seq                                       # ?since_seq= (o 0 = replay completo)
```

`Last-Event-ID` gana sobre `?since_seq=` cuando está presente, porque es el cursor
**más reciente** que el cliente conoce. Sin cursor, `0` → replay completo desde el
inicio del scan.

> **Precisión sobre el transporte de este repo (no es un error, es para no inducir a
> error):** el header `Last-Event-ID` lo reenvía **automáticamente** solo un cliente
> `EventSource` **nativo**. El transporte real aquí es `subscribeSSE` (`fetch`, §6.2),
> que **no** reenvía ese header por sí solo; en este camino el cursor efectivo lo
> aporta la **URL-factory `?since_seq=lastSeq`** del hook (§6.2). La rama
> `Last-Event-ID` de `resolve_cursor` se mantiene de todos modos por dos razones: (a)
> el BFF de §6.1 **reenvía** el header `Last-Event-ID` si el browser lo manda, así que
> un cliente que usara `EventSource` nativo (o reenvío manual) funcionaría sin tocar el
> backend; y (b) ambos caminos convergen al **mismo** cursor numérico, de modo que el
> endpoint es indiferente a cuál llegó. Con `subscribeSSE`, en la práctica, manda
> `?since_seq=`.

### 4.5 Por qué `filter_fn=None` (dedupe en el cliente, no en el servidor)

El solape natural replay↔tail (un evento que entró al canal Redis **justo** mientras
se leía el cursor de PG puede llegar por **ambos** caminos) se resuelve **en el
cliente** descartando `seq <= lastSeq` (spec §3.1). El helper lo soporta de fábrica:
su docstring dice *"Live events are NOT deduped against the replay — clients dedupe
by `seq`"*. No se pasa `filter_fn` server-side porque mantener un set de `seq` vistos
en el generador es justo el bug que el comentario de `_frames` advierte (colisión de
`seq` entre namespaces). **El front es el único árbitro de duplicados** (§6.2).

## 5. Auth por cookie (no por header)

`EventSource`/`fetch` del stream **no** llevan el JWT en header (spec §4): `EventSource`
nativo no permite headers custom, y el subscriber del repo (`sse.ts`) usa
`credentials: "same-origin"`. El flujo es por cookie:

### 5.1 Camino normal (cookie HttpOnly)

1. El BFF de login **Google** (`src/app/api/auth/login/route.ts`) setea la cookie
   HttpOnly `SameSite=Lax` (patrón de set/forward del boilerplate).
2. El cliente abre `/api/scans/{id}/stream` **same-origin** (§6.1); la cookie viaja
   sola.
3. La ruta valida vía `Depends(require_scan_access)` (12 §4). Para `scan.visibility ==
   "public"` (gov básico/pasivo) **no exige sesión**; para `private` exige
   `current_user` (cookie) **o** `stream_token` (§5.2), y si falta → **404, no 403**
   (no se filtra la existencia de un scan privado vulnerable — regla anti-IDOR de 12
   §4). **Un scan privado nunca queda con el stream abierto sin auth** (spec §4).

### 5.2 Alternativa: `stream_token` efímero de un solo uso

Para scans privados sin depender de la cookie (spec §4 — "alternativa rápida"):

```python
# src/scans/infrastructure/sse/stream_token.py  (NET-NEW)
async def mint_stream_token(redis, scan_id, user_id, *, ttl_s=120) -> str:
    token = secrets.token_urlsafe(32)
    await redis.set(f"stream_token:{token}", f"{scan_id}:{user_id}", ex=ttl_s)
    return token

async def consume_stream_token(redis, token, scan_id) -> bool:
    raw = await redis.getdel(f"stream_token:{token}")    # GETDEL = un solo uso atómico
    return raw is not None and raw.split(":")[0] == scan_id
```

- **Un solo uso**: `GETDEL` lo borra atómicamente al consumirlo; un replay del token
  falla. TTL corto (≤120s) acota la ventana.
- Se acopla a `require_scan_access` (12 §4): si no hay `current_user`, intenta
  `?stream_token=`; si tampoco valida → 404. La emisión del token (un endpoint o el
  propio `GET /scans/{id}` devolviéndolo al owner) la decide 12; 10 aporta
  mint/consume.

## 6. Frontend — hook EventSource y el "Live Pentest Theater"

El **render** del theater (carriles de agentes, `tool_start`/`tool_end`, findings en
vivo, gauges de score parcial) lo define [13-frontend](../13-frontend/spec.md). 10
aporta solo el **transporte cliente**: el hook que consume el stream y mantiene el
estado deduplicado.

### 6.1 BFF de paso — `app/api/scans/[id]/stream/route.ts`

Regla del repo (CLAUDE.md): el browser **nunca** pega al backend directo. El stream
pasa por una ruta BFF same-origin que reenvía a `/v1/scans/{id}/stream` propagando la
cookie y **sin comprimir/buffer**:

```ts
// NET-NEW — handler GET que hace stream-through
export async function GET(req: NextRequest, { params }) {
  const upstream = await fetch(
    `${BACKEND_API_HOST}/v1/scans/${params.id}/stream${req.nextUrl.search}`,
    { headers: { cookie: req.headers.get("cookie") ?? "",
                 "Last-Event-ID": req.headers.get("Last-Event-ID") ?? "",
                 Accept: "text/event-stream" },
      cache: "no-store" },
  );
  return new NextResponse(upstream.body, {                // pasa el ReadableStream tal cual
    status: upstream.status,
    headers: { "Content-Type": "text/event-stream",
               "Cache-Control": "no-cache, no-transform",
               "X-Accel-Buffering": "no",                 // desactiva buffer del proxy
               Connection: "keep-alive" },
  });
}
```

> **Compresión desactivada (spec §3.2 — crítico):** Next.js bufferea/comprime SSE y
> solo flushea al final si no se desactiva, lo que rompe el live view (el cliente no
> ve nada hasta que el scan termina). Se desactiva **explícitamente** en esta ruta:
> `Content-Type: text/event-stream` + `Cache-Control: no-transform` +
> `X-Accel-Buffering: no`, y se reenvía `upstream.body` (ReadableStream) sin
> recolectarlo. **No** se enruta el stream por el proxy genérico `src/proxy.ts`
> (rewrite de `/api/v1/*`) porque ese camino no garantiza el no-buffer; el stream
> tiene su **propia** ruta BFF.

### 6.2 El hook — `application/hooks/use-scan-stream.ts`

Envuelve `subscribeSSE` (`infrastructure/http/sse.ts`), que ya da reconexión,
backoff, watchdog y `parseEvent`. El hook **solo** añade: cursor por `seq`,
deduplicación e interpretación del discriminante.

```ts
// NET-NEW
export function useScanStream(scanId: string) {
  const lastSeq = useRef(0);                              // cursor de idempotencia
  const [state, dispatch] = useReducer(theaterReducer, initialTheater);

  useEffect(() => {
    const url = () => `/api/scans/${scanId}/stream?since_seq=${lastSeq.current}`; // factory: reconexión retoma el cursor
    const stop = subscribeSSE(url, {
      onEvent: ({ type, data }) => {
        if (type === "ready" || type === "heartbeat") return;
        const ev = JSON.parse(data) as ScanEvent;
        if (ev.seq <= lastSeq.current) return;            // §4.5 — descarta solape replay↔tail
        lastSeq.current = ev.seq;
        dispatch({ kind: ev.type, event: ev });           // discriminante → reducer del theater (13)
      },
      onStateChange: (s) => dispatch({ kind: "_conn", state: s }),
    });
    return stop;
  }, [scanId]);

  return state;                                           // alimenta el render del theater (13)
}
```

- **Cursor en la URL-factory**: como `subscribeSSE` usa `fetch` (no `EventSource`
  nativo), el navegador **no** reenvía `Last-Event-ID` por sí solo; el cursor lo
  lleva la factory, que `subscribeSSE` reevalúa en cada reintento enviando
  `?since_seq=lastSeq`, y el servidor hace replay solo de lo perdido. En este repo el
  `?since_seq=` es el cursor **efectivo**; la rama `Last-Event-ID` de §4.4 solo
  aplicaría si un cliente usara `EventSource` nativo (o reenviara el header a mano).
  Ambos caminos convergen al mismo cursor numérico (§4.4).
- **Dedup por `seq`**: `ev.seq <= lastSeq` se descarta → el solape replay↔tail es
  inofensivo (spec §3.1). **Único** árbitro de duplicados (§4.5).
- **Mapeo discriminante → UI**: el `dispatch({kind: ev.type})` enruta cada `type`
  (`agent_status|tool_start|tool_end|finding|phase|score|done|error`) al reducer del
  theater (forma de tarjetas/carriles/gauges en 13). `progress` ausente en `phase` →
  el reducer **conserva** el último valor (spec §2). `done`/`error` ponen el theater
  en estado terminal (`outcome` de `done.payload`).
- **Tipo TS `ScanEvent`** en `domain/scans/scan-event.ts` espeja `events.py` (mismos
  `type` literales) para tipar el `JSON.parse`.

## 7. Demo level — perfil rápido con timeout duro (referido a 04/05)

El live view del pitch corre solo el **perfil rápido** (spec §5): Nuclei subset +
testssl + **1 probe** contra el bot propio, con **timeout duro ~60–90s**. ZAP full /
garak / hexstrike **no** corren en vivo: se muestran desde fixtures pre-horneadas
(06 §2.7) para densidad sin pagar el costo. El **transporte** (esta feature) es
indiferente al perfil: el emisor publica los eventos que produzca el flujo; el
timeout/budget y la whitelist de tools los poseen
[04-scanning-engine](../04-scanning-engine/spec.md) y
[05-agent-team](../05-agent-team/plan.md) §4 (watchdog de budget → `done`/`cancelled`
→ cierre del stream vía `close_after`).

## 8. Suite de tests

Convención del repo: `tests/<área>/...`, pytest async, librería **`expects`**,
funciones standalone, AAA, fixtures por función. Los tests de `_frames` ya existen
(`tests/common/infrastructure/sse/test_streaming.py`); aquí se **extiende** esa suite
para el `id:` y se añaden los del replay/emisor/cursor/token y el hook.

### 8.1 Backend

| Archivo | Capa | Asserts |
|---|---|---|
| `tests/common/infrastructure/sse/test_streaming.py` (extiende) | unit (`_frames`) | nuevo `test_frames__emits_seq_as_sse_id`: un evento con `seq` produce un `ServerSentEvent` con `id == str(seq)`; un evento **sin** `seq` produce `id is None` (no rompe a otros callers). Los tests `ready`/`replay-before-live`/`heartbeat`/`close_after` existentes siguen verdes. |
| `tests/scans/infrastructure/sse/test_replay.py` | repo (DB) | `make_scan_event_replay(repo, scan_id, since_seq)` emite **solo** `seq > since_seq`, **ordenado por `seq` ASC**; `since_seq=0` ⇒ replay completo; `since_seq=last` ⇒ vacío; eventos de **otro** `scan_id` no se filtran dentro (aislamiento por scan). |
| `tests/scans/infrastructure/sse/test_channels.py` | puro | `scan_events_channel(id) == f"scan:{id}:events"` (1 punto de verdad emisor↔endpoint). |
| `tests/scans/infrastructure/sse/test_stream_token.py` | repo (Redis) | `mint`→`consume` válido una vez; **segundo** `consume` del mismo token ⇒ `False` (GETDEL, un solo uso); token de **otro** `scan_id` ⇒ `False`; expira tras TTL. |
| `tests/scans/worker/test_event_emitter_order.py` | unit (mock repo+redis) | `emit` llama `repo.append` **antes** de `redis.publish` (orden PG→Redis verificado por `mock_calls`); `seq` es monótono creciente por scan; `done` lleva `payload.outcome`; un re-emit del mismo `seq` propaga el `IntegrityError` del `UNIQUE (scan_id, seq)` (no lo traga). |
| `tests/scans/presentation/test_resolve_cursor.py` | puro | `Last-Event-ID` numérico gana sobre `?since_seq=`; `Last-Event-ID` ausente ⇒ usa `since_seq`; ambos ausentes ⇒ `0`; `Last-Event-ID` no numérico ⇒ cae a `since_seq`. |
| `tests/api/test_scan_stream.py` | E2E (HTTP) | `GET /scans/{id}/stream` de un scan **público** sin sesión ⇒ 200 + primer frame `ready` + replay de los `scan_events` sembrados ordenados por `seq`; scan **privado** sin cookie/token ⇒ **404** (no 403); con cookie de owner ⇒ 200; respeta `Content-Type: text/event-stream` y `Cache-Control: no-transform`. |

### 8.2 Frontend

| Archivo | Capa | Asserts |
|---|---|---|
| `frontend/src/application/hooks/use-scan-stream.test.ts` | vitest + testing-library | con un `subscribeSSE` mockeado que emite `ready` + 3 eventos `seq 1..3`, el hook ignora `ready`/`heartbeat`, despacha 3 al reducer y deja `lastSeq=3`; un evento repetido `seq<=lastSeq` se **descarta** (dedup §4.5); la URL-factory incluye `?since_seq=lastSeq` tras avanzar el cursor; `done` deja el theater terminal con `outcome`. |
| `frontend/src/infrastructure/http/sse.test.ts` (existente) | vitest | `parseEvent` ya cubre el wire format; sin cambios (se referencia para no duplicar el parser en el hook). |

## 9. Secuencia de build

1. **06-data-model** (bloquea): `events.py` (`ScanEvent`), `ScanEventORM`
   (`UNIQUE (scan_id, seq)`), `ScanEventRepository`. 06 ya congela `append` con `seq`
   monótono; 10 le **pide declarar explícitamente** (§2.2) la reserva del `seq` y un
   lector por cursor `seq > since_seq` ASC (`replay`/`list_since`) para que la
   referencia sea exacta.
2. **`streaming.py` +`id:{seq}`** + su test (`test_frames__emits_seq_as_sse_id`). Es
   la única edición al helper compartido; se hace temprano y se blinda.
3. **`scans/infrastructure/sse/`**: `channels.py`, `replay.py`, `stream_token.py` +
   sus tests de repo/puros.
4. **`ScanEventEmitter`** (`scans/worker/events.py`) con orden PG→Redis + test de
   orden/monotonía. (Lo consume 05; 10 lo deja contractualmente correcto.)
5. **Endpoint** `stream_scan.py`: `resolve_cursor` + `stream_sse(replay=…,
   channel=…, close_after={done,error}, heartbeat_s=20)` + `require_scan_access`
   (de 12). Test E2E `test_scan_stream.py`.
6. **Frontend**: tipo `ScanEvent` (TS) → BFF `app/api/scans/[id]/stream/route.ts`
   (no-buffer) → hook `use-scan-stream.ts`. Tests vitest.
7. **13-frontend** monta el render del theater **sobre** el estado que devuelve el
   hook.

La feature pasa a `implemented`/coverage>0 cuando: la migración de 06 aplica, el
helper emite `id:{seq}`, el endpoint hace replay-then-tail sin huecos ni duplicados
(E2E verde) y el hook deduplica por `seq` (vitest verde).

## 10. Decisiones y riesgos abiertos

1. **Postgres es la verdad; Redis es solo el tail** — resuelto (spec §1). El emisor
   persiste **antes** de publicar; el endpoint hace replay-then-tail; el cliente
   deduplica por `seq`. Nunca se confía en Redis para orden ni para recuperación.
2. **Reutilizar `stream_sse`, no reinventar** — resuelto. El helper ya soporta
   `replay`/`heartbeat`/`close_after`/`filter_fn` y los headers anti-buffer; la
   **única** edición compartida es añadir `id: {seq}` (§4.3), retro-compatible
   (`id=None` cuando no hay `seq`).
3. **Dedupe en el cliente, no en el servidor** — resuelto (§4.5). `filter_fn=None`;
   el front descarta `seq <= lastSeq`. Evita el bug de colisión de `seq` entre
   namespaces que el propio `_frames` documenta.
4. **`id:` SSE vs `?since_seq=`** — ambos coexisten: `Last-Event-ID` tiene precedencia
   **cuando llega**, pero con el transporte real del repo (`subscribeSSE`/`fetch`) el
   navegador **no** lo reenvía solo, así que el cursor efectivo lo lleva la URL-factory
   `?since_seq=` del hook. La rama `Last-Event-ID` queda como compatibilidad para un
   `EventSource` nativo (el BFF de §6.1 ya reenvía el header). Ambos convergen al mismo
   `resolve_cursor` (§4.4).
5. **Cancelación = `done{outcome:cancelled}`, no un `type` aparte** — resuelto (spec
   §2, alineado con `POST /scans/{id}/cancel` de 12). `close_after={done,error}`
   cierra el stream en ambos terminales.
6. **BFF dedicado para el stream, no el proxy genérico** — el rewrite de
   `src/proxy.ts` (`/api/v1/*`) no garantiza no-buffer; el stream tiene su propia
   ruta `app/api/scans/[id]/stream/route.ts` que reenvía `ReadableStream` con
   `X-Accel-Buffering: no` (§6.1). **Riesgo abierto**: validar en el VPS real (Nginx
   /Cloudflare delante) que ningún proxy intermedio re-bufferee SSE; el header
   `X-Accel-Buffering: no` cubre Nginx, pero un CDN podría requerir bypass explícito
   de la ruta `/api/scans/*/stream`.
7. **`stream_token` efímero** — resuelto como `GETDEL` con TTL≤120s (un solo uso). La
   **emisión** del token (endpoint dedicado vs. campo en `GET /scans/{id}`) la decide
   [12-api](../12-api/spec.md); 10 aporta mint/consume.
8. **Un único emisor por scan garantiza `seq` monótono** — los tres carriles (worker
   / OWASP / agéntico) emiten a través del **mismo** `ScanEventEmitter` cerrado en el
   flujo (05). **Riesgo residual**: si 05 instanciara emisores por carril, el `seq`
   dejaría de ser globalmente monótono; el `UNIQUE (scan_id, seq)` de 06 lo
   convertiría en error duro (no en corrupción silenciosa), y el test de orden del
   §8.1 lo detecta.
