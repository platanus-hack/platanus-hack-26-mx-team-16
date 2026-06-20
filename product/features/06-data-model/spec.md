---
feature: data-model
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §6, §7, §8, §9.1, §15; spec-gaps.md §6.2, §6.3, §6.4, §6.6, §6.7, §6.8, §6.11, §6.12, §6.13
---

# Owliver — Modelo de datos del motor de pentest (Postgres)

> Este subspec define el esquema Postgres del motor de pentest de Owliver (tablas `sites`, `scans`, `findings`, `agentic_surface`, `scan_events`, `watchlist`, `alerts`, `magic_tokens`, `public_reports`) junto con sus índices clave y los **contratos Pydantic congelados** (`Finding`, `AgenticResult` y sus enums) que viven en `finding.py` como artefacto de la hora 0. Es el modelo de datos del **SCAN** de Owliver, distinto del modelo del boilerplate SaaS (ver [../data-model](../data-model/spec.md)). El esquema persiste todo lo que el worker produce (ver [05-agent-team](../05-agent-team/spec.md)) y alimenta scoring, ranking, live-view, reporte y API. Cómo el scoring **consume** estas columnas se especifica en [07-scoring](../07-scoring/spec.md); el flujo de replay/SSE de `scan_events` en [10-realtime-live-view](../10-realtime-live-view/spec.md); las formas de endpoint en [12-api](../12-api/spec.md).

## 1. Alcance y principios

Este modelo de datos es la frontera persistente del motor de pentest. Tres principios lo gobiernan:

1. **El scoring y la deduplicación son Python determinista, no el LLM.** Todas las columnas de score (`web_score`, `agentic_score`, `agentic_status`, `overall_score`, `overall_grade`, `penalty_raw`) se calculan en Python antes de tocar la DB. El modelo solo las persiste.
2. **Identidad estable de findings entre escaneos.** La columna `dedupe_key` (un `sha256` determinista) habilita el monitoreo temporal: UPSERT por `(site_id, dedupe_key)`, y un finding que deja de reaparecer pasa a `status='fixed'`.
3. **Observabilidad del worker desde la propia DB.** `tools_status`, `coverage`, `progress`, `current_phase` y `error` permiten depurar un scan colgado vía `GET /scans/{id}` sin montar tooling extra.

El esquema se congela en la hora 0–2 junto con `finding.py` (contratos Pydantic) para desbloquear los carriles P1–P4 en paralelo (ver §6 de este doc y [05-agent-team](../05-agent-team/spec.md)).

## 2. Esquema Postgres

El DDL de referencia (formas y comentarios preservados verbatim de la spec):

