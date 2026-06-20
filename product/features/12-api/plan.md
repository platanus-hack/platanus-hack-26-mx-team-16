---
feature: api
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: 12-api/spec.md (toda la superficie); 06-data-model/plan.md (módulos sites/scans, contratos); 01-legal-ethics/plan.md (gate, rate-limit, common/legal); 10-realtime-live-view/spec.md (SSE); 09-reporting/spec.md (/r/{token})
---

# Owliver — API (FastAPI) — plan de implementación (CÓMO)

> La spec ([./spec.md](./spec.md)) fija el **QUÉ** de toda la superficie HTTP
> (endpoints, idempotencia, AuthZ anti-IDOR, SSE, paginación, formato de error,
> rate-limit). Este plan fija el **CÓMO** sobre el patrón HTTP **ya canónico del
> repo** (módulo `auth` como referencia): cada endpoint es una función standalone
> en `presentation/endpoints/`, registrada con `add_api_route()` en el `router.py`
> del módulo; la lógica vive en un **use case** `@dataclass(UseCase)` con
> `execute()`; un **presenter** convierte la entidad a dict camelCase; los errores
> se traducen por el **handler global** ya montado en `config/main.py`.
>
> La API **no posee tablas ni dominio nuevos**: es la fachada HTTP sobre los
> módulos `src/sites/` y `src/scans/` que define
> [06-data-model](../06-data-model/plan.md). Este plan crea los `presentation/` y
> `application/use_cases/` de esos dos módulos, más dos piezas transversales
> net-new (helper de paginación por cursor y dependency de owner-check), y la
> suite E2E en `backend/tests/api/`.

## 0. Estado y dependencias

El codebase hoy es **solo el fundamento SaaS** (módulos `auth, users, profile,
tenants, common, messaging, assets, admin`). **No existen** `src/scans/` ni
`src/sites/`. Esta feature se habilita **después** de 06 (tablas + contratos) y en
paralelo con 10 (SSE) (auth Google ya existente, no bloquea).

**Depende de:**
- [06-data-model](../06-data-model/plan.md): tablas `sites`, `scans`, `findings`,
  `agentic_surface`, `scan_events`, `public_reports`, `watchlist`,
  `notification_prefs`; enums (`scan.status` con `cancelled`/`partial`,
  `scan.visibility`, `scan.level`, `finding.severity`); contratos Pydantic en
  `src/scans/domain/contracts/` (`Finding`, `AgenticResult`, `ScanEvent`). **Crea el
  partial unique index de idempotencia** (`scans(site_id, level) WHERE status IN
  ('queued','running')`).
- **Auth Google (boilerplate):** el login Google ya implementado en `auth` emite el
  JWT y la **cookie HttpOnly SameSite=Lax**. La API **consume** la dependency
  `get_authenticated_user` resultante (no hay flujo magic-link).
- [10-realtime-live-view](../10-realtime-live-view/spec.md): la semántica
  replay-then-tail y el esquema de eventos del `GET /scans/{id}/stream`. La API
  solo declara el endpoint y delega su cuerpo a 10.
- [01-legal-ethics](../01-legal-ethics/plan.md): `common/legal`
  (`enforce_attestation`, `default_visibility`, `is_active`) y `API_SCAN_RATE_LIMIT`.

**Reutiliza tal cual del fundamento (no se reinventa):**
- **Router pattern**: `APIRouter(prefix=..., tags=[...])` + `add_api_route(path,
  endpoint, methods)` — `src/auth/presentation/router.py` es el patrón exacto.
- **Use case**: `UseCase` (ABC, `async execute()`) en
  `src/common/domain/interfaces/use_case.py`.
- **Presenter**: `Presenter[T]` (Protocol, `@property to_dict`) en
  `src/common/domain/interfaces/presenter.py`.
- **Respuesta**: `ApiJSONResponse` (`src/common/infrastructure/responses/api_json.py`,
  envuelve en `{data: ...}`) + `src/common/domain/constants/status`.
- **Errores**: `DomainError` (`src/common/domain/exceptions/_base.py`) + handler
  global `domain_error_handler` ya registrado en `config/main.py`
  (`app.add_exception_handler(DomainError, domain_error_handler)`).
- **Rate-limit**: `create_rate_limit_dependency(limit, window, strategy, key_func)`
  (`src/common/infrastructure/dependencies/rate_limit.py`) + `RateLimitExceededError`
  → handler `rate_limit_exception_handler` (429) ya registrado en `main.py`.
