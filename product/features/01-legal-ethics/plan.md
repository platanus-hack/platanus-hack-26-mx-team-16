---
feature: legal-ethics
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §1–§5; 02-attack-levels §4–§5; 04-scanning-engine §; 06-data-model §3.2; 08-ranking-watchlists §2.2/§4.1; 12-api (POST /scans, AuthZ)
---

# Owliver — Capa legal/ética — plan de implementación (CÓMO)

> La spec de esta feature es un **invariante transversal**, no un módulo con
> endpoints propios. Su implementación se reparte entre 04 (worker), 08
> (scheduler/ranking), 12 (API) y 13 (frontend). Este plan hace dos cosas:
> (1) **centraliza** la fuente de verdad legal en un paquete `common/legal` que
> todos los caminos importan —para que el invariante no quede esparcido ni se
> pueda divergir—, y (2) define la **suite de tests de invariante** que es lo que
> convierte "pasivo/atestado/privado" en algo *aplicado en código*, no en prosa.
>
> Principio operativo: **un control que no tiene test que lo rompa cuando se
> viola, no existe**. El entregable medular de esta feature son los tests del §5.

## 0. Estado de las dependencias

Esta capa se monta sobre código que **aún no existe** en el repo (el codebase hoy
es solo el fundamento SaaS). Orden real de habilitación en §6. Hoy:

- No hay tabla `scans`/`sites` → las define [06-data-model](../06-data-model/spec.md).
- No hay módulo `scans`, worker de pentest, ni scheduler gov.
- **Sí** existe infra reutilizable que evita reinventar:
  - Rate-limiter Redis: `backend/src/common/infrastructure/services/rate_limiter.py`
    + factory `create_rate_limit_dependency(limit, window, strategy, key_func)` en
    `backend/src/common/infrastructure/dependencies/rate_limit.py`. **Se reutiliza
    tal cual** para el límite de API (§4.5) — no se introduce `slowapi`.
  - Cola de jobs: **SAQ** (`backend/config/tasks.py`, `Queue.from_url`). El
    scheduler gov se implementa como **cron de SAQ** (`CronJob`); ver §6.
  - Enums/constantes de dominio: `backend/src/common/domain/enums/`,
    `backend/src/common/domain/constants/`.
  - Errores: extender `DomainError` (code, message, status_code).

## 1. Mapa de enforcement (qué control vive dónde)

Los cinco controles de la spec, su punto de aplicación y el feature dueño. Este
plan es la **spec-de-registro del comportamiento legal** que cada hermana debe
cumplir; el test de invariante (§5) es transversal y vive aquí.

| # | Control (spec) | Punto de aplicación (código) | Dueño | Test de invariante |
|---|---|---|---|---|
| 2.1 | Atestación persistida + gate | `enqueue_scan` use case + `POST /scans` | 12-api | `test_active_requires_attestation`, `test_attestation_persisted` |
| 2.2 | Automático = solo pasivo | seed/cron SAQ del ranking gov | 08 | `test_scheduler_only_emits_basico` |
| 2.3 | Ranking público = solo pasivo | `default_visibility()` al crear scan + filtro `WHERE visibility='public'` en `/ranking` | 08 + 12 | `test_active_scan_is_private`, `test_ranking_excludes_private` |
| 3 | "Pasivo" = whitelist tools+flags + robots | `resolve_tools(is_gov, level)` + robots policy en el worker | 04 + 02 | `test_gov_passive_tool_whitelist`, `test_robots_disallow_excluded` |
| 2.5/4 | Rate-limit (API + worker) + UA | dependency en `POST /scans` + flags `-rl`/delay en `run_tool()` | 12 + 04 | `test_api_scan_rate_limit_429`, `test_scanner_user_agent` |

## 2. Código net-new que ESTA feature posee — `backend/src/common/legal/`

Fuente de verdad única, sin dependencias de capa (importable por use case, worker
y scheduler sin ciclos). Todo **puro** (sin I/O) salvo donde se indica.

```
backend/src/common/domain/legal/
  __init__.py
  constants.py        # UA, límites, niveles automáticos permitidos
  host.py             # clasificación is_gov / sensible por sufijo
  levels.py           # predicados activo/pasivo + visibilidad por defecto
  passive_profile.py  # contrato legal del perfil pasivo gov (allow-list)
  exceptions.py       # AttestationRequiredError, AutomaticActiveScanError
  robots.py           # Protocol RobotsPolicy (contrato; impl en 04)
backend/src/common/domain/services/
  attestation_gate.py # check puro: nivel activo ⇒ authorized=True obligatorio
```

### 2.1 `constants.py`
```python
SCANNER_USER_AGENT = "Owliver-Scanner/1.0 (+contacto)"   # §2.5 — único, importado por worker + robots
API_SCAN_RATE_LIMIT = (5, 3600)                          # (limit, window_s) — §4.1
WORKER_NUCLEI_RATE = 150                                  # -rl por defecto hacia el target — §4.2 (04 lo aplica)
WORKER_REQUEST_DELAY_MS = 200                             # delay ffuf/katana — §4.2
```