```sql
users(id, email, name, created_at)

sites(id, url, hostname, is_gov bool, country, owner_user_id NULL,
      latest_scan_id NULL, created_at)

scans(id UUID PK, site_id, level ENUM(basico,intermedio,avanzado),
      status ENUM(queued,running,partial,done,failed,cancelled),
      visibility ENUM(public,private),
      requested_by, authorized bool, authorized_at,
      -- progreso / observabilidad del live-view al recargar (§12.1)
      progress int DEFAULT 0,            -- 0..100
      current_phase text,                -- fase humana legible
      tools_status jsonb,                -- {nuclei:'done', zap:'running', testssl:'queued'}
      coverage jsonb,                    -- [{tool, status: ok|failed|timeout}] (§9.2)
      -- scoring (ver §9)
      web_score int, agentic_score int NULL, overall_score int,
      overall_grade char(1),             -- A..F, incluye E
      agentic_status ENUM(no_surface,detected_not_tested,tested),  -- (§9.1)
      penalty_raw int,                   -- penalty SIN cap, para orden/desempate (§9.4)
      started_at, finished_at, error)

findings(id, scan_id, site_id, source, tool, category, title,
         severity, cvss, confidence, description, evidence jsonb,
         affected_url, endpoint, param, impact, remediation,
         references jsonb, status ENUM(open,fixed,accepted),
         -- identidad estable para monitoreo temporal (§8)
         dedupe_key char(64),               -- sha256(site_id|source|category|normalize(affected_url)|param|tool)
         first_seen, last_seen)             -- a nivel SITE, no scan

agentic_surface(id, scan_id, site_id, type, vendor, location_url,
                inferred_model NULL, detected_at)   -- inferred_model solo con señal dura

watchlist(id, user_id, site_id, monitor bool, created_at)   -- watchlist privada
                                                            -- global = sites.is_gov

alerts(id, user_id, site_id, scan_id, type, message, channel, sent_at)

notification_prefs(user_id PK, email_enabled bool DEFAULT true,   -- prefs de canal por usuario
                   slack_webhook_url NULL, updated_at)            -- (§3.6; canales en 08 §5.1)

-- canje del magic-link (§14.1): se guarda el hash, nunca el token plano
magic_tokens(token_hash char(64) PK, email, expires_at,
             consumed_at NULL, created_at)

-- live-view: persistencia OBLIGATORIA, ya NO opcional (§12.1)
-- seq monótono por scan = única fuente de orden; habilita replay
scan_events(id, scan_id, seq int, ts, type, agent, tool NULL,
            severity NULL, message, payload jsonb)
-- type ∈ agent_status|tool_start|tool_end|finding|phase|score|done|error

public_reports(token, scan_id, created_at, expires_at, revoked_at NULL)  -- links compartibles
```

## 3. Tablas en detalle

### 3.1 `sites`

Catálogo de dominios escaneados. Una fila por `hostname`.

- `is_gov bool` — **se calcula al insertar el site**, no se acepta del cliente: `is_gov = hostname.endswith('.gob.mx')` (artefacto congelado de la hora 0, ver [05-agent-team](../05-agent-team/spec.md)). Es la fuente del **leaderboard global**: el ranking público de `.gob.mx` es `WHERE is_gov` (ver [08-ranking-watchlists](../08-ranking-watchlists/spec.md)).
- `owner_user_id NULL` — dueño del site cuando lo registró un usuario (URL propia). Un site con `owner_user_id` no nulo nunca es público por defecto (ver `scans.visibility` y AuthZ, §3.2).
- `latest_scan_id NULL` — puntero al último scan para resolver el grado actual sin subconsulta.
- `country` — país inferido; informativo.

### 3.2 `scans`

Una fila por ejecución del motor. Es el núcleo observable del worker y la fila del leaderboard.

- `id UUID PK` — **UUIDv4, no serial.** Decisión de seguridad: evita la enumeración de scans y el IDOR sobre findings reales (vulnerabilidades explotables de dominios privados). Owliver almacena vulnerabilidades explotables; un id secuencial convertiría al producto en un índice público de cómo hackear los sitios de sus usuarios — el peor titular posible.
- `level ENUM(basico, intermedio, avanzado)` — nivel de ataque solicitado (ver [02-attack-levels](../02-attack-levels/spec.md)).
- `status ENUM(queued, running, partial, done, failed, cancelled)` — máquina de estados del scan:
  - `queued` — encolado en SAQ, aún sin worker.
  - `running` — worker activo; sirve también como **lock** para la idempotencia (§4).
  - `partial` — terminó pero **faltó ≥1 scanner base** (cobertura incompleta). Estado de primera clase: un scan donde ZAP/Nuclei/testssl crashearon, expiraron o fueron bloqueados por un WAF no debe salir con grado A por tener 0 findings. La regla de cap a grado C la aplica el scoring (ver [07-scoring](../07-scoring/spec.md)); aquí el modelo solo distingue `partial` de `done`.
  - `done` — terminó con todos los scanners base cubiertos.
  - `failed` — error irrecuperable; ver `error`.
  - `cancelled` — cancelado por el usuario; el worker chequea una flag Redis entre tools y aborta (ver [12-api](../12-api/spec.md) para `POST /scans/{id}/cancel`).