- **Cola SAQ**: `config/tasks.py` (`worker_settings`, `queue`); el patrón de
  encolado desde un endpoint es `src/admin/presentation/endpoints/enqueue_example_job.py`.
  Nota: el `SaqCommandEnqueuer` compartido encola siempre `"handle_command"` con
  `timeout=AWS_LAMBDA_MAX_TIMEOUT` y **no** pasa `key`/`retries` (ver §2).
- **DI**: `get_app_context` (`src/common/infrastructure/dependencies/common.py`) +
  `AppContext` (solo `domain`/`bus`/`scheduler` — **no** transporta sesión ni
  redis). El ping de `/ready` (redis) y el rate-limit obtienen redis/sesión de sus
  **propias** dependencies, no de `AppContext`.
- **Registro de routers**: `config/router.py` → `app.include_router(api_router)`
  bajo prefijo `/v1`.

## 1. Mapa de endpoints → use case → repositorio → presenter → router

Cada endpoint vive en el `presentation/` del **módulo dueño** (06): `/scans/*`,
`/findings`, `/scans/*/stream|cancel|share`, `/r/{token}` en
`src/scans/`; `/sites/*`, `/watchlist/*`, `/ranking`, `/me/alerts` en `src/sites/`. `/auth/*`
los posee 11 (aquí solo se referencian). `/health`/`/ready` en `src/common/`.

| Método + ruta | Use case (`application/use_cases/`) | Repositorio (06) | Presenter | Router (módulo) | AuthZ |
|---|---|---|---|---|---|
| `POST /scans` | `EnqueueScan` | `ScanRepository`, `SiteRepository` | `ScanCreatedPresenter` | `scans` | auth + rate-limit |
| `GET /scans` | `ListUserScans` | `ScanRepository` | `ScanListItemPresenter` | `scans` | auth (filtra por user) |
| `GET /scans/{id}` | `GetScan` | `ScanRepository` | `ScanDetailPresenter` | `scans` | owner-or-public (404) |
| `GET /scans/{id}/findings` | `ListScanFindings` | `FindingRepository` | `FindingPresenter` | `scans` | owner-or-public (404) |
| `GET /scans/{id}/stream` | (cuerpo en 10) | `ScanEventRepository` | — (SSE) | `scans` | cookie/`stream_token` |
| `GET /scans/{id}/report.pdf` | `GetScanReportPdf` (render en 09) | `ScanRepository` | — (bytes) | `scans` | owner (404) |
| `POST /scans/{id}/share` | `CreatePublicShare` | `PublicReportRepository` | `ShareTokenPresenter` | `scans` | owner (404) |
| `POST /scans/{id}/cancel` | `CancelScan` | `ScanRepository` | `TaskResult` | `scans` | owner (404) |
| `GET /r/{token}` | `GetPublicReport` | `PublicReportRepository` | `PublicReportPresenter` (redacta, 09) | `scans` | público (token) |
| `GET /me/alerts` | `GetAlertPrefs` | `NotificationPrefsRepository` | `AlertPrefsPresenter` | `sites` | auth |
| `PUT /me/alerts` | `UpdateAlertPrefs` | `NotificationPrefsRepository` | `AlertPrefsPresenter` | `sites` | auth |
| `GET /sites/{id}` | `GetSiteHistory` | `SiteRepository`, `ScanRepository` | `SiteHistoryPresenter` | `sites` | público/owner |
| `GET /ranking?country=mx` | `GetRanking` | `SiteRepository` | `RankingItemPresenter` | `sites` | público (`visibility='public'`) |
| `GET /watchlist` | `ListWatchlist` | `WatchlistRepository` | `WatchlistItemPresenter` | `sites` | auth |
| `POST /watchlist` | `AddToWatchlist` | `WatchlistRepository`, `SiteRepository` | `WatchlistItemPresenter` | `sites` | auth |
| `PATCH /watchlist/{id}` | `ToggleWatchlistMonitor` | `WatchlistRepository` | `WatchlistItemPresenter` | `sites` | owner (404) |
| `DELETE /watchlist/{id}` | `RemoveFromWatchlist` | `WatchlistRepository` | `TaskResult` | `sites` | owner (404) |
| `GET /health` | — | — | — | `common` | público |
| `GET /ready` | `CheckReadiness` | (ping pg+redis) | — | `common` | público |

