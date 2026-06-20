---
feature: api
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §14 (§14.1–§14.5), §11.3, §12.1; spec-gaps.md §6 (6.2–6.6, 6.10, 6.11)
---

# Owliver — API (FastAPI) — endpoints

> Superficie HTTP completa de Owliver sobre FastAPI: encolado idempotente de escaneos, autorización por endpoint para no convertir un producto que almacena vulnerabilidades explotables en un índice de cómo hackear los sitios de los usuarios (IDOR), cancelación/listado/health, el contrato del stream SSE, CRUD de watchlist, paginación por cursor y un formato de error único centralizado. La verdad de cada scan vive en Postgres; esta API es la fachada de lectura/mutación sobre ese estado. La autenticación (login **Google** del boilerplate SaaS, ya implementado) se documenta aquí solo como contrato HTTP; su flujo vive en el módulo `auth` existente.

## Superficie de endpoints

```
POST   /auth/logout                limpia sesión
GET    /auth/me                    usuario actual (auth)

POST   /scans            {url, level, authorized}  → encola, devuelve scan_id
GET    /scans                      (auth) lista paginada del usuario
GET    /scans/{id}                 estado + scores (+ tools_status, coverage, error)
GET    /scans/{id}/findings        findings del escaneo (paginado)
GET    /scans/{id}/stream          SSE live view (replay-then-tail, §12.1)
GET    /scans/{id}/report.pdf      PDF
POST   /scans/{id}/share           crea link público → token (TTL settable)
POST   /scans/{id}/cancel          mata un scan colgado

GET    /sites/{id}                 último escaneo + histórico
GET    /ranking?country=mx         leaderboard global gov (paginado)

GET    /watchlist                  (auth) sitios del usuario
POST   /watchlist        {url, monitor}
PATCH  /watchlist/{id}   {monitor}            alterna monitoreo
DELETE /watchlist/{id}             (auth) quita un sitio de la watchlist

GET    /me/alerts                  (auth) prefs de canal de alerta del usuario
PUT    /me/alerts        {emailEnabled, slackWebhookUrl}

GET    /r/{token}                  reporte público (redactado, §11.3)

GET    /health                     liveness del proceso
GET    /ready                      readiness (Postgres + Redis)
```

Todos los endpoints, salvo los explícitamente públicos (`/health`, `/ready`,
`/ranking`, `/r/{token}`, y los scans `public`), exigen sesión válida y check de
owner. Las tablas referenciadas (`scans`, `findings`,
`public_reports`, `watchlist`) son propiedad de [06-data-model](../06-data-model/spec.md);
el cálculo de scores expuesto por estos endpoints es propiedad de
[07-scoring](../07-scoring/spec.md).

## Autenticación (`/auth/*`) — contrato HTTP

Owliver **reusa el login Google del boilerplate SaaS** (ya implementado en el
módulo `auth`: OAuth → `GoogleSessionBuilder` → JWT + cookie). **No hay flujo
magic-link.** Esta API expone únicamente:

- `POST /auth/logout` limpia la cookie de sesión.
- `GET /auth/me` (auth) devuelve el usuario actual.

La cookie HttpOnly `SameSite=Lax` emitida por el BFF de login Google es la misma
que autentica el stream SSE (ver [10-realtime-live-view](../10-realtime-live-view/spec.md)).

## `POST /scans` — encolado idempotente

`POST /scans` recibe `{url, level, authorized}`, valida, encola un job y devuelve
el `scan_id`. Nada debe permitir que un doble-click, un retry de red o un seed
re-ejecutado lancen escaneos duplicados: cada escaneo corre Opus + Sonnet + garak
+ ZAP (caro), ensucia el ranking, y un retry ciego de un nivel **activo** es un
**segundo ataque no consentido** (ver [01-legal-ethics](../01-legal-ethics/spec.md)).

### Enforcement legal (gate previo al encolado)

Antes de encolar se aplica el **gate de atestación** de
[01-legal-ethics](../01-legal-ethics/spec.md) §2.1: un nivel **activo**
(intermedio/avanzado) **sin `authorized=true`** en el request responde **422**
(`attestation_required`) y el job **no** se encola. Un nivel **básico/pasivo** no
requiere atestación.