- `visibility ENUM(public, private)` — control de acceso del scan. **Gov básico/pasivo = `public`**; intermedio/avanzado o cualquier site con `owner_user_id` = `private` (requiere ser el owner o tener el site en la watchlist). El reporte público se expone **solo vía token** (`public_reports`), nunca vía `GET /scans/{id}`. Junto con el `id` UUIDv4 y el check de owner, cierra el IDOR sobre vulnerabilidades reales.
- `requested_by` — usuario que disparó el scan (puede ser NULL para scans gov anónimos del seed).
- `authorized bool` / `authorized_at` — registro del consentimiento explícito para el ataque (gate legal/ético, ver [01-legal-ethics](../01-legal-ethics/spec.md)). Un re-scan ciego de un nivel activo sería un segundo ataque no consentido, de ahí la idempotencia (§4).
- **Observabilidad / live-view al recargar:**
  - `progress int DEFAULT 0` — 0..100.
  - `current_phase text` — fase humana legible (p. ej. "escaneando TLS").
  - `tools_status jsonb` — estado por herramienta, p. ej. `{nuclei:'done', zap:'running', testssl:'queued'}`.
  - `coverage jsonb` — lista `[{tool, status: ok|failed|timeout}]`. Es la fuente de verdad de la cobertura: si faltó ≥1 scanner base, el scoring capa el grado en C y etiqueta "cobertura parcial". Un scan que tira el scanner no debe premiarse con un buen score.
  - `error` — mensaje del fallo irrecuperable. `tools_status` + `coverage` + `error` se devuelven en `GET /scans/{id}` para depurar un scan colgado sin tooling extra.
- **Scoring (calculado en Python, ver [07-scoring](../07-scoring/spec.md)):**
  - `web_score int`, `agentic_score int NULL`, `overall_score int`.
  - `overall_grade char(1)` — A..F, **incluye E** (escala `A≥90 B≥80 C≥70 D≥60 E≥40 F<40`, con más escalones en la zona poblada).
  - `agentic_status ENUM(no_surface, detected_not_tested, tested)` — tres estados, no un N/A binario (contrato congelado, ver §5.2 y [07-scoring](../07-scoring/spec.md) §9.1).
  - `penalty_raw int` — penalty **SIN** el cap `min(100, penalty)`. Se persiste para desempatar el leaderboard: cuando muchos `.gob.mx` reales colapsan al mismo grado/sub-score (la mayoría empata en 0/F), el orden "peores primero" se vuelve indefinido. El leaderboard ordena por `(overall_grade ASC, penalty_raw DESC)` (ver [08-ranking-watchlists](../08-ranking-watchlists/spec.md)).
- `started_at`, `finished_at` — marcas temporales del worker.

### 3.3 `findings`

Una fila por hallazgo deduplicado. Las tool-functions parsean su salida cruda a `Finding[]` en Python; el `dedupe_key` se calcula en Python en el momento del parseo, antes de tocar la DB.