### 1.1 Archivos a crear

**`src/scans/presentation/`**
```
router.py                         # scans_router = APIRouter(prefix="/scans", ...) + add_api_route(...)
                                  # + report_router (prefix="/r")
endpoints/
  enqueue_scan.py                 # POST /scans  → EnqueueScan
  list_scans.py                   # GET  /scans
  get_scan.py                     # GET  /scans/{id}
  list_findings.py                # GET  /scans/{id}/findings
  stream_scan.py                  # GET  /scans/{id}/stream   (cuerpo lo aporta 10)
  report_pdf.py                   # GET  /scans/{id}/report.pdf
  share_scan.py                   # POST /scans/{id}/share
  cancel_scan.py                  # POST /scans/{id}/cancel
  public_report.py                # GET  /r/{token}
requests/
  enqueue_scan.py                 # EnqueueScanRequest(CamelCaseRequest): url, level, authorized
  share_scan.py                   # ShareScanRequest: ttl_days (opt)
presenters/
  scan.py                         # ScanCreatedPresenter, ScanListItemPresenter, ScanDetailPresenter
  finding.py                      # FindingPresenter
  share.py                        # ShareTokenPresenter
  public_report.py               # PublicReportPresenter  (redacción la posee 09)
exceptions.py                     # ScanNotFoundError(404), PublicReportNotFoundError(404),
                                  # PublicReportGoneError(410)  (subclases de DomainError)
```

**`src/scans/application/use_cases/`**: `enqueue_scan.py`, `list_user_scans.py`,
`get_scan.py`, `list_scan_findings.py`, `cancel_scan.py`, `create_public_share.py`,
`get_public_report.py`, `get_scan_report_pdf.py`.

**`src/sites/presentation/`**: `router.py` (`sites_router`, `watchlist_router`,
`ranking_router`, `me_router` prefix="/me") +
`endpoints/{get_site,get_ranking,list_watchlist,add_watchlist,toggle_watchlist,remove_watchlist,alerts_get,alerts_put}.py`
+ `requests/{add_watchlist,toggle_watchlist,alert_prefs}.py` +
`presenters/{site_history,ranking_item,watchlist_item,alert_prefs}.py`.

**`src/sites/application/use_cases/`**: `get_site_history.py`, `get_ranking.py`,
`list_watchlist.py`, `add_to_watchlist.py`, `toggle_watchlist_monitor.py`,
`remove_from_watchlist.py`, `get_alert_prefs.py`, `update_alert_prefs.py`.

**`src/common/` (transversal net-new):**
```
presentation/pagination.py        # CursorPage[T] (items, next_cursor), parse de ?limit=&cursor=
infrastructure/dependencies/ownership.py
                                  # require_scan_access(...) / require_watchlist_owner(...) → 404 si no autorizado
presentation/endpoints/health.py  # GET /health, GET /ready  (en módulo common o config)
```

**Registro**: añadir `scans_router`, `me_router`, `report_router`, `sites_router`,
`watchlist_router`, `ranking_router` y health a `config/router.py`.

## 2. Idempotencia de `POST /scans` — en el use case `EnqueueScan`

Dos capas, exactamente como la spec §"Idempotencia — dos capas". Toda la lógica
vive en `EnqueueScan.execute()`; el endpoint solo arma el use case y mapea el
resultado a 200/201.

```
EnqueueScan.execute():
  1. host_flags = resolve_host_flags(url)                      # common/legal (01)
  2. enforce_attestation(level, authorized)                    # 01 → AttestationRequiredError (422) si activo sin authorized
  3. site = SiteRepository.get_or_create(url, host_flags)      # upsert por hostname
  4. visibility = default_visibility(is_gov, level, has_owner) # 01
  5. try:
        scan = ScanRepository.create(site_id, level, visibility,
                 authorized, authorized_at=now, requested_by=user.id,
                 status='queued')                              # INSERT
     except IntegrityError on partial unique index:            # ya hay scan vivo (site_id, level)
        existing = ScanRepository.get_active(site_id, level)
        return EnqueueResult(scan=existing, created=False)     # → 200
  6. await enqueuer.enqueue(RunScanCommand(scan_id=scan.id))  # ver nota: el SaqCommandEnqueuer
                                                              # compartido NO pasa key/retries (§abajo)
  7. return EnqueueResult(scan=scan, created=True)             # → 201
```