Owliver **no bloquea por dominio**: el activo se permite sobre **cualquier** URL
—incluidos `.gob.mx`— bajo atestación; la responsabilidad legal recae en quien
atesta. Para hosts `is_gov`/sensibles el refuerzo es **no bloqueante**: la
advertencia de la UI es más enfática (copy reforzado, [13-frontend](../13-frontend/spec.md))
y el resultado queda **privado por defecto** (`visibility=private`, fuera del
ranking público), pero el usuario **puede proceder**. Queda **descartado** el
bloqueo histórico `is_gov && level != basico → 422`.

### Idempotencia — dos capas

La cola es **SAQ** (asyncio-native, Redis-backed; el worker hace `asyncio.gather`). La
idempotencia se implementa en dos capas complementarias:

1. **Partial unique index** sobre `scans(site_id, level) WHERE status IN
   ('queued','running')`. Mientras exista un scan vivo para ese `(site_id, level)`,
   un segundo `POST` no crea otra fila: devuelve **200** con el `scan_id`
   existente. Una creación nueva devuelve **201 Created** con el `scan_id` recién
   generado. (El `200` queda **reservado** para el hit idempotente; toda creación
   real es `201`.)
2. **Job key de SAQ** derivada de `site_id+level` para colapsar el doble-submit
   inmediato dentro de la cola. El partial index cubre el re-scan posterior (que
   la cola por sí sola no cubre); la job key cubre la ráfaga simultánea antes de que
   la primera fila llegue a `queued`.

`scans.status='running'` actúa además como lock lógico.

### Reintentos

- `max_tries=1` para niveles **activos** (intermedio/avanzado): preferir **fallar
  a re-atacar**.
- `max_tries=2` para **básico/gov** (pasivo, sin segundo ataque no consentido).

### Códigos de respuesta de `POST /scans`

| Código | Significado |
|---|---|
| `201` | Scan nuevo encolado; body incluye el `scan_id` recién creado. |
| `200` | Hit idempotente: ya existía un scan `queued`/`running` para `(site_id, level)`; body devuelve el `scan_id` existente. |
| `422` | Gate de atestación: nivel activo sin `authorized=true` (`attestation_required`), o validación de input. |
| `429` | Rate-limit de API excedido (`5 scans/hora` por usuario); incluye `Retry-After`. |

### Rate-limiting de `POST /scans`

El límite de API —`5 scans/hora` por usuario— **reutiliza el `RateLimiter` Redis ya
existente** del fundamento SaaS, no `slowapi`:
`create_rate_limit_dependency(limit=5, window=3600, key_func=<por-usuario>)` de
`backend/src/common/infrastructure/dependencies/rate_limit.py`, estrategia
`fixed_window` (`INCR` + TTL). Al exceder, el handler existente responde **429** con
`Retry-After`. El rate-limit hacia el *target* (flags `-rl` / delay por herramienta)
es del worker ([04-scanning-engine](../04-scanning-engine/spec.md)); la política de
ambos límites y el `User-Agent` identificable los fija
[01-legal-ethics](../01-legal-ethics/spec.md) §4.

## AuthZ por endpoint — evitar IDOR

El producto almacena **vulnerabilidades explotables**; sin authZ, Owliver se
vuelve un índice público de cómo hackear los sitios de sus usuarios (el peor
titular posible). Reglas normativas:

- **`scans.id` = UUIDv4** (no serial) para que los identificadores no sean
  enumerables.
- **`scans.visibility ENUM(public, private)`**: gov básico/pasivo = `public`;
  intermedio/avanzado, o sites con `owner_user_id`, = `private`.
- `GET /scans/{id}` y `GET /scans/{id}/findings` de un scan **`private`** requieren
  ser **owner** (o estar en la watchlist del sitio). Sin permiso se responde
  **404** (no 403): no se confirma siquiera la existencia del recurso.
- El reporte público se sirve **solo vía token** en `/r/{token}` (con exploits
  redactados, §11.3), **nunca** vía `/scans/{id}`. Ver [09-reporting](../09-reporting/spec.md).