- `source` — `owasp` | `agentic`. Separa Web vs Agéntico; alimenta los dos sub-scores.
- `tool` — herramienta que originó el hallazgo.
- `category` — código OWASP `A01–A10` **o** OWASP-LLM `LLM01–LLM10`. El mapeo a categoría sale de un **dict/YAML estático curado** (template-id/probe → categoría), **nunca** del LLM.
- `title`, `description`.
- `severity` — `critical|high|medium|low|info`; junto con `cvss` alimenta el score.
- `cvss` — score CVSS cuando la tool lo provee.
- `confidence` — `alta|media|baja`. **Crítico para falsos positivos**: el orquestador (Opus) puede hacer triage y bajar la confianza de hallazgos dudosos. El factor de confianza pondera el penalty (ver [07-scoring](../07-scoring/spec.md)).
- `evidence jsonb` — payload enviado, snippet request/response, ref a screenshot. Es lo que da **valor técnico**. Para hallazgos agénticos incluye `{payload, respuesta_cruda, veredicto, reason}`; el caso canary guarda el token secreto como evidencia incontestable. La `evidence.screenshot` guarda una **URL relativa** a `/data/scans/{scan_id}/{n}.png` (volumen compartido servido por ruta estática FastAPI): **no** base64 en jsonb (infla la DB), **no** MinIO (servicio extra inútil al demo). El PDF embebe desde la misma ruta (ver [09-reporting](../09-reporting/spec.md)).
- `affected_url`, `endpoint`, `param` — localización del hallazgo; entran al `dedupe_key`.
- `impact` — lenguaje de negocio.
- `remediation` — pasos accionables. `impact` + `remediation` dan el valor "fácil de entender".
- `references jsonb` — enlaces de referencia.
- `status ENUM(open, fixed, accepted)` — estado a **nivel site**. El re-scan hace UPSERT por `(site_id, dedupe_key)`; un finding que no reaparece pasa a `fixed`; `accepted` es un riesgo aceptado por el usuario.
- `dedupe_key char(64)` — `sha256(site_id | source | category | normalize(affected_url) | param | tool)`. Identidad **estable** del finding entre escaneos: es lo que hace computable el monitoreo. Se calcula en Python en el momento del parseo, antes de tocar la DB. La deduplicación por `dedupe_key` ocurre **antes** de calcular cualquier penalty.
- `first_seen` / `last_seen` — a **nivel site** (vía `dedupe_key`), **no** a nivel scan, para que el monitoreo temporal sobreviva entre escaneos. Habilitan detectar findings nuevos (`first_seen` del último scan) y resueltos (no reaparecen) entre escaneos sucesivos.

> Los findings de severidad `info` (peso 0) se persisten y se muestran en la capa técnica del reporte con su **conteo aparte**, pero **no afectan el score**. Se usan también como findings-meta del propio escaneo: "tool X no completó" (`confidence=baja`) o "cobertura incompleta".

### 3.4 `agentic_surface`

Inventario de la superficie agéntica detectada (chatbots / inputs de prompt / search-ai), independiente de si se llegó a probar.

- `type` — `chatbot | prompt-input | search-ai`.
- `vendor` — Intercom, Drift… o NULL (superficie genérica).
- `location_url` — dónde vive la superficie.
- `inferred_model NULL` — modelo inferido **solo con señal dura** (best-effort; NULL si "modelo no expuesto").
- `detected_at`.

Su relación con `agentic_status` y el contrato `AgenticResult` se detalla en §5.2 y en [03-agentic-surface](../03-agentic-surface/spec.md).

### 3.5 `scan_events`

Persistencia **OBLIGATORIA** (ya no opcional) del live-view. El `seq` monótono por scan es la **única fuente de orden** y habilita el replay determinista al recargar.

- `seq int` — secuencia monótona **por scan**; única fuente de orden.
- `ts` — timestamp del evento.
- `type` — discriminante: `agent_status | tool_start | tool_end | finding | phase | score | done | error`.
- `agent`, `tool NULL`, `severity NULL`, `message`, `payload jsonb`.

El flujo de emisión (Redis pub/sub), el replay y el SSE se especifican en [10-realtime-live-view](../10-realtime-live-view/spec.md); aquí solo se fija la forma de la tabla y la garantía de orden.

### 3.6 `watchlist`, `alerts` y `notification_prefs`