- **Capa 1 (partial index)**: el `IntegrityError` del índice parcial de 06 es la
  fuente de verdad del hit idempotente. Se captura **dentro del use case** (no en
  el router) y se traduce a `EnqueueResult(created=False)` → el endpoint responde
  **200** con el `scan_id` existente.
- **Capa 2 (job key SAQ) — atención al enqueuer compartido**: el
  `SaqCommandEnqueuer` del fundamento
  (`src/common/infrastructure/buses/saq_command_enqueuer.py`) hardcodea
  `queue.enqueue("handle_command", command_data=..., timeout=AWS_LAMBDA_MAX_TIMEOUT)`
  y **no** propaga `key` ni `retries`. El job key `scan:{site_id}:{level}` que
  colapsaría la ráfaga simultánea **no está cableado hoy**. Para tenerlo hay que
  **o bien** extender `SaqCommandEnqueuer` (o usar `queue.enqueue` directo) para
  pasar `key`/`retries`, **o bien** renunciar a la capa 2 y apoyarse **solo en la
  capa 1** (el partial unique index de 06 sobre `scans(site_id, level)`), que cubre
  el re-scan posterior y casi toda la ráfaga salvo la ventana de carrera previa al
  primer `queued`. La implementación **no debe** asumir un parámetro `key` que no
  existe en el enqueuer.
- **`max_tries`/`retries`**: el objetivo de diseño es `1` para activos (preferir
  fallar a re-atacar — §01) y `2` para básico/gov; igual que `key`, esto **solo es
  configurable si se extiende el enqueuer compartido** (que hoy no expone `retries`).
- El endpoint elige status por `result.created`:
  `ApiJSONResponse(ScanCreatedPresenter(result.scan).to_dict, status_code=201 if result.created else 200)`.

## 3. Rate-limit de `POST /scans`

Reutiliza la factory existente — **sin slowapi**. En `enqueue_scan.py`:

```python
from src.common.infrastructure.dependencies.rate_limit import create_rate_limit_dependency
from src.common.domain.legal.constants import API_SCAN_RATE_LIMIT  # (5, 3600) — 01

scan_rate_limit = create_rate_limit_dependency(
    limit=API_SCAN_RATE_LIMIT[0],
    window=API_SCAN_RATE_LIMIT[1],
    strategy="fixed_window",
    key_func=lambda r: f"scans:{current_user_id(r)}",   # por usuario, no por IP
)

async def enqueue_scan(
    payload: EnqueueScanRequest,
    _: Annotated[None, Depends(scan_rate_limit)],
    app_context: AppContext = Depends(get_app_context),
    user: User = Depends(get_authenticated_user),
): ...
```

`fixed_window` = `INCR` + TTL en Redis. Al exceder, `RateLimiter` lanza
`RateLimitExceededError` y el `rate_limit_exception_handler` ya registrado en
`config/main.py` responde **429** con header `Retry-After`. No se toca el handler.

## 4. AuthZ anti-IDOR — dependency reutilizable + regla 404-no-403

Una sola dependency `require_scan_access` (`common/.../ownership.py`) usada por
`GET /scans/{id}`, `/findings`, `/report.pdf`, `/cancel`, `/share`:

```python
async def require_scan_access(
    scan_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    user: User | None = Depends(get_optional_authenticated_user),
) -> Scan:
    scan = await ScanRepository.get_by_id(scan_id)
    if scan is None:
        raise ScanNotFoundError                       # 404
    if scan.visibility == "public":
        return scan                                   # gov básico/pasivo
    if user is None or not _owns_or_watches(user, scan):
        raise ScanNotFoundError                       # 404, NUNCA 403 — no confirma existencia
    return scan
```

- **404, no 403** para `private` sin permiso: no se filtra la existencia del
  recurso (la peor fuga sería un índice enumerable de sitios vulnerables).
- `scans.id` es **UUIDv4** (06) → no enumerable.
- `_owns_or_watches` = `scan.requested_by == user.id` **o** el `site_id` está en la
  watchlist del usuario.
- `require_watchlist_owner(watchlist_id, user)` análogo para `PATCH`/`DELETE
  /watchlist/{id}` (el `{id}` es **fila de `watchlist`**, no `site_id`): 404 si la
  fila no existe o no es del usuario.