- `/health` y `/ready` son públicos. El resto de mutaciones —`watchlist`,
  `cancel`, `share`— exigen **owner**.

El mismo criterio aplica al stream: para scans `private` el `GET /scans/{id}/stream`
nunca queda abierto sin auth (cookie HttpOnly vía `Depends`, o token efímero de un
solo uso `?stream_token=`); ver [10-realtime-live-view](../10-realtime-live-view/spec.md).

## Lectura de scans

### `GET /scans/{id}` — estado + scores

Devuelve el estado del scan más los scores, exponiendo además los campos de
progreso y diagnóstico necesarios para el live-view al recargar:

- `status` (enum, incluye `cancelled` y `partial`; ver [06-data-model](../06-data-model/spec.md)).
- `web_score` / `agentic_score` (cálculo en [07-scoring](../07-scoring/spec.md)).
- `tools_status` (jsonb, p. ej. `{nuclei:'done', zap:'running'}`).
- `coverage` (jsonb con `{tool, status: ok|failed|timeout}`): permite a la UI
  marcar "cobertura parcial" y nunca mostrar A con cobertura incompleta.
- `error` (texto del fallo, si lo hubo).

### `GET /scans/{id}/findings`

Findings del escaneo, **paginado por cursor** y ordenados por **severidad desc**.
Sujeto al check de owner para scans `private` (404 si no hay permiso). La forma de
cada finding y su `dedupe_key` son propiedad de [06-data-model](../06-data-model/spec.md).

### `GET /scans/{id}/stream` — SSE live view

Contrato del endpoint SSE; la semántica de **replay-then-tail** y el esquema de
eventos son propiedad de [10-realtime-live-view](../10-realtime-live-view/spec.md).
Resumen del contrato:

- Redis pub/sub es at-most-once y sin replay; la **verdad vive en Postgres** y el
  pub/sub es solo el canal de tail.
- Al conectar, la ruta lee el cursor de `Last-Event-ID` (header de reconexión de
  `EventSource`) o de `?since_seq=`, hace **replay** desde Postgres de todos los
  `scan_events` con `seq > cursor` (emitiéndolos con su `id:` SSE = `seq`), y luego
  se suscribe al canal `scan:{id}:events` para **tail**.
- **Auth por cookie** (no header): `EventSource` no admite headers custom; el
  cliente abre con `new EventSource(url, { withCredentials: true })` y la ruta
  valida la cookie vía `Depends`. Alternativa rápida para scans privados: token
  efímero de un solo uso en query (`?stream_token=`).
- Heartbeat comment cada ~20s; **compresión desactivada** en esta ruta.

## Cancelación, listado y health

### `POST /scans/{id}/cancel`

Mata un scan colgado (crítico con hexstrike/garak atascados, que de otro modo
obligan a reiniciar el worker en pleno pitch). Efectos:

- Setea `scans.status='cancelled'` (se añade `cancelled` al enum de `scans.status`).
- Publica un evento SSE **terminal** `type=done` con `{outcome: 'cancelled'}` en el
  payload. Nota: el enum de `scan_events.type` **no** lleva `cancelled` — eso es un
  `status` del scan, no un tipo de evento.
- Levanta una flag en Redis que el worker chequea **entre tools** (no aborta a
  mitad de una tool, pero sí evita lanzar la siguiente).

Requiere owner.

### `GET /scans`

`GET /scans?status=&site_id=&limit=&cursor=`: listado paginado de los scans del
**usuario** (auth). Filtros opcionales por `status` y `site_id`.

### `GET /health` / `GET /ready`

- `GET /health`: **liveness** del proceso (público).
- `GET /ready`: **readiness**, verifica conectividad a **Postgres + Redis**
  (público). Útil para orquestadores y para el panel de demo.

## Watchlist — CRUD

- `GET /watchlist` (auth): sitios en la watchlist del usuario. Cada item incluye su
  **id de fila de `watchlist`**.
- `POST /watchlist` `{url, monitor}`: añade un sitio a la watchlist y **devuelve la
  fila creada** (incluido su `id` de fila de `watchlist`), de modo que el cliente
  pueda referenciarla luego para `DELETE`.
