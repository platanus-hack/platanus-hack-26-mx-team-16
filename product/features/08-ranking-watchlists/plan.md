---
feature: ranking-watchlists
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §2–§7; 06-data-model §2/§3/§5; 07-scoring §9.2–§9.4; 01-legal-ethics §2.2/§2.3/§3.2; 12-api (POST /scans, /ranking, /watchlist, /me/alerts); 04-scanning-engine §; 13-frontend §
---

# Owliver — Ranking público gov + watchlists + monitoreo/alertas — plan de implementación (CÓMO)

> El entregable medular **no** es un módulo nuevo de tablas (esas las define
> [06-data-model](../06-data-model/plan.md)), sino **tres mecanismos de continuidad
> cableados sobre el esquema y la cola que ya existen**: **(1)** un query de
> leaderboard "peores primero" sobre `sites WHERE is_gov` + un seed/fixtures que lo
> deja poblado desde el segundo 0; **(2)** el CRUD de watchlist privada con el flag
> `monitor`; y **(3)** un **`CronJob` de SAQ** que reencola monitoreo y, al comparar
> el nuevo scan contra el histórico **a nivel site** (`dedupe_key`/`first_seen`),
> emite alertas por **Resend** (email) y **Slack** (webhook), registrándolas en
> `alerts`.
>
> Principio operativo: **esta feature nunca recalcula columnas derivadas.** El
> grado (`overall_grade`), la penalización (`penalty_raw`), `is_gov`, `visibility`,
> `dedupe_key` y `first_seen` ya vienen computados por
> [07-scoring](../07-scoring/spec.md) / [04-scanning-engine](../04-scanning-engine/spec.md) /
> [06-data-model](../06-data-model/plan.md). El ranking solo **ordena y filtra**; el
> monitoreo solo **compara dos valores ya escritos** y decide notificar. El LLM no
> toca nada de esto.

## 0. Estado de las dependencias

Esta feature se monta sobre un repo que hoy es **solo el fundamento SaaS**: no hay
tabla `sites`/`scans`/`watchlist`/`alerts`, ni scheduler, ni cliente de Resend. Lo
que **sí** existe y se reutiliza tal cual (no se reinventa):

- **Cola + worker SAQ:** `backend/config/tasks.py` ya construye
  `queue = Queue.from_url(settings.redis_url)` y expone `worker_settings` con
  **`"cron_jobs": []`** vacío y listo para poblar, además de `startup`/`shutdown`
  (que ya inyectan `db_config` y un `Redis` en `ctx`). El cron de monitoreo se
  registra **aquí**, en esa lista (§4). El despacho de jobs sigue el patrón
  command-bus: `handle_command(ctx, command_data)` resuelve un `CommandHandler` vía
  `AsyncTaskResolver`; cada nuevo job es un `@dataclass CommandHandler` (ver
  `src/messaging/application/commands/example_job.py` como referencia de handler de
  background y `send_email.py` como referencia de handler que delega en un servicio).
- **Settings fail-loud:** `backend/src/common/settings.py` (pydantic-settings,
  `SettingsConfigDict(extra="ignore", case_sensitive=True)`). Aquí se añaden las
  claves nuevas (`RESEND_API_KEY`, `MONITOR_CRON`, etc., §5.3) con el mismo estilo;
  `settings.redis_url` ya es un `@computed_field`.
- **Cliente HTTP saliente:** `httpx` ya es dependencia del backend
  (`src/common/infrastructure/helpers/http.py` con `catch_httpx_exceptions`, y el
  helper de entrega de webhooks `src/common/application/helpers/webhooks/delivery.py`
  → `deliver_webhook(...)` con retry/backoff acotado que **nunca lanza** y devuelve
  un `WebhookDeliveryResult`). **OJO:** `deliver_webhook` es un emisor de
  **standard-webhooks _firmado_** — exige `secret`/`event_id`/`timestamp`
  obligatorios y emite headers de firma HMAC (`sign_payload` /
  `build_signature_headers`). Un Slack *incoming webhook* espera un POST JSON
  **plano** (`{"text": …}`) **sin** esos headers ni secret, así que **no** reutiliza
  `deliver_webhook`: el POST de Slack es un `httpx.AsyncClient.post` simple envuelto
  en `catch_httpx_exceptions` (igual que el cliente de Resend), encapsulado en un
  helper net-new `post_unsigned_webhook(...)` que devuelve un `WebhookDeliveryResult`
  para conservar el contrato fire-and-forget (§5.1). El cliente de Resend es,
  asimismo, un `httpx.AsyncClient` envuelto en `catch_httpx_exceptions`.