- El reporte público **nunca** se sirve por `/scans/{id}`; solo por `/r/{token}`
  con redacción (09). `GET /r/{token}`: token inexistente → 404; expirado/revocado
  → **410**; válido → reporte redactado.
- **Stream** (`/scans/{id}/stream`): para `private` se valida cookie HttpOnly vía
  `Depends`, o `?stream_token=` de un solo uso (detalle en 10); nunca queda abierto
  sin auth.

## 5. Formato de error único y paginación por cursor

### 5.1 Formato de error
**Ya resuelto por el fundamento** — no se crea nada nuevo: el
`domain_error_handler` registrado en `config/main.py` serializa cualquier
`DomainError` a la forma real del fundamento `{ "errors": [ { "code", "message" } ], "validation": null, "timestamp": "..." }` (`errors` es un **arreglo**; el cliente
lee `errors[0]`; no existe `details`; `ApiJSONResponse` añade `timestamp`). El
handler de validación Pydantic reusa la misma forma con `validation` poblado (422).
Esta feature solo **añade subclases** de `DomainError` (`ScanNotFoundError` 404,
`PublicReportNotFoundError` 404, `PublicReportGoneError` 410) en `exceptions.py`;
`AttestationRequiredError` (422) lo aporta 01. Rate-limit →
`rate_limit_exception_handler` (429), que emite su propia forma divergente (`error`
como string). **Mapa completo de códigos**: 200 (hit idempotente), 201 (scan nuevo),
422 (`attestation_required`/validación), 404 (ausente o sin permiso), 410 (token
expirado/revocado), 429 (rate-limit).

### 5.2 Paginación por cursor
**Reutiliza la infra de cursor ya existente en `common`** (no se reinventa): el
helper `encode_cursor`/`decode_cursor` (`src/common/application/helpers/pagination.py`,
base64 Fernet de `datetime|uuid`) y el genérico `Page[T]`
(`src/common/domain/entities/common/pagination.py`: `next_cursor`, `items`,
`apply_presenter()`), que `ApiJSONResponse` ya serializa como
`{ data, pagination: { nextCursor, limit }, timestamp }`. El patrón `limit+1` →
`encode_cursor` → keyset-WHERE ya lo usan los repos de `tenants`.

- Contrato HTTP (el **real**, no uno nuevo): `?limit=50&cursor=<id>` →
  `{ data: [...], pagination: { nextCursor, limit }, timestamp }`. `findings`,
  `scans` y `ranking` devuelven este mismo envoltorio.
- Lo **único net-new** es el cursor compuesto `(severity, id)` que `findings`
  necesita para ordenar por severidad desc de forma estable: una **extensión** del
codec existente, no un `CursorPage` paralelo. `PageIndex` cubre `datetime|uuid`;
  el cursor de severidad añade un discriminante `{sev}:{id}` al mismo `encode_cursor`.
- El repo (06) recibe `(limit, cursor)`, aplica el keyset-WHERE y devuelve `limit+1`
  filas para calcular `next_cursor`; el use case arma un `Page[T]`.
- El archivo `common/presentation/pagination.py` puede agrupar el helper de
  findings/presenters, pero **construye sobre `Page[T]`/`encode_cursor`**, no define
  un `CursorPage` nuevo.
- Respuestas camelCase: presenters convierten snake_case → camelCase (regla CLAUDE.md).

## 6. Health / readiness

- `GET /health`: liveness puro (proceso vivo), sin tocar dependencias → 200.
- `GET /ready`: `CheckReadiness` hace ping a **Postgres** (`SELECT 1`) y **Redis**
  (`PING`) obteniendo la sesión y el cliente redis de sus **propias** dependencies
  (el `AppContext` no los transporta); 200 si ambos responden, 503 si alguno falla.
  Ambos **públicos** (sin auth) — útiles para orquestadores y el panel de demo.

## 7. Secuencia de build

1. **06-data-model**: tablas + enums + contratos + **partial unique index** de
   idempotencia. (Bloquea todo.)
2. **`common` transversal**: `pagination.CursorPage`, `ownership.require_scan_access`/
   `require_watchlist_owner`, `health`/`ready`. Tests unitarios del cursor.
3. **`src/sites/` presentation+application**: `/sites/{id}`, `/ranking`, watchlist
   CRUD + toggle. → tests E2E watchlist + ranking público.
4. **`src/scans/` lectura**: `GET /scans`, `GET /scans/{id}`, `/findings` con
   `require_scan_access`. → tests IDOR (404).