- `PATCH /watchlist/{id}` `{monitor}` (auth, owner): alterna el flag `monitor`
  (re-escaneo periódico) sobre una fila existente — respalda el **toggle de
  monitoreo** por dominio de la UI (brief §3.8 / [13-frontend](../13-frontend/spec.md)),
  que antes solo se podía fijar al crear. Devuelve la fila actualizada.
- `DELETE /watchlist/{id}` (auth): quita un sitio de la watchlist del usuario. El
  `{id}` de la ruta es el **id de fila de `watchlist`** (el devuelto por
  `GET /watchlist` y por `POST /watchlist`), **no** el `site_id`. Requiere owner.

## Alertas — preferencias de canal (`/me/alerts`)

Las preferencias de canal de alerta son **a nivel cuenta** (no por dominio; ver
[06-data-model](../06-data-model/spec.md) `notification_prefs`). Los canales y la
lógica de disparo los define [08-ranking-watchlists](../08-ranking-watchlists/spec.md) §5.

- `GET /me/alerts` (auth): devuelve `{emailEnabled, slackWebhookUrl}` del usuario
  actual (email al owner activo por defecto).
- `PUT /me/alerts` `{emailEnabled, slackWebhookUrl}` (auth): actualiza las
  preferencias (upsert sobre `notification_prefs`). `slackWebhookUrl` opcional/null.

## Reporte público — `GET /r/{token}` y `POST /scans/{id}/share`

`POST /scans/{id}/share` crea un link público y devuelve el token. El token se
genera con `secrets.token_urlsafe(32)`, TTL **default 7 días** (settable en este
mismo POST), con índice **UNIQUE** sobre `public_reports(token)` y soporte de
revocación (`revoked_at NULL`). Requiere owner.

`GET /r/{token}` sirve el reporte público (redactado). Contrato del token:

- Token inexistente → **404**.
- Token con `expires_at < now()` o `revoked_at` no nulo → **410 Gone** (copy
  "Este enlace expiró").
- Token válido → reporte **redactado**: capa ejecutiva + findings técnicos **sin
  payloads de explotación** (se muestra tipo, categoría, severidad, `impact` y
  `remediation`, nunca el exploit crudo). La redacción y el render son propiedad de
  [09-reporting](../09-reporting/spec.md) (§11.3).

## Paginación y formato de error

### Paginación por cursor

Aplica a `findings`, `scans` y `ranking`:

```
?limit=50&cursor=<id>   →   reutiliza Page[T] de common: { data, pagination: { nextCursor, limit }, timestamp }
```

Los findings se ordenan por **severidad desc**.

### Formato de error único

Centralizado en los `exception_handler` de FastAPI **desde la hora 0** (reutilizados
del fundamento SaaS, no se crean nuevos). La forma canónica del
`domain_error_handler` (y de la validación Pydantic) es:

```json
{ "errors": [ { "code": "", "message": "" } ], "validation": null, "timestamp": "..." }
```

- `errors` es un **arreglo** (no un objeto `error` singular); el cliente lee
  `errors[0].code` / `errors[0].message`. **No** existe la clave `details`.
- `validation` lleva el detalle de errores de campo (Pydantic 422), `null` en el
  resto; `timestamp` lo añade `ApiJSONResponse`.
- **Excepción**: el handler de rate-limit (`rate_limit_exception_handler`) emite una
  forma divergente (`{ "error": "rate_limit_exceeded", ... }`); el "formato único" es
  aspiracional entre handlers del fundamento y se documenta así para que el frontend
  ([13-frontend](../13-frontend/spec.md)) no asuma un único shape literal.

Códigos relevantes en toda la superficie:

| Código | Cuándo |
|---|---|
| `422` | Gate de atestación: nivel activo sin `authorized=true` (`attestation_required`) / validación de input. |
| `404` | Recurso ausente **o** sin permiso (scan `private` no-owner; token de reporte inexistente). |
| `410` | Token de reporte expirado o revocado (`/r/{token}`). |
| `200` | Hit idempotente de `POST /scans`: body trae el `scan_id` existente. |
| `201` | Scan nuevo encolado por `POST /scans`. |
| `429` | Rate-limit de API excedido (`POST /scans`, 5/h por usuario); incluye `Retry-After`. |