- **Email por command-bus:** `src/messaging/` ya tiene `EmailService` (ABC,
  `domain/services/email.py`) y `SendEmailHandler`
  (`application/commands/send_email.py`); el `SendEmailCommand` que ese handler
  resuelve vive en `src/common/application/commands/common.py` (no en
  `src/messaging/`). Resend se añade como **segunda impl de `EmailService`** (§5.3),
  no como camino paralelo.
- **Base ORM + mixins, registro de modelos, enums, repos, migraciones:** todo lo
  que [06-data-model](../06-data-model/plan.md) §0 enumera. Esta feature **no crea
  tablas** salvo que [06](../06-data-model/plan.md) ya las posee (`sites`,
  `watchlist`, `notification_prefs`, `scans`, `findings`, `alerts`). Aquí solo se
  añaden **repos/queries/use-cases/jobs**.
- **Tests:** `backend/tests/<área>/...` con `expects`, AAA, standalone; `conftest`
  con DB `doxiq_test` + `create_all` sobre `Base.metadata` (carpetas hoy: `api`,
  `auth`, `common`, `tenants`; se añaden `sites`, `scans`).

## 1. Decisión de módulos — dónde vive cada pieza

Esta feature **no introduce un módulo propio**; se reparte entre los dos módulos
que [06-data-model](../06-data-model/plan.md) §1 ya definió y un job de
infraestructura compartida. La separación sigue la dirección de dependencia
(`sites` no conoce `scans` salvo el puntero denormalizado `sites.latest_scan_id`):

| Pieza | Vive en | Razón |
|---|---|---|
| Query de leaderboard, seed gov, CRUD watchlist | `src/sites/` | Son lectores/escritores de `sites`/`watchlist`/`notification_prefs`; el ranking es la cara pública del catálogo de dominios. Los endpoints `/ranking`, `/watchlist`, `/me/alerts` ya están asignados a `sites`/`scans` en [12-api](../12-api/plan.md) §1. |
| Comparación de grado/`first_seen` + decisión de alerta | `src/scans/` | Lee el histórico de `scans`/`findings` de un site; la lógica de "bajó el grado / apareció critical nuevo" es de dominio `scans`. |
| Cron de monitoreo + clientes Resend/Slack | `config/tasks.py` (registro) + `src/scans/application/commands/` (handler) + `src/messaging/infrastructure/services/` (Resend) + `src/common/.../webhooks` (Slack: helper net-new `post_unsigned_webhook`, **no** `deliver_webhook`) | El cron es infraestructura de cola; el handler es lógica de aplicación; los canales son servicios de mensajería. **Ningún módulo de feature nuevo.** |
| Seed gov (`seed/gob_mx.txt`) + carga de fixtures | `backend/seed/` (data) + `backend/command.py` (`load`, extendido por 06) | El contenido del leaderboard pre-horneado es data, no código. La carga la hace el CLI typer existente. |

> **Por qué no un módulo `monitoring/`:** el monitoreo es un **orquestador delgado**
> que solo encola jobs ya existentes (`run_scan`, owned por
> [05-agent-team](../05-agent-team/spec.md)) y dispara notificaciones; no tiene
> tablas ni entidades propias (`alerts` es de `scans`). Un módulo extra solo añadiría
> indirección.

## 2. Mapa de archivos a crear

Rutas **exactas**. Todo lo marcado *(net-new)* lo crea esta feature; lo demás se
**reutiliza** de 06/fundamento.

### 2.1 Ranking público — `src/sites/`

```
src/sites/
  domain/
    repositories/ranking.py          # (net-new) RankingRepository(ABC): list_gov_ranking(country, limit, cursor)
  application/use_cases/
    get_ranking.py                    # (net-new) GetRanking — orden + cap parcial (§3)
  infrastructure/repositories/
    sql_ranking.py                    # (net-new) @dataclass SQLRankingRepository(session)
  presentation/                       # endpoint/presenter los detalla 12-api §1.1; aquí solo el query
```

> **No se crea una tabla nueva.** El ranking es un `SELECT` sobre `sites JOIN
> scans` (el scan vivo es `sites.latest_scan_id`). El índice del orden ya lo crea
> [06-data-model](../06-data-model/plan.md) §3.4 (`scans (overall_grade ASC,
> penalty_raw DESC)` + filtro `is_gov`).

### 2.2 Watchlist + preferencias — `src/sites/`

Los ORM `WatchlistORM`/`NotificationPrefsORM` y sus repos ABC/SQL ya están en el
mapa de [06-data-model](../06-data-model/plan.md) §2.3. Esta feature añade
**use-cases** (el CRUD HTTP lo expone [12-api](../12-api/plan.md) §1):

| Use case (`src/sites/application/use_cases/`) | Repo (06) | Qué hace |
|---|---|---|
| `list_watchlist.py` *(net-new)* | `WatchlistRepository` | filas del usuario + último grado (join a `sites.latest_scan_id`). |
| `add_to_watchlist.py` *(net-new)* | `WatchlistRepository`, `SiteRepository` | `get_or_create` site + inserta fila watchlist con `monitor=false` por defecto. |
| `toggle_watchlist_monitor.py` *(net-new)* | `WatchlistRepository` | `PATCH {monitor}` — **única señal** que el cron lee (§4.1). |
| `remove_from_watchlist.py` *(net-new)* | `WatchlistRepository` | `DELETE` por **id de fila** (no site_id). |
| `get_alert_prefs.py` / `update_alert_prefs.py` *(net-new)* | `NotificationPrefsRepository` | upsert 1:1 por `user_id` de `email_enabled`/`slack_webhook_url`. |

### 2.3 Monitoreo + alertas — `src/scans/` + `config/`

```
src/scans/
  domain/
    services/grade_delta.py           # (net-new) compare_grade(prev, curr) -> bool (bajó); new_criticals(scan) -> list[FindingRecord]
    repositories/alert.py             # AlertRepository(ABC) — ya en mapa 06 §2.4; aquí se usa para log
  application/
    use_cases/evaluate_site_alerts.py # (net-new) EvaluateSiteAlerts — la decisión de §4.2 (puro sobre repos)
    commands/monitor_cron.py          # (net-new) MonitorCronHandler — el cuerpo del CronJob (§4.1)
  infrastructure/
    services/resend_email.py          # (net-new) ResendEmailService(EmailService) — impl Resend del ABC de messaging
    services/slack_alert.py           # (net-new) post_slack_alert(webhook_url, payload) → POST httpx plano vía post_unsigned_webhook (NO deliver_webhook firmado)
    alerts/render.py                  # (net-new) build_alert_payload(site, prev_grade, curr_grade, new_criticals) — texto redactado (§5.3)
src/common/application/helpers/webhooks/
    unsigned.py                       # (net-new) post_unsigned_webhook(url, json) → httpx POST plano + catch_httpx_exceptions → WebhookDeliveryResult (para Slack incoming webhooks)
config/tasks.py                       # (editar) registrar el CronJob en worker_settings["cron_jobs"]
src/common/settings.py                # (editar) RESEND_API_KEY, MONITOR_CRON, MONITOR_LEVEL_DEFAULT, etc. (NO RESEND_FROM — se reusa DEFAULT_FROM_EMAIL, §5.4)
seed/gob_mx.txt                       # (net-new) ~30–50 dominios .gob.mx (§2.3 spec)
src/sites/application/commands/seed_gov.py  # (net-new) SeedGovHandler — job de arranque (§2.4)
```

> El **ORM `AlertORM`** (`alerts`) y `ScanORM`/`FindingORM` los posee
> [06-data-model](../06-data-model/plan.md). El `ResendEmailService` es una **segunda
> impl** de `EmailService` (`src/messaging/domain/services/email.py`), inyectable por
> el mismo command-bus; en prod se selecciona por presencia de `RESEND_API_KEY`.

### 2.4 Frontend — referencia, no propiedad aquí

`frontend/src/app/` hoy tiene `(public)` y `(protected)` pero **ningún**
`ranking`/`watchlist`/`sites` (verificado). La UI (Hall of Shame en `/`, dashboard
de watchlist, `/sites/[id]`) la construye [13-frontend](../13-frontend/spec.md)
consumiendo los endpoints de [12-api](../12-api/plan.md) vía el patrón BFF
obligatorio (`fetch("/api/...")` → `route.ts` → `serverHttp`). Aquí no se escribe
UI; solo se garantiza que `/ranking` sea **RSC-friendly** (§3.4).

## 3. Ranking — query, orden y cap de cobertura parcial

Autoridad del orden: [07-scoring](../07-scoring/spec.md) §9.4. El leaderboard
**no** ordena por `overall_score`.

### 3.1 Query (`SQLRankingRepository.list_gov_ranking`)

```sql
SELECT s.uuid, s.hostname, sc.overall_grade, sc.penalty_raw, sc.agentic_score,
       sc.status, sc.coverage, sc.finished_at
FROM sites s
JOIN scans sc ON sc.uuid = s.latest_scan_id
WHERE s.is_gov = true
  AND sc.visibility = 'public'        -- invariante solo-pasivo (§2.2 spec / 01)
  AND ($country IS NULL OR s.country = $country)
ORDER BY sc.overall_grade ASC, sc.penalty_raw DESC   -- peores primero, desempate cruda
LIMIT $limit OFFSET …                 -- cursor por (grade, penalty_raw, uuid)
```

- **`visibility='public'` + `is_gov=true` es el único origen de filas.** Un activo
  de usuario (`visibility='private'`) nunca aparece (invariante de
  [01-legal-ethics](../01-legal-ethics/plan.md) §3.3; el filtro es el mismo que
  `/ranking` aplica en [12-api](../12-api/plan.md) §1).
- **`penalty_raw` se muestra sin clamp** (06 lo persiste sin `min(100, …)`) para que
  decenas de `.gob.mx` colapsados en **F/0** sigan siendo comparables (§2.1 spec).
- El **índice** `scans (overall_grade ASC, penalty_raw DESC)` + parcial sobre
  `sites.is_gov` los crea [06](../06-data-model/plan.md) §3.4; este query es su
  consumidor y su test de orden (`tests/sites/...`, §6).

### 3.2 Cap de cobertura parcial (en `GetRanking`, no en SQL)

Cuando `scans.status='partial'`, [07-scoring](../07-scoring/spec.md) §9.2–§9.3
exige capar el grado mostrado a **C** y etiquetar "cobertura parcial". El cap **ya
viene escrito en `overall_grade`** por scoring (07 nunca persiste A con cobertura
parcial); `GetRanking` **no recalcula**, solo **propaga la bandera** `partial` al
presenter para que [13-frontend](../13-frontend/spec.md) pinte la etiqueta. Esta
feature no decide grados; solo decide que la fila lleve el flag.

### 3.3 Paginación

Reusa el helper de cursor net-new `common/presentation/pagination.py`
(`CursorPage[T]`) que define [12-api](../12-api/plan.md) §5.2. El cursor del ranking
codifica `(overall_grade, penalty_raw, uuid)` para ser estable ante empates masivos
en F. El repo devuelve `limit+1` filas; el use case arma `next_cursor`.

### 3.4 RSC-friendly (pre-horneado)

El leaderboard es la primera pantalla del pitch y debe renderizar en el servidor sin
bloquear en jobs. Garantías:

- El query **solo lee** `sites`/`scans` ya escritos (fixtures o scans reales); nunca
  encola ni espera.
- Como `sites.latest_scan_id` está denormalizado, el ranking es **un solo JOIN sin
  agregación**, cacheable por la capa RSC de Next.
- Los **fixtures pre-horneados** (§5) garantizan 30–50 filas coherentes desde el
  arranque; un board vacío o lleno de `failed` es imposible en el demo.

## 4. Monitoreo recurrente — el `CronJob` de SAQ

### 4.1 Registro del cron (NO rq-scheduler, NO APScheduler)

[01-legal-ethics](../01-legal-ethics/plan.md) §6.2 ya zanjó **SAQ** (cron `CronJob`,
dedupe por job key) como única cola/scheduler. El cron se registra poblando la lista
hoy vacía `worker_settings["cron_jobs"]` en `backend/config/tasks.py`:

```python
from saq import CronJob
from src.common.settings import settings

worker_settings = {
    "queue": queue,
    "functions": [handle_command, run_scan, seed_gov, monitor_cron],  # + jobs de 04/05
    "cron_jobs": [
        CronJob(monitor_cron, cron=settings.MONITOR_CRON),   # p.ej. "0 */6 * * *"
    ],
    "startup": startup,
    "shutdown": shutdown,
}
```

`settings.MONITOR_CRON` (string cron, default `"0 */6 * * *"` = cada 6 h) es fail-loud
en `settings.py`. **Una sola cola SAQ** es la fuente de verdad; no se introduce un
proceso scheduler extra (decisión cerrada, §7.1).

### 4.2 Cuerpo del cron (`MonitorCronHandler` / `monitor_cron`)

El handler corre dentro del worker (mismo `ctx` con `db_config`/`redis` que
`handle_command`). En cada tick:

```
monitor_cron(ctx):
  1. sites_a_reescanear =
        WatchlistRepository.sites_with_monitor_true()        # watchlist.monitor=true
        ∪ SiteRepository.gov_seed_sites()                    # seed gov (is_gov, sembrado)
  2. para cada (site, level):
        # watchlist → nivel autorizado por el owner; gov → SIEMPRE básico/pasivo
        level = MONITOR_LEVEL_DEFAULT if site.is_gov else watchlist.authorized_level
        assert (not site.is_gov) or level == ScanLevel.basico   # guard 01 §3.2
        enqueue_scan_idempotent(site_id, level)              # MISMA idempotencia que POST /scans
```

- **Idempotencia idéntica a `POST /scans`** (no se reimplementa): partial unique
  index `scans(site_id, level) WHERE status IN ('queued','running')` (el 2º encolado
  devuelve el `scan_id` vivo) + **job key SAQ** `key=f"scan:{site_id}:{level}"`. Si
  un escaneo del ciclo previo sigue corriendo, el reencolado es no-op. Contrato en
  [12-api](../12-api/plan.md) §2 y [06](../06-data-model/plan.md) §3.1.
- **Guard legal duro:** para `is_gov` el nivel está **hardcodeado** a `ScanLevel.basico`
  y se afirma `level in AUTOMATIC_ALLOWED_LEVELS`, si no →
  `AutomaticActiveScanError` ([01-legal-ethics](../01-legal-ethics/plan.md) §3.2). El
  cron **no** acepta nivel gov como parámetro.
- **Origen del scan = `requested_by IS NULL` (contrato fijado aquí).** El cron
  encola sus scans **sin `requested_by`** (esa columna ya es `FK→users.uuid`
  **nullable** en [06](../06-data-model/plan.md) §3.2 / spec §107, usada hoy para
  "gov anónimo del seed"). Esta feature **fija ese mismo NULL como la marca de
  "scan de cron/monitoreo"**: un scan con `requested_by IS NULL` es de origen
  cron-o-seed; uno con `requested_by` no-nulo es manual (lo disparó un usuario por
  `POST /scans`). Es la **única** señal que distingue ambos orígenes y de la que
  dependen tanto el encadenamiento de `EvaluateSiteAlerts` (§4.3, abajo) como el
  filtro de `previous_completed_scan`. No se añade una columna `origin`/`trigger`
  nueva: `requested_by` ya carga esa semántica. ([05-agent-team](../05-agent-team/spec.md)
  debe respetar el contrato — encolar con `requested_by=user_id` los scans manuales
  y dejarlo NULL para cron/seed — pero el contrato lo **fija este plan**, no queda
  abierto.)
- El cron **solo encola**. La ejecución del scan es de
  [05-agent-team](../05-agent-team/spec.md); el scoring/escritura de `overall_grade`
  y `findings` es de [07-scoring](../07-scoring/spec.md)/[04](../04-scanning-engine/spec.md).
  La evaluación de alertas (§4.3) corre **al final del scan**, encadenada por el
  worker, no en el tick del cron (el cron solo reencola; cuando un scan **de origen
  cron** —`requested_by IS NULL`— termina, dispara `EvaluateSiteAlerts`).

### 4.3 Detección de cambio a nivel site (`EvaluateSiteAlerts`)

Se ejecuta **después** de que un scan de monitoreo persiste su grado y sus findings.
Compara contra el histórico del site (no del scan), usando lo que 06 ya escribió:

`EvaluateSiteAlerts` **solo** se encadena para scans de origen cron
(`scan.requested_by IS NULL`, contrato de §4.2); un scan manual no dispara
alertas de monitoreo. La base de comparación es el último scan **completado** del
mismo site (sea manual o de cron — lo que importa es que tenga grado escrito):

```
EvaluateSiteAlerts.execute(scan):
  assert scan.requested_by is None            # gate: solo scans de cron/monitoreo (§4.2)
  prev = ScanRepository.previous_completed_scan(site_id, before=scan)   # último scan COMPLETED previo del mismo site
  bajo_grado   = compare_grade(prev.overall_grade, scan.overall_grade)  # grade_delta.py
  nuevos_crit  = FindingRepository.criticals_first_seen_in(scan)        # dedupe_key con first_seen == este scan
  if bajo_grado or nuevos_crit:
        dispatch_alert(site, prev.overall_grade, scan.overall_grade, nuevos_crit)  # §5
```

- **`compare_grade(prev, curr)`** (`grade_delta.py`, puro): `True` si el grado
  empeoró (A<B<…<F; F es el peor). Compara dos `char(1)` ya escritos; no recalcula.
- **`criticals_first_seen_in(scan)`** usa `findings(site_id, dedupe_key)` y
  `first_seen` (a nivel **site**, definidos por [06](../06-data-model/plan.md) §3.3):
  un `critical` cuyo `first_seen` es el de **este** scan es **nuevo**. Un `critical`
  que ya existía (mismo `dedupe_key`, `first_seen` anterior) **no** re-dispara — es
  exactamente lo que evita el spam por ciclo (§5.2 spec).
- Un `dedupe_key` previo que **no** reaparece pasa a `status='fixed'` (lo hace el
  UPSERT de 06 al persistir el re-scan; **sin alerta**, fila §6 del spec).

## 5. Alertas — canales, contenido y secretos