5. **`POST /scans`**: `EnqueueScan` (gate 01 + idempotencia 2 capas + rate-limit +
   enqueue SAQ). → tests 422/429/200/201.
6. **Mutaciones**: `/cancel`, `/share` + `/r/{token}` (410), `/me/alerts`.
7. **`/scans/{id}/stream`**: declarar endpoint; cuerpo replay-then-tail lo monta
   [10](../10-realtime-live-view/spec.md).
8. **Registro** de todos los routers en `config/router.py`.

La feature pasa a `implemented`/coverage>0 solo cuando la suite §8 pasa completa.

## 8. Suite de tests — `backend/tests/api/` (E2E) + `backend/tests/{scans,sites}/`

E2E sobre HTTP real con `requests` + `expects`, `pytestmark = [pytest.mark.api]`,
`BASE_URL`/cookie de sesión (patrón `tests/api/test_login.py`); responses camelCase
bajo `data`. Use cases con repos mockeados en `tests/{scans,sites}/application/`.

| Archivo | Asserts (contrato mínimo) |
|---|---|
| `tests/api/test_enqueue_scan.py` | activo sin `authorized` → **422** `attestation_required` y **no** encola; básico válido → **201** + `scanId`; segundo POST del mismo `(site,level)` vivo → **200** con el mismo `scanId` (idempotencia partial index); 6º scan/h del usuario → **429** + `Retry-After`; doble-submit en ráfaga → un solo job (job key) |
| `tests/api/test_get_scan_idor.py` | scan `private` de otro usuario → **404** (no 403); `public` → 200; UUID inexistente → 404 |
| `tests/api/test_findings.py` | paginación `?limit=&cursor=` → `{items, nextCursor}`; orden severidad desc; `private` no-owner → 404 |
| `tests/api/test_cancel_share.py` | `cancel` owner → status `cancelled` + evento SSE `done{outcome:cancelled}`; no-owner → 404; `share` → token; `GET /r/{token}` válido → 200 redactado; expirado/revocado → **410**; inexistente → 404 |
| `tests/api/test_watchlist.py` | `POST` devuelve fila con `id`; `PATCH {monitor}` alterna; `DELETE` usa **id de fila** (no site_id); `{id}` ajeno → 404 |
| `tests/api/test_alerts.py` | `GET /me/alerts` default `{emailEnabled, slackWebhookUrl:null}`; `PUT` upsert; aislado por usuario |
| `tests/api/test_ranking_health.py` | `/ranking` excluye `private`; `/health` 200 sin auth; `/ready` 200 con pg+redis, 503 si cae uno |
| `tests/scans/application/test_enqueue_scan.py` | unit: `IntegrityError` → `created=False`; gate llama `enforce_attestation`; persiste `authorized/authorized_at/requested_by`; encola el comando de scan (si se extiende el enqueuer para soportar `key`/`retries`, verificar también que son correctos por nivel) |

## 9. Decisiones / riesgos abiertos

1. **Cookie del stream**: la elección final cookie-HttpOnly vs `?stream_token=`
   efímero para scans `private` la cierra [10](../10-realtime-live-view/spec.md);
   la API expone ambos hooks (la dependency acepta cualquiera de las dos).
2. **`get_or_create` de `site`**: la normalización de hostname (puerto, trailing
   dot, `www.`) y el upsert atómico son de 06; `EnqueueScan` asume un repo que
   resuelve race en el `INSERT` del site igual que en el del scan.
3. **`/report.pdf`**: el render del PDF y la redacción los posee
   [09-reporting](../09-reporting/spec.md); la API solo hace owner-check y streamea
   bytes. Si el PDF no está listo (scan en curso) → 409/425 (a confirmar con 09).
4. **`get_optional_authenticated_user`**: la variante no-bloqueante de la dependency
   (devuelve `None` en vez de 401) **ya existe en el fundamento**
   (`src/common/infrastructure/dependencies/session.py`, junto a su alias
   `OptionalAuthenticatedUserDep`); `require_scan_access` solo la reutiliza para
   distinguir `public` sin sesión de `private` sin permiso. No es un riesgo abierto
   ni requiere coordinación con 11.
5. **Cursor estable en `findings`**: orden por severidad desc obliga a cursor
   compuesto (severity, id); si 06 expone solo `id`, se ordena en el repo y el
   cursor codifica ambos campos (base64 `{sev}:{id}`).