- `watchlist(id, user_id, site_id, monitor bool, created_at)` — watchlist **privada** por usuario. La watchlist **global** no se materializa: es `sites.is_gov`.
- `alerts(id, user_id, site_id, scan_id, type, message, channel, sent_at)` — **log** de notificaciones de monitoreo enviadas (ver [08-ranking-watchlists](../08-ranking-watchlists/spec.md)). `channel ∈ {email, slack}`.
- `notification_prefs(user_id PK → users, email_enabled bool DEFAULT true, slack_webhook_url NULL, updated_at)` — **preferencias de canal por usuario** (a nivel cuenta, no por dominio): el email al owner está activo por defecto y el `slack_webhook_url` es opcional. Es lo que el monitoreo lee para decidir a qué canales emitir (los canales como tales los define [08-ranking-watchlists](../08-ranking-watchlists/spec.md) §5.1; se configura vía `PUT /me/alerts`, ver [12-api](../12-api/spec.md)).

### 3.7 `magic_tokens`

Canje del magic-link. Se guarda el **hash**, nunca el token plano.

- `token_hash char(64) PK` — `sha256` del token opaco; el token plano nunca se persiste.
- `email`, `expires_at`, `consumed_at NULL`, `created_at`.

Token opaco de 1 uso, TTL 10 min. El callback `GET /auth/callback?token=` verifica no-consumido/no-expirado, marca `consumed_at`, hace upsert de `users` y emite sesión. El flujo completo (login, logout, me) está en [11-auth-magic-link](../11-auth-magic-link/spec.md).

### 3.8 `public_reports`

Links compartibles del reporte ejecutivo (sin payloads de explotación).

- `token` — `secrets.token_urlsafe(32)`, opaco. Index `UNIQUE`.
- `scan_id`, `created_at`, `expires_at`, `revoked_at NULL`.

TTL default 7 días, settable en `POST /scans/{id}/share`. `GET /r/{token}`: 404 si no existe, **410 Gone** si `expires_at < now` o `revoked_at` no nulo. El público expone la capa ejecutiva + findings **sin payloads de explotación** (ver [09-reporting](../09-reporting/spec.md) y [12-api](../12-api/spec.md)).

## 4. Índices clave e idempotencia

- `UNIQUE (scan_id, seq)` en `scan_events` — orden y replay determinista por scan.
- `(site_id, dedupe_key)` en `findings` — el re-scan hace UPSERT por esta clave; un finding que no reaparece pasa a `status='fixed'`.
- **Partial unique index** `scans(site_id, level) WHERE status IN ('queued','running')` — **idempotencia de `POST /scans`.** Impide que un doble-click, un retry de red o el seed re-ejecutado lancen escaneos duplicados (cada uno corre Opus+Sonnet+garak+ZAP: duplicar es caro, ensucia el ranking, y un retry ciego de un nivel activo es un segundo ataque no consentido). El 2º POST devuelve 200 con el `scan_id` existente. Segunda capa: la **job key de SAQ** derivada de `site_id+level` colapsa el doble-submit inmediato que el partial index no alcanza a cubrir; `scans.status='running'` actúa como lock. La política de reintentos (`max_tries=1` para niveles activos, `max_tries=2` para básico/gov) vive en el worker (ver [05-agent-team](../05-agent-team/spec.md)).
- `UNIQUE (token)` en `public_reports`.

## 5. Contratos Pydantic congelados (`finding.py`)

`finding.py` es uno de los **5 artefactos innegociables de la hora 0–2**: contiene `Finding` + `AgenticResult` + los enums (`severity`, `confidence`, `source`, `category`). Es el contrato entre P2 (parsers), P3 (agéntico) y P4 (reporte); nadie lo toca después de la hora 2 (cambiarlo rompe a tres personas a la vez). Estos shapes son normativos y se preservan verbatim.

### 5.1 `Finding`

```python
class Finding(BaseModel):           # salida estructurada estándar (sección 8)
    source: Literal["owasp", "agentic"]
    tool: str
    category: str                   # A01..A10 o LLM01..LLM10
    title: str
    severity: Literal["critical","high","medium","low","info"]
    cvss: float | None
    confidence: Literal["alta","media","baja"]
    description: str
    evidence: dict                  # payload, req/resp snippet, screenshot ref (URL relativa)
    affected_url: str | None
    endpoint: str | None
    param: str | None
    impact: str                     # lenguaje de negocio
    remediation: str
    references: list[str]
```