### 5.1 Canales (`dispatch_alert`)

Según `notification_prefs` del owner (a nivel cuenta, no por dominio;
[06](../06-data-model/plan.md) §2.3):

- **Resend (email):** si `email_enabled` (default `true`). Vía `ResendEmailService`
  (impl del `EmailService` ABC) despachado por el command-bus existente
  (`SendEmailCommand`, en `src/common/application/commands/common.py`, resuelto por
  `SendEmailHandler` de `src/messaging/`, como referencia).
- **Slack (webhook):** si `slack_webhook_url` no es nulo. **POST JSON plano**
  (`{"text": …}`) vía el helper net-new `post_unsigned_webhook(...)`
  (`src/common/application/helpers/webhooks/unsigned.py`): un
  `httpx.AsyncClient.post` envuelto en `catch_httpx_exceptions` que devuelve un
  `WebhookDeliveryResult` (fire-and-forget). **No** se usa `deliver_webhook` (§0):
  ése firma con HMAC y exige `secret`/`event_id`/`timestamp`, headers que un Slack
  *incoming webhook* rechaza/ignora; Slack no valida firma standard-webhooks.
- Para el **seed gov** (sin `owner_user_id`) no hay destinatario → **no se emite
  alerta** (el board gov no notifica a nadie; solo se reescanea para refrescar
  grados).

Cada despacho exitoso/fallido se **registra en `alerts`** (`AlertORM`: `user_id`,
`site_id`, `scan_id`, `type`, `message`, `channel`, `sent_at`) vía `AlertRepository`.

### 5.2 In-app = recorte (documentado)

**No** se construye un centro de notificaciones in-app (sin tabla de "inbox", sin
endpoint `/notifications`, sin badge). Solo email + Slack. Es un recorte de alcance
explícito de la spec §5.1; queda como riesgo abierto §7.5 por si post-demo se pide.

### 5.3 Contenido redactado (`build_alert_payload`)

La alerta identifica **hostname**, **grado anterior → nuevo** y la lista de
`critical` nuevos (tipo + categoría + severidad + `impact` resumido). **Nunca**
incluye el payload de explotación crudo (mismo principio de redacción que `/r/[token]`
en [09-reporting](../09-reporting/spec.md)): el canal de alerta no filtra exploits
reales contra el sitio del usuario. `build_alert_payload` toma `FindingRecord[]` y
emite solo campos seguros (descarta `evidence` cruda).

### 5.4 Secretos / settings (fail-loud)

Se añaden a `src/common/settings.py` siguiendo el estilo existente (todos
`str | None = None`, validados en uso, no inventados):

```python
# -> ALERTS
RESEND_API_KEY: str | None = None          # Resend transaccional (§5.1)
MONITOR_CRON: str = "0 */6 * * *"          # cron del CronJob de SAQ (§4.1)
MONITOR_LEVEL_DEFAULT: str = "basico"      # nivel del seed gov (guard 01 §3.2)
# NO se añade RESEND_FROM: el remitente ya es DEFAULT_FROM_EMAIL (settings.py:86)
# slack_webhook_url NO es global: vive por usuario en notification_prefs (06)
```

> **Remitente: se reutiliza `DEFAULT_FROM_EMAIL`, no se añade `RESEND_FROM`.**
> `settings.py` ya expone `DEFAULT_FROM_EMAIL: str | None = None`, y
> `SendEmailHandler` ya lo usa como sender por defecto
> (`sender=command.from_email or settings.DEFAULT_FROM_EMAIL`,
> `src/messaging/application/commands/send_email.py`). Como `ResendEmailService` es
> una **segunda impl del mismo `EmailService` ABC** despachada por el **mismo**
> command-bus, hereda ese mismo sender; introducir `RESEND_FROM` duplicaría el
> concepto de remitente y abriría la puerta a que email SMTP y email Resend salgan
> con `From` distintos. El remitente verificado en Resend se configura, pues, en
> `DEFAULT_FROM_EMAIL`.
>
> El `slack_webhook_url` **no** es un setting global: es por usuario en
> `notification_prefs`. Solo Resend (servicio compartido) tiene clave global
> (`RESEND_API_KEY`).

## 6. Suite de tests — `backend/tests/sites/` y `backend/tests/scans/`

Convención del repo: `tests/<área>/...`, pytest, librería **`expects`**, funciones
standalone, AAA, fixtures por función. Dominio puro = sin I/O; repo/cron = async
contra `doxiq_test` (`conftest` con `create_all` sobre `Base.metadata`). Las
carpetas `tests/sites/` y `tests/scans/` se crean aquí (hoy existen `api`, `auth`,
`common`, `tenants`).

| Archivo | Capa | Asserts |
|---|---|---|
| `tests/sites/infrastructure/test_ranking_order.py` | repo (DB) | `list_gov_ranking` ordena `overall_grade ASC, penalty_raw DESC`; empates en grado se desempatan por `penalty_raw`; excluye `is_gov=false` y `visibility='private'`; filtra por `country`. |
| `tests/sites/application/test_ranking_partial_cap.py` | use case (mock repo) | `GetRanking` propaga el flag `partial` cuando `status='partial'`; **no recalcula** el grado (lo lee tal cual de `overall_grade`). |
| `tests/sites/application/test_watchlist_crud.py` | use case (mock repo) | `add` crea fila `monitor=false`; `toggle` alterna `monitor`; `remove` usa **id de fila**; aislado por `user_id`. |
| `tests/sites/application/test_alert_prefs.py` | use case (mock repo) | `update_alert_prefs` upsert 1:1 por `user_id`; default `{email_enabled:true, slack_webhook_url:null}`. |
| `tests/scans/domain/test_grade_delta.py` | dominio (puro) | `compare_grade` → `True` solo si empeora (B→D sí, B→A no, B→B no); F es el peor. |
| `tests/scans/application/test_evaluate_site_alerts.py` | use case (mock repo) | dispara si bajó el grado; dispara si hay `critical` con `first_seen==este scan`; **no** dispara para un `critical` preexistente (mismo `dedupe_key`, `first_seen` anterior); `dedupe_key` ausente ⇒ no dispara (es `fixed`). |
| `tests/scans/application/test_monitor_cron.py` | cron/use case (mock cola) | el cron reencola `watchlist.monitor=true` ∪ seed gov; gov siempre `level=basico`; forzar nivel activo gov ⇒ `AutomaticActiveScanError`; re-encolar un `(site,level)` con scan vivo ⇒ no-op (idempotencia). |
| `tests/scans/infrastructure/test_slack_alert.py` | infra (mock httpx) | `post_slack_alert` hace POST **JSON plano** (`{"text": …}`, sin headers de firma HMAC) a la URL vía `post_unsigned_webhook`; payload **redactado** (sin `evidence` cruda); fallo de red ⇒ `WebhookDeliveryResult(delivered=False)` sin lanzar. |
| `tests/scans/infrastructure/test_resend_email.py` | infra (mock httpx) | `ResendEmailService.send_email` pega a Resend con `RESEND_API_KEY` y `sender=DEFAULT_FROM_EMAIL` (no un `RESEND_FROM` propio); sin clave ⇒ degrada (no rompe el ciclo de monitoreo). |
| `tests/scans/infrastructure/test_alert_log.py` | repo (DB) | cada despacho deja una fila en `alerts` con `channel` correcto, `site_id`/`scan_id`/`user_id` y `sent_at`. |

Los tests de **endpoint** (`/ranking` excluye `private`, `/watchlist` CRUD + 404
IDOR, `/me/alerts`) viven en [12-api](../12-api/plan.md) §8
(`tests/api/test_ranking_health.py`, `test_watchlist.py`, `test_alerts.py`); aquí se
cubren query, decisión de alerta, cron y canales. El invariante "automático solo
pasivo" tiene además su test transversal `test_scheduler_passive.py` en
[01-legal-ethics](../01-legal-ethics/plan.md) §4.

## 7. Secuencia de build

1. **06-data-model**: `sites`/`scans`/`findings`/`watchlist`/`notification_prefs`/
   `alerts` + índice de leaderboard + `dedupe_key`/`first_seen` a nivel site.
   (Bloquea todo.)
2. **Settings + seed data**: claves de §5.4 en `settings.py`; `seed/gob_mx.txt` con
   ~30–50 dominios; fixtures pre-horneados cargados por `command.load` (extensión de
   [06](../06-data-model/plan.md) §2.7). Test de carga (06).
3. **Ranking** (`src/sites/`): `RankingRepository` + `SQLRankingRepository` +
   `GetRanking` con cap parcial. → `test_ranking_order`, `test_ranking_partial_cap`.
4. **Watchlist + prefs** (`src/sites/`): use-cases CRUD + alert-prefs. →
   `test_watchlist_crud`, `test_alert_prefs`. (Los endpoints los expone 12.)
5. **Canales** (`src/scans/infrastructure/` + `src/common/.../webhooks/unsigned.py`):
   `ResendEmailService`, `post_slack_alert` (POST plano vía `post_unsigned_webhook`,
   **no** `deliver_webhook`), `build_alert_payload` redactado, log en `alerts`. →
   `test_slack_alert`, `test_resend_email`, `test_alert_log`.