### 2.2 `host.py` — clasificación (afecta copy, visibilidad y scheduler)
```python
def is_gov_hostname(hostname: str) -> bool: ...     # sufijo .gob.mx (case-insensitive, normaliza puerto/trailing dot)
def is_sensitive_hostname(hostname: str) -> bool:   # is_gov ∪ otros marcados sensibles → copy reforzado §2.4
@dataclass(frozen=True)
class HostFlags: hostname: str; is_gov: bool; is_sensitive: bool
def resolve_host_flags(url: str) -> HostFlags: ...  # 06 lo usa para poblar sites.is_gov
```

### 2.3 `levels.py` — el predicado que decide automático/público
```python
AUTOMATIC_ALLOWED_LEVELS = frozenset({ScanLevel.basico})   # §2.2 — el scheduler solo puede emitir esto
def is_active(level: ScanLevel) -> bool: ...               # intermedio | avanzado
def default_visibility(*, is_gov: bool, level: ScanLevel, has_owner: bool) -> ScanVisibility:
    # §2.3: gov & básico & sin owner ⇒ public; cualquier otro ⇒ private
```
> `ScanLevel`/`ScanVisibility` los define 06 en el dominio `scans`; `legal` solo
> aporta los **predicados**. Si 06 aún no existe al construir, viven temporalmente
> aquí y 06 los reexporta.

### 2.4 `passive_profile.py` — contrato legal de "pasivo" (allow-list)
Congela, en código, la definición de §3 de la spec para `(is_gov=True, basico)`.
04 importa esto como **fuente de verdad** del perfil pasivo; 04 posee los perfiles
intermedio/avanzado. Allow-list, no deny-list.
```python
GOV_PASSIVE_PROFILE = PassiveProfile(
    tools=frozenset({"testssl", "security-headers", "whatweb", "nuclei"}),
    nuclei_tags_allow=("ssl", "tech", "http-misconfig"),
    nuclei_tags_exclude=("intrusive", "dos", "fuzzing", "network"),
    spider=False, katana=False, zap_spider=False,    # deshabilitados para gov
    root_only=True, honor_robots=True,
)
def assert_within_passive_profile(tools: Iterable[ToolInvocation]) -> None:
    # lanza si alguna tool/flag resuelta cae fuera del allow-list → usado por el test §5
```

### 2.5 `attestation_gate.py` + `exceptions.py`
```python
class AttestationRequiredError(DomainError):  code="attestation_required"; status_code=422
class AutomaticActiveScanError(DomainError):  code="automatic_active_forbidden"; status_code=500  # guard del scheduler

def enforce_attestation(*, level, authorized: bool) -> None:
    if is_active(level) and not authorized:
        raise AttestationRequiredError(...)   # sin atestación, el activo no se encola
```

## 3. Cableado de cada control

### 3.1 Gate de atestación (2.1) — en el use case, no en el router
- `enqueue_scan` use case (lo crea 12/06) llama `enforce_attestation(level, authorized)`
  **antes** de tocar la cola; al persistir el scan setea `authorized=True`,
  `authorized_at=now`, `requested_by=current_user.id` (columnas de `scans`, 06 §3.2).
- El router `POST /scans` solo traduce `AttestationRequiredError` → 422 vía el
  handler de errores existente. La UI/copy del gate es de [13-frontend](../13-frontend/spec.md).

### 3.2 Automático solo pasivo (2.2) — guard duro en el scheduler SAQ
- El task de seed/cron gov (08) construye el job con `level=ScanLevel.basico`
  **hardcodeado**; antes de encolar afirma
  `assert level in AUTOMATIC_ALLOWED_LEVELS else raise AutomaticActiveScanError`.
- Es invariante de código: el seed no acepta `level` como parámetro configurable.

### 3.3 Visibilidad (2.3) — default al crear + filtro en lectura
- Al crear cualquier scan se setea `visibility = default_visibility(...)`.
- `GET /ranking` (08/12) filtra `WHERE visibility='public'`; un activo de usuario
  nunca entra. Publicar uno exige `POST /scans/{id}/share` → `/r/{token}` (09/12).

### 3.4 Whitelist + robots (3) — en el worker (04), validado contra el contrato
- `resolve_tools(is_gov, level)` (04) devuelve la lista concreta de invocaciones.
  Para gov/básico, esa lista **debe** validar `assert_within_passive_profile`.
- `RobotsPolicy` (Protocol en `legal/robots.py`, impl en 04): parsea `robots.txt`
  con `SCANNER_USER_AGENT` **antes de cualquier request** y excluye `Disallow`.
  Defensa en profundidad: al `owasp_agent` solo se le pasan las tools pasivas, así
  ni siquiera puede elegir un activo contra gov (02 §4).

