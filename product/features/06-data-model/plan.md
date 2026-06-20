---
feature: data-model
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §2–§6; 05-agent-team §; 07-scoring §9; 08-ranking-watchlists §2/§4/§5; 10-realtime-live-view §; 12-api §
---

# Owliver — Modelo de datos del motor de pentest — plan de implementación (CÓMO)

> Este es el artefacto de la **hora 0**: el esquema Postgres del motor de pentest
> y los contratos Pydantic congelados (`finding.py`). Es el carril que **desbloquea
> a todos los demás** (P1–P4 corren en paralelo solo una vez que las tablas y los
> shapes existen, ver [05-agent-team](../05-agent-team/spec.md) §6). El entregable
> medular no es "muchas tablas", sino **(1)** un esquema que persiste exactamente
> lo que el worker produce sin re-litigar columnas más tarde, y **(2)** `finding.py`
> congelado para que P2 (parsers), P3 (agéntico) y P4 (reporte) puedan codificar
> contra el mismo contrato sin coordinarse en caliente.
>
> Principio operativo: **el LLM no escribe en este esquema columnas calculadas.**
> Score, `dedupe_key`, `is_gov` y la clasificación de categoría se computan en
> Python determinista antes de tocar la DB (spec §1). El modelo solo persiste.

## 0. Estado de las dependencias

Este esquema se monta sobre un repo que hoy es **solo el fundamento SaaS**. No
existe ninguna tabla del SCAN, ningún módulo de pentest, ningún worker. Lo que
**sí** existe y se reutiliza tal cual (no se reinventa):

- **Base ORM + mixins:** `backend/src/common/database/mixins/common.py` aporta
  `Base` (DeclarativeBase), `UUIDPrimaryKeyModelMixin` (PK `uuid` con `default=uuid4`),
  `TimeStampedModelMixin` (`created_at`/`updated_at` con `server_default=func.now()`),
  el combinado `UUIDTimestampMixin` y `SoftDeleteMixin`. Todos los modelos del SCAN
  los heredan: **nada de PK serial ni timestamps a mano** (cumple la decisión de UUID
  PK de la spec §3.2).
- **Registro de modelos:** `backend/src/common/database/models/__init__.py` importa
  cada `*ORM` y lo expone en `__all__` para que Alembic y `conftest` los vean en
  `Base.metadata`. Las tablas nuevas deben quedar enganchadas a este mismo
  `Base.metadata` (es lo que `tests/conftest.py` usa con `create_all`).
- **Enums de dominio:** `backend/src/common/domain/enums/base_enum.py`
  (`BaseEnum(Enum)`, valores `str`); convención: un archivo por área, persistidos
  como `String` con `default=str(MiEnum.VALOR)` (ver `models/tenants/tenant.py`).
- **Repos:** abstractos `ABC` en `<modulo>/domain/repositories/`, impl
  `@dataclass SQLXxxRepository(session: AsyncSession)` en
  `<modulo>/infrastructure/repositories/sql_*.py` (patrón en
  `src/users/infrastructure/repositories/sql_user.py`, con `atomic_transaction`).
- **Migraciones:** Alembic en `backend/src/common/database/versions/`
  (`script.py.mako`, una sola revisión `…_initial.py` hoy). `just migrate-backend-new`.
- **CLI de fixtures:** `backend/command.py` (typer; `load` / `dump` / `flush_and_load`,
  estilo Django `loaddata`/`dumpdata`). Aquí extendemos su `load` para entender los
  modelos del leaderboard.

## 1. Decisión de módulos — dónde viven estas tablas

El boilerplate SaaS pone su modelo de datos genérico en
`src/common/database/models/`. **No mezclamos** el modelo del SCAN ahí: el motor de
pentest es un dominio de negocio propio, no infraestructura compartida. Siguiendo la
organización de los módulos existentes (`auth`, `users`, `tenants` →
`domain/application/infrastructure/presentation`), creamos **módulos feature-first**:

| Módulo | Tablas que posee | Razón |
|---|---|---|
| `src/sites/` | `sites`, `watchlist`, `notification_prefs` | Catálogo de dominios + suscripción/preferencias del usuario. Es la entidad "sujeto del escaneo"; su ciclo de vida (registro, `is_gov`, owner) es independiente del scan. |
| `src/scans/` | `scans`, `findings`, `agentic_surface`, `scan_events`, `alerts`, `public_reports` | El núcleo del motor: una ejecución y todo lo que produce (hallazgos, superficie, eventos, alertas emitidas, links compartibles). Cohesión alta; todo gira alrededor de `scan_id`. |
| `src/auth/` (existente) | `magic_tokens` | El magic-link es **autenticación**, no parte del motor. Vive con el resto del flujo de login ([11-auth-magic-link](../11-auth-magic-link/spec.md)), no en `scans`. |

> **Por qué dos módulos y no uno:** `sites` tiene lectores que `scans` no
> (leaderboard, watchlist, scheduler gov de [08-ranking-watchlists](../08-ranking-watchlists/spec.md)),
> y `scans` referencia `sites` pero no al revés (salvo el puntero denormalizado
> `sites.latest_scan_id`). Separarlos mantiene el grafo de dependencias en una sola
> dirección y evita un módulo `scans` que lo sepa todo.
>
> **`finding.py` y `events.py` NO van en un módulo de feature.** Son contratos
> compartidos congelados que P1–P4 importan; viven en
> `src/scans/domain/contracts/` (ver §3) para que cualquier carril los importe sin
> arrastrar infraestructura. Son Pydantic puro, sin I/O.

Cada modelo ORM se registra además en `src/common/database/models/__init__.py`
(import + `__all__`) **o** el módulo expone su propio paquete de modelos que
`conftest`/Alembic importen — usamos lo primero por consistencia con el registro
actual de `Base.metadata` (todos los `*ORM` se descubren desde un único punto).

## 2. Mapa de archivos a crear

### 2.1 Enums de dominio — `src/common/domain/enums/scans.py`

Un único archivo de enums del SCAN (espeja `enums/tenants.py`), `BaseEnum` con
valores `str` que coinciden **verbatim** con el DDL de la spec §2:

```python
class ScanLevel(BaseEnum):        basico | intermedio | avanzado          # §3.2
class ScanStatus(BaseEnum):       queued | running | partial | done | failed | cancelled
class ScanVisibility(BaseEnum):   public | private
class AgenticStatus(BaseEnum):    no_surface | detected_not_tested | tested  # §5.2
class FindingSource(BaseEnum):    owasp | agentic
class FindingSeverity(BaseEnum):  critical | high | medium | low | info
class FindingConfidence(BaseEnum): alta | media | baja
class FindingStatus(BaseEnum):    open | fixed | accepted
class AgenticType(BaseEnum):      chatbot | prompt_input | search_ai        # §3.4
class ScanEventType(BaseEnum):    agent_status | tool_start | tool_end | finding | phase | score | done | error
class AlertChannel(BaseEnum):     email | slack                            # §3.6
```

> Estos enums son la fuente de verdad de las columnas y de los `Literal[...]` de
> `finding.py`. La capa legal ([01-legal-ethics](../01-legal-ethics/plan.md) §2.3)
> consume `ScanLevel`/`ScanVisibility` como predicados — los **reexporta** desde
> aquí, no los duplica.

### 2.2 Contratos Pydantic congelados — `src/scans/domain/contracts/`

| Archivo | Contenido | Congelado en hora |
|---|---|---|
| `finding.py` | `Finding`, `AgenticResult` (shapes verbatim de spec §5.1/§5.2) | 0–2 |
| `events.py` | `ScanEvent` Pydantic (`seq`, `ts`, `type` discriminante, `payload`, `progress int|None`) | 0–2 |
| `__init__.py` | re-exporta `Finding`, `AgenticResult`, `ScanEvent` para imports cortos | — |

`finding.py` se escribe **verbatim** según spec §5; los `Literal[...]` usan los
mismos valores que los enums de §2.1 (no se importa el enum en el `Literal` para
mantener el contrato auto-contenido y serializable, igual que `domain/models/user.py`
usa Pydantic sin acoplar al ORM).

### 2.3 Módulo `src/sites/`

```
src/sites/
  domain/
    models/site.py              # Site (Pydantic) — entidad de dominio
    models/watchlist.py         # WatchlistEntry
    models/notification_prefs.py# NotificationPrefs
    repositories/site.py        # SiteRepository(ABC)
    repositories/watchlist.py   # WatchlistRepository(ABC)
    repositories/notification_prefs.py
    services/host.py            # resolve_host_flags(url) -> hostname/is_gov (§3.1)
  infrastructure/
    repositories/sql_site.py    # @dataclass SQLSiteRepository(session)
    repositories/sql_watchlist.py
    repositories/sql_notification_prefs.py
    builders/site.py            # build_site(orm) -> Site
```

ORM (registrados en `common/database/models/__init__.py`):
- `models/site.py → SiteORM` (`sites`): hereda `UUIDTimestampMixin`; `url`, `hostname`
  (`index=True`), `is_gov bool` (**poblado al insertar** por `resolve_host_flags`,
  nunca del cliente — §3.1), `country`, `owner_user_id` FK→`users.uuid`
  `ondelete=SET NULL` nullable, `latest_scan_id` FK→`scans.uuid` nullable
  (`use_alter=True` por la referencia circular sites↔scans).
- `models/watchlist.py → WatchlistORM` (`watchlist`).
- `models/notification_prefs.py → NotificationPrefsORM` (`notification_prefs`):
  **PK = `user_id`** FK→`users.uuid` (no UUID propio; rompe el patrón de
  `UUIDTimestampMixin` a propósito porque es 1:1 con el usuario — usa
  `TimeStampedModelMixin` + `user_id` como `primary_key=True`), `email_enabled bool
  DEFAULT true server_default='true'`, `slack_webhook_url nullable`.

### 2.4 Módulo `src/scans/`

```
src/scans/
  domain/
    contracts/finding.py, events.py   # §2.2 (congelados hora 0)
    models/scan.py                    # Scan (Pydantic, con sub-scores/grade)
    models/finding.py                 # FindingRecord (Finding persistido + ids/status/dedupe)
    models/agentic_surface.py
    models/alert.py
    models/public_report.py
    repositories/scan.py              # ScanRepository(ABC)  — incl. enqueue idempotente
    repositories/finding.py           # FindingRepository(ABC) — UPSERT por (site_id, dedupe_key)
    repositories/scan_event.py        # ScanEventRepository(ABC) — append seq monótono
    repositories/agentic_surface.py
    repositories/alert.py
    repositories/public_report.py
    services/dedupe.py                # compute_dedupe_key(...) -> sha256 (§3.3)
  infrastructure/
    repositories/sql_scan.py, sql_finding.py, sql_scan_event.py,
                 sql_agentic_surface.py, sql_alert.py, sql_public_report.py
    builders/scan.py, finding.py, ...
```

ORM (cada uno hereda `UUIDTimestampMixin` salvo donde se note; registrados en
`common/database/models/__init__.py`):

| Archivo / ORM | Tabla | Notas de columnas y tipos |
|---|---|---|
| `scan.py → ScanORM` | `scans` | `uuid` PK UUID (≠ serial, §3.2); `site_id` FK→`sites.uuid`; `level/status/visibility/agentic_status` = `String` (enum); `requested_by` FK→`users.uuid` **nullable** (gov anónimo); `authorized bool`, `authorized_at`; `progress int default 0`; `current_phase text`; `tools_status/coverage` = `JSONB`; `web_score int`, `agentic_score int nullable`, `overall_score int`, `overall_grade char(1)`, `penalty_raw int`; `summary JSONB nullable` (ExecutiveSummary de Opus, §3.2 — 05 lo persiste, 09 lo lee); `started_at/finished_at/error` nullable. |
| `finding.py → FindingORM` | `findings` | `scan_id` FK→`scans.uuid`, `site_id` FK→`sites.uuid`; `source/severity/confidence/status` enum-`String`; `category String`; `cvss Float nullable`; `evidence/references` = `JSONB`; `affected_url/endpoint/param/impact/remediation/title/description`; `dedupe_key char(64)`; `first_seen/last_seen` (a nivel SITE, §3.3). |
| `agentic_surface.py → AgenticSurfaceORM` | `agentic_surface` | `scan_id`, `site_id` FK; `type` enum; `vendor nullable`; `location_url`; `inferred_model nullable`; `detected_at`. |
| `scan_event.py → ScanEventORM` | `scan_events` | `scan_id` FK; `seq int`; `ts`; `type` enum; `agent`, `tool nullable`, `severity nullable`, `message`, `payload JSONB`, `progress int nullable` (eventos `phase`/`score`, §3.5). **`UNIQUE (scan_id, seq)`** (§4). |
| `alert.py → AlertORM` | `alerts` | log de notificaciones: `user_id`, `site_id`, `scan_id` FK; `type`, `message`, `channel` enum, `sent_at`. |
| `public_report.py → PublicReportORM` | `public_reports` | `token` (`secrets.token_urlsafe(32)`, **UNIQUE** index, §4); `scan_id` FK; `created_at`, `expires_at`, `revoked_at nullable`. |

### 2.5 `magic_tokens` — en `src/auth/`

`src/auth/infrastructure/...` ya posee el flujo de sesión. Se añade
`MagicTokenORM` (`magic_tokens`) con **PK = `token_hash char(64)`** (no UUID; se
guarda el `sha256` del token opaco, **nunca** el plano — spec §3.7), `email`,
`expires_at`, `consumed_at nullable`, `created_at`. El canje
(`GET /auth/callback`) lo implementa [11-auth-magic-link](../11-auth-magic-link/spec.md);
aquí solo se fija la tabla.

### 2.6 Migración Alembic

Una sola revisión `…_scan_engine.py` (autogen + ajuste manual) en
`src/common/database/versions/`, con `down_revision` = la `initial` actual
(`720929e089fd`, único head SaaS). Debe incluir explícitamente los índices y constraints del §3
(Alembic **no** autogenera el partial unique index ni el orden del leaderboard;
se añaden a mano con `op.create_index(..., postgresql_where=...)`).

> **Nota — evitar multiple-heads:** como 06 es dueño del esquema y varias waves
> agregan migraciones en paralelo, **toda** revisión nueva debe encadenarse vía
> `autogenerate` partiendo del head actual único (`720929e089fd`, la migración
> `initial` del SaaS) para que features corriendo concurrentemente no produzcan
> múltiples heads. Antes de generar, verifica `alembic heads` = un solo head y
> rebasa contra él si otra wave ya avanzó la cadena.

### 2.7 Seed / fixtures del leaderboard — `backend/command.py` + `fixtures/`

Se extiende el `load` de `command.py` (hoy solo entiende `model: User`) para
reconocer `Site`, `Scan`, `Finding`, `AgenticSurface` y poblar 30–50 filas
pre-horneadas (grados ya calculados, findings agénticos plantados) que el
leaderboard muestra desde el segundo 0 y que los scans reales **sobrescriben** si
terminan a tiempo (detalle de contenido en
[08-ranking-watchlists](../08-ranking-watchlists/spec.md)). Las fixtures viven en
`fixtures/*.yaml` con `model/pk/fields` (formato existente). Comando:
`python command.py load fixtures` (o `flush_and_load` en dev).

## 3. Índices clave e idempotencia

Todos se crean en la migración del §2.6; cada uno tiene un test que lo ejerce (§5).

1. **Idempotencia de `POST /scans` — partial unique index:**
   ```python
   op.create_index(
       "uq_scans_active_per_site_level", "scans", ["site_id", "level"],
       unique=True, postgresql_where=sa.text("status IN ('queued','running')"))
   ```
   Impide que un doble-click / retry de red / seed re-ejecutado lancen dos
   escaneos concurrentes del mismo `(site, nivel)`. El 2º `POST` devuelve 200 con
   el `scan_id` vivo. **Segunda capa (worker):** la **job key de SAQ** derivada de
   `site_id+level` colapsa el doble-submit instantáneo que el índice no alcanza a
   cubrir; `scans.status='running'` actúa como lock. (Cola = **SAQ**, no Arq, ver
   [01-legal-ethics](../01-legal-ethics/plan.md) §6.2.)
2. **`UNIQUE (site_id, dedupe_key)` en `findings`** — el re-scan hace **UPSERT** por
   esta clave (`insert(...).on_conflict_do_update`); un finding que no reaparece
   pasa a `status='fixed'`; `first_seen/last_seen` se mantienen a nivel site. La
   `dedupe_key` la calcula `services/dedupe.compute_dedupe_key()` en Python en el
   parseo, antes de tocar la DB (`sha256(site_id|source|category|normalize(affected_url)|param|tool)`).
3. **`UNIQUE (scan_id, seq)` en `scan_events`** — única fuente de orden; habilita el
   replay determinista del live-view ([10-realtime-live-view](../10-realtime-live-view/spec.md)).
4. **Índice del leaderboard** sobre `scans` para el orden "peores primero":
   `CREATE INDEX … ON scans (overall_grade ASC, penalty_raw DESC)`, consultado con
   join a `sites WHERE is_gov` (o índice parcial sobre `sites.is_gov`). `penalty_raw`
   desempata cuando muchos `.gob.mx` colapsan al mismo grado (spec §3.2,
   [08-ranking-watchlists](../08-ranking-watchlists/spec.md)).
5. **`UNIQUE (token)` en `public_reports`**; índice en `sites.hostname` y en
   `sites.latest_scan_id`; índice en `findings.scan_id` y `findings.site_id`.

## 4. Contratos congelados — por qué en la hora 0

`finding.py` (`Finding` + `AgenticResult` + los enums `severity/confidence/source/category`)
es uno de los **5 artefactos innegociables de la hora 0–2**. Es el contrato entre:

- **P2 (parsers, [04-scanning-engine](../04-scanning-engine/spec.md)):** las
  tool-functions parsean salida cruda y devuelven `list[Finding]` ya construido en
  Python (los Sonnet **no** usan `response_model`).
- **P3 (agéntico, [03-agentic-surface](../03-agentic-surface/spec.md)):** el
  subagente devuelve `AgenticResult`, fuente de `scans.agentic_status`.
- **P4 (reporte, [09-reporting](../09-reporting/spec.md)):** renderiza `Finding[]`.

Cambiarlo después de la hora 2 **rompe a tres personas a la vez**; por eso se
congela primero. `events.py` (forma de `ScanEvent` con `seq` + `type` discriminante)
se congela junto, y corresponde 1:1 a la tabla `scan_events`
([10-realtime-live-view](../10-realtime-live-view/spec.md)).

## 5. Suite de tests — `backend/tests/scans/` y `backend/tests/sites/`

Convención del repo: `tests/<área>/...`, pytest, librería **`expects`**, funciones
standalone, AAA, fixtures por función. Los tests de dominio/contrato son puros; los
de repositorio son async contra la DB de test (`conftest` con `create_all` sobre
`Base.metadata`).

| Archivo | Capa | Asserts |
|---|---|---|
| `tests/scans/domain/test_finding_contract.py` | dominio (puro) | `Finding`/`AgenticResult` aceptan los shapes verbatim de spec §5; `severity`/`confidence`/`source` rechazan valores fuera del `Literal`; `AgenticResult.agentic_status` ∈ los 3 estados. |
| `tests/scans/domain/test_dedupe.py` | dominio (puro) | `compute_dedupe_key` es determinista, longitud 64, estable ante variaciones de URL que `normalize` colapsa, y cambia si cambia `source/category/param/tool`. |
| `tests/sites/domain/test_host.py` | dominio (puro) | `resolve_host_flags` → `is_gov=True` solo para sufijo `.gob.mx` (case-insensitive, normaliza puerto/trailing dot); `is_gov` **no** se acepta del cliente. |
| `tests/scans/infrastructure/test_scan_idempotency.py` | repo (DB) | dos `enqueue` del mismo `(site_id, level)` con `status∈{queued,running}` ⇒ el 2º **no** crea fila (IntegrityError capturado → devuelve la viva); cambiar a `done` permite re-encolar. |
| `tests/scans/infrastructure/test_finding_upsert.py` | repo (DB) | UPSERT por `(site_id, dedupe_key)` actualiza `last_seen` sin duplicar; finding ausente en re-scan ⇒ `status='fixed'`; `first_seen` se preserva. |
| `tests/scans/infrastructure/test_scan_events_seq.py` | repo (DB) | `UNIQUE (scan_id, seq)` viola al reinsertar `seq`; el append entrega orden monótono; replay por `scan_id` sale ordenado por `seq`. |
| `tests/scans/infrastructure/test_leaderboard_order.py` | repo (DB) | el query del ranking ordena `overall_grade ASC, penalty_raw DESC` y filtra `is_gov`; empates en grado/score se desempatan por `penalty_raw`. |
| `tests/scans/infrastructure/test_public_report_token.py` | repo (DB) | `token` único; lookup por token vivo OK; expirado/revocado ⇒ tratado como no servible (el 410 lo da 12-api). |
| `tests/scans/infrastructure/test_fixtures_load.py` | CLI/DB | `command.load` ingiere `Site/Scan/Finding` del fixture y deja el leaderboard poblado con grados pre-calculados. |

Los tests de endpoint (`POST /scans` idempotente → 200, AuthZ/IDOR, paginación)
viven en [12-api](../12-api/spec.md); aquí cubrimos esquema, índices y contratos.

## 6. Secuencia de build

1. **Enums + contratos** (`enums/scans.py`, `scans/domain/contracts/finding.py`,
   `events.py`). Tests puros del §5 (contract, dedupe). **Esto es lo que desbloquea
   P1–P4** — se hace primero y se congela.
2. **ORM + módulos** `src/sites/` y `src/scans/` (modelos, registro en
   `common/database/models/__init__.py`, `services/host.py`, `services/dedupe.py`).
3. **Migración Alembic** `…_scan_engine.py` con índices/constraints del §3 a mano.
   `just migrate-backend`.
4. **Repositorios** (ABC en `domain/`, `SQLXxxRepository` en `infrastructure/`):
   `enqueue` idempotente, UPSERT de findings, append de `scan_events`, query de
   leaderboard. Tests de repo del §5.
5. **Seed/fixtures** del leaderboard en `command.py` + `fixtures/`. Test de carga.
6. Carriles dependientes (04/05/07/08/10/12) construyen **sobre** este esquema.

La feature se considera `implemented`/coverage>0 cuando la migración aplica limpio,
los contratos están congelados y **toda** la suite del §5 pasa.

## 7. Decisiones y riesgos abiertos

1. **Dos módulos (`sites` + `scans`) vs uno** — resuelto: separados por dirección de
   dependencia y por tener lectores distintos (§1). `magic_tokens` se queda en `auth`.
2. **PK column name `uuid` vs `id`** — el DDL de la spec usa `id`; el repo real nombra
   la PK `uuid` (mixin `UUIDPrimaryKeyModelMixin`). **Se adopta `uuid`** por
   consistencia con todo el codebase. Ojo: los presenters **no** renombran a `id` —
   exponen el campo tal cual como `uuid` en las respuestas (passthrough camelCase; ver
   `common/presentation/presenters/tenant.py`, que emite `"uuid"`). Por tanto los
   contratos/consumidores aguas abajo deben referenciar `"uuid"`, **no** `"id"`.
   Las FKs apuntan a `…uuid` (`sites.uuid`, `scans.uuid`, `users.uuid`).
3. **Referencia circular `sites.latest_scan_id ↔ scans.site_id`** — se resuelve con
   `use_alter=True` en la FK (mismo patrón que `tenants.owner_id` en
   `models/tenants/tenant.py`); la migración crea las tablas y luego el constraint.
4. **`notification_prefs` y `magic_tokens` rompen el patrón UUID-PK** a propósito
   (PK natural: `user_id` y `token_hash`). Documentado para que un revisor no lo
   "corrija".
5. **Enum como `String` (no `sa.Enum` nativo de PG)** — se sigue la convención del
   repo (`TenantStatus` se persiste como `String` con `default=str(...)`), evitando
   migraciones de tipo enum de Postgres. Riesgo: la integridad del valor la
   garantizan el dominio + el `Literal` de Pydantic, no la DB; aceptable y consistente.
6. **DB de test se llama `doxiq_test`** en `tests/conftest.py` (herencia del base
   vnext). No se toca aquí; los tests nuevos cuelgan del mismo `conftest`/`Base.metadata`.