6. **Detección + alerta** (`src/scans/`): `grade_delta`, `EvaluateSiteAlerts`,
   `dispatch_alert`. → `test_grade_delta`, `test_evaluate_site_alerts`.
7. **Cron** (`config/tasks.py` + `MonitorCronHandler` + `SeedGovHandler`): registrar
   `CronJob` con guard legal. → `test_monitor_cron` (+ `test_scheduler_passive` de 01).
8. **Frontend** ([13-frontend](../13-frontend/spec.md)): Hall of Shame en `/`,
   dashboard watchlist, `/sites/[id]` consumiendo 12 vía BFF. (No bloqueante de
   backend.)

La feature pasa a `implemented`/coverage>0 cuando el cron se registra, los canales
despachan + loguean, la decisión de alerta es a nivel site, y **toda** la suite §6
pasa.

## 8. Decisiones y riesgos abiertos

1. **✅ SAQ `CronJob` (no rq-scheduler, no APScheduler, no proceso aparte).** El
   monitoreo recurrente se registra en `worker_settings["cron_jobs"]` (hoy `[]`);
   una sola cola SAQ es la fuente de verdad (spec §4.1, reconciliado en
   [01-legal-ethics](../01-legal-ethics/plan.md) §6.2).
2. **✅ Comparación a nivel site, no a nivel scan.** `dedupe_key`/`first_seen` son
   por site ([06](../06-data-model/plan.md) §3.3); así "nuevo critical" se distingue
   de "ya estaba" y no se alerta cada ciclo (spec §5.2). Capa de `EvaluateSiteAlerts`.
3. **✅ Resend como 2ª impl de `EmailService`; Slack = POST plano (NO
   `deliver_webhook`).** No se crea un sistema de notificaciones paralelo: el email
   va por el command-bus existente (`SendEmailCommand` en
   `src/common/application/commands/common.py`, `SendEmailHandler`/`EmailService` en
   `src/messaging/`), reutilizando `DEFAULT_FROM_EMAIL` como remitente (§5.4). Para
   Slack **no** se reutiliza `deliver_webhook`: ése es un emisor **firmado**
   (standard-webhooks, exige `secret`/`event_id`/`timestamp` y emite headers HMAC),
   y un Slack *incoming webhook* espera un POST JSON plano sin firma. Se añade el
   helper net-new `post_unsigned_webhook` (`httpx` + `catch_httpx_exceptions` →
   `WebhookDeliveryResult`) que conserva el contrato fire-and-forget "nunca lanza"
   sin la firma.
4. **✅ Board público = solo pasivo.** El query filtra `is_gov=true AND
   visibility='public'`; un activo de usuario nunca entra. Invariante de
   [01-legal-ethics](../01-legal-ethics/plan.md); aquí se aplica, no se justifica.
5. **Alertas in-app = recorte explícito.** Solo email/Slack para el demo (spec §5.1).
   Riesgo si post-demo se pide un inbox: requeriría tabla + endpoint + UI nuevos.
6. **✅ Evaluación de alerta encadenada al fin del scan, no al tick del cron;
   origen del scan = `requested_by IS NULL` (contrato fijado en §4.2).** El cron
   solo **reencola**; `EvaluateSiteAlerts` corre cuando el scan **de origen cron**
   termina y ya tiene grado escrito. La distinción "scan de monitoreo" vs "scan
   manual" **no** queda abierta a coordinar: este plan **fija** que el cron encola
   con `requested_by=NULL` (la columna ya es nullable en [06](../06-data-model/plan.md)
   §3.2, hoy para "gov anónimo") y que un `requested_by` no-nulo ⇒ scan manual.
   `EvaluateSiteAlerts` se gatea con `scan.requested_by IS NULL` y no se añade
   columna `origin`/`trigger` nueva. [05-agent-team](../05-agent-team/spec.md) debe
   **respetar** ese contrato al encolar (manual ⇒ `requested_by=user_id`; cron/seed
   ⇒ NULL), pero el contrato es de este plan, no una incógnita.
7. **Carrera fixtures vs scan real (no camino crítico).** Los fixtures pre-horneados
   pueblan el board; los scans reales gob.mx lo **sobrescriben solo si terminan a
   tiempo** y se pre-ejecutan en el VPS antes del demo (spec §2.4). Riesgo nulo para
   la narrativa: el fallback siempre es el fixture.
8. **`previous_completed_scan` y el primer scan de un site.** El primer scan de un
   site (sin previo) **no** dispara alerta de "bajó el grado" (no hay base de
   comparación); sí puede disparar por `critical` nuevo (todo `first_seen` es de ese
   scan). Documentado para que no se confunda con un bug.