Enums normativos derivados de `Finding`:

- `severity`: `critical | high | medium | low | info`.
- `confidence`: `alta | media | baja`.
- `source`: `owasp | agentic`.
- `category`: cadena con dominio `A01..A10` (OWASP) **o** `LLM01..LLM10` (OWASP-LLM). El valor concreto se asigna por dict/YAML estático curado, **nunca** por el LLM.

Las tool-functions **PARSEAN en Python** y devuelven `list[Finding]` ya construido; los agentes Sonnet **no** usan `response_model=list[Finding]` (ver [04-scanning-engine](../04-scanning-engine/spec.md) y [05-agent-team](../05-agent-team/spec.md)).

### 5.2 `AgenticResult` (contrato de la hora 0)

**`AgenticResult` DEBE definirse aquí** y congelarse en `finding.py` desde la hora 0 (decisión de consistencia): es la salida del subagente agéntico y la fuente de `agentic_status`. Shape verbatim:

```python
class AgenticResult(BaseModel):     # salida del subagente agéntico (§4) — congelado en finding.py (§15)
    type: str                       # chatbot | prompt-input | search-ai
    vendor: str | None              # Intercom, Drift… o None (superficie genérica)
    location_url: str
    inferred_model: str | None      # best-effort; NULL si "modelo no expuesto" (§4)
    agentic_status: Literal["no_surface","detected_not_tested","tested"]  # §9.1
    findings: list[Finding]         # hallazgos de los probes (source="agentic", canary/leak/jailbreak)
```

Notas del contrato agéntico:

- `type` / `vendor` / `location_url` espejan las columnas de `agentic_surface`; `inferred_model` es best-effort (NULL si el modelo no se expone).
- Cada veredicto de un probe se materializa como un `Finding` con `source="agentic"`, su `confidence` (**alta** si hubo canary/regex, **media** si fue juicio del LLM) y `evidence = {payload, respuesta_cruda, veredicto, reason}`.
- `agentic_status` es un `Literal` de **tres** estados (no un N/A binario):

| `agentic_status` | Significado | Efecto en `overall` |
|---|---|---|
| `no_surface` | No se detectó chatbot/superficie agéntica | `overall = web_score` (no penaliza) |
| `detected_not_tested` | Hay superficie pero no se pudo probar (testing falló/se recortó) | **No** se promedia y **no** se premia con 100: badge "IA detectada, sin auditar" en reporte + leaderboard |
| `tested` | Superficie detectada y sondeada → `agentic_score` válido | entra al promedio ponderado |

Cómo `agentic_status` pondera `overall_score` (la fórmula `0.6 × web + 0.4 × agentic`) se detalla en [07-scoring](../07-scoring/spec.md); aquí solo se fija el enum y su persistencia en `scans.agentic_status` y en el contrato Pydantic.

## 6. Relación con la hora 0 y los demás subspecs

El esquema de §2–§4 y los contratos de §5 se congelan en el bloque 0–2 para abrir los carriles P1–P4 en paralelo. Junto a `finding.py` se congela `events.py` (la forma de `scan_event` con `seq` + `type` discriminante), que aquí corresponde a la tabla `scan_events` (§3.5) y se desarrolla en [10-realtime-live-view](../10-realtime-live-view/spec.md). El seeding/pre-horneado del leaderboard (30–50 filas `sites`+`scans`+`findings` con grados pre-calculados y findings agénticos plantados, cargadas vía CLI de fixtures y sobrescritas por scans reales si terminan a tiempo) se detalla en [08-ranking-watchlists](../08-ranking-watchlists/spec.md). La paginación por cursor (`?limit=&cursor=` → `{items, next_cursor}`) y el formato de error estándar (`{error:{code, message, details?}}`) que operan sobre estas tablas se especifican en [12-api](../12-api/spec.md).