### 3.5 Rate-limit + UA (2.5/4)
- **API (por usuario):** en `POST /scans`, reusar la factory existente:
  ```python
  scan_rate_limit = create_rate_limit_dependency(
      limit=API_SCAN_RATE_LIMIT[0], window=API_SCAN_RATE_LIMIT[1],
      key_func=lambda r: f"scans:{current_user_id(r)}")
  ```
  El handler existente ya responde 429 con `Retry-After`.
- **Worker (por target):** Nuclei `-rl WORKER_NUCLEI_RATE`, delay
  `WORKER_REQUEST_DELAY_MS` en ffuf/katana, y `SCANNER_USER_AGENT` en todo request
  saliente — aplicado en `run_tool()` (04).

## 4. Suite de invariante (el entregable medular) — `backend/tests/legal/`

Tests transversales que fallan si cualquier camino viola la capa legal. Siguen la
convención del repo (`tests/<área>/...`, pytest async).

| Archivo | Asserts |
|---|---|
| `test_attestation.py` | activo sin `authorized` ⇒ `AttestationRequiredError`/422 y **no** se encola; aceptado ⇒ `authorized/authorized_at/requested_by` persistidos; pasivo no exige atestación |
| `test_scheduler_passive.py` | el seed/cron gov solo emite `level=basico`; forzar otro nivel ⇒ `AutomaticActiveScanError` |
| `test_visibility.py` | gov+básico ⇒ `public`; intermedio/avanzado o con owner ⇒ `private`; `GET /ranking` excluye `private` (property test sobre combinaciones) |
| `test_passive_profile.py` | `resolve_tools(is_gov=True, basico)` ⊆ `GOV_PASSIVE_PROFILE`; ZAP-spider/katana ausentes; Nuclei excluye `intrusive,dos,fuzzing,network`; cualquier tool fuera del allow-list ⇒ falla |
| `test_robots.py` | paths `Disallow` excluidos antes de request; UA usado = `SCANNER_USER_AGENT` |
| `test_rate_limit_and_ua.py` | 6º scan/h del mismo usuario ⇒ 429; todo request saliente lleva el UA identificable |

Cada hermana añade además sus tests de endpoint/integración; estos son el contrato
mínimo que ninguna refactor puede romper.

## 5. Secuencia de build

1. **06-data-model**: tabla `scans` con `level`, `visibility`, `authorized`,
   `authorized_at`, `requested_by`; `sites.is_gov`. (Bloquea todo.)
2. **`common/legal`** (esta feature): constantes, `host`, `levels`,
   `passive_profile`, `attestation_gate`, excepciones. Tests unitarios puros.
3. **12-api**: `enqueue_scan` + `POST /scans` con gate + rate-limit; filtro de
   visibilidad en lectura. → `test_attestation`, `test_rate_limit`.
4. **04-scanning-engine**: `resolve_tools` valida contra `passive_profile`;
   `RobotsPolicy`; UA y `-rl` en `run_tool()`. → `test_passive_profile`, `test_robots`.
5. **08-ranking-watchlists**: cron SAQ con guard `AUTOMATIC_ALLOWED_LEVELS`;
   `/ranking` solo `public`. → `test_scheduler_passive`, `test_visibility`.
6. **13-frontend**: copy del gate + refuerzo rojo para `is_sensitive` (no bloqueante).

La capa se considera `implemented`/coverage>0 solo cuando **toda** la suite §4 pasa.

## 6. Decisiones / reconciliaciones (todas resueltas — 2026-06-20)

1. **✅ Conflicto gov-activo — RESUELTO (2026-06-20).** Esta spec (§1 nota, §2.4)
   **descarta** el bloqueo `is_gov → 422 hard` y declara el activo gov **permitido
   bajo atestación** (privado + copy reforzado, no bloqueado). [12-api](../12-api/spec.md)
   se **reconcilió** a esta decisión: se eliminó el 422-por-gov de *Enforcement
   legal* y de las tablas de códigos; el único 422 del gate es ahora `activo sin
   authorized=true` (`attestation_required`). `enforce_attestation` (§2.5) implementa
   exactamente eso; `is_gov` solo afecta copy (13) y `default_visibility` (§2.3).
2. **✅ Arq → SAQ — RESUELTO (2026-06-20).** Toda referencia a Arq en las specs
   vivas (`spec.md`, 04, 05, 06, 08, 12) se migró a **SAQ** (asyncio-native,
   Redis-backed, cron `CronJob`, dedupe por job key). Cero Arq en el producto; el
   `_archive/` conserva la justificación histórica. El scheduler gov y su guard
   `AUTOMATIC_ALLOWED_LEVELS` corren sobre el cron de SAQ.
3. **✅ slowapi → RateLimiter existente — RESUELTO (2026-06-20).** La mención a
   `slowapi` estaba en el **§4 de esta spec** (no en 12-api); se reescribió para
   reutilizar el `RateLimiter` Redis del fundamento
   (`create_rate_limit_dependency`, `fixed_window` `INCR`+TTL, `5/3600` por
   usuario). 12-api ahora **documenta el detalle** (`429` + `Retry-After`). No se
   añade `slowapi`.