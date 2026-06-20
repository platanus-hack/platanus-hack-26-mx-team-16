---
feature: scanning-engine
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §1–§11; 02-attack-levels §3–§5; 01-legal-ethics §2.5/§3/§4; 05-agent-team §4–§5; 06-data-model (Finding/coverage)
---

# Owliver — Motor de escaneo — plan de implementación (CÓMO)

> La [spec](./spec.md) fija el **QUÉ** del motor: patrón híbrido de ejecución
> (subprocess vs DooD), timeouts/budget/watchdog, redes de egress, cold-start de
> imágenes y persistencia de evidencia. Este plan aterriza el **CÓMO** contra el
> codebase real: una **imagen fat `scanners`** que es la base del servicio
> `worker` (SAQ), un paquete net-new `backend/src/scanning/` con `run_tool()`,
> `resolve_tools()` y `RobotsPolicy`, los servicios docker-compose nuevos, y la
> suite de tests que prueba el aislamiento de fallos y el invariante pasivo.
>
> **Límites de propiedad (no re-litigar):**
> - El **contrato legal del perfil pasivo gov** lo posee
>   [01-legal-ethics](../01-legal-ethics/spec.md) (paquete `common/legal`,
>   `passive_profile.py`, `SCANNER_USER_AGENT`). El motor lo **importa**, nunca lo
>   redefine.
> - La **whitelist `(is_gov, level)`** (qué tools por nivel) la define
>   [02-attack-levels](../02-attack-levels/spec.md); `resolve_tools()` la
>   **materializa** y la valida contra el contrato legal.
> - La **forma de `Finding` / `coverage`** la posee
>   [06-data-model](../06-data-model/spec.md); el **parseo** y la orquestación del
>   Team Agno los posee [05-agent-team](../05-agent-team/spec.md). El motor solo
>   provee el **mecanismo de ejecución** que entrega salida cruda a esos parsers.

## 0. Estado de las dependencias

El codebase hoy es solo el **fundamento SaaS**: no existe ni un scanner, ni el
servicio `worker`, ni el paquete `scanning`. El motor es **infra + worker
net-new**. Lo que **sí** existe y se reutiliza tal cual:

- **Cola SAQ**: `backend/config/tasks.py` define `worker_settings`
  (`queue`, `functions=[handle_command]`, `cron_jobs=[]`, `startup`, `shutdown`),
  lanzado por `saq config.tasks.worker_settings`. `startup(ctx)` ya inyecta
  `ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=True)`
  — **el flag de cancelación del watchdog (§4.3) usa ese mismo cliente**.
- **Registro de comandos**:
  `backend/src/common/application/data/tasks_mapping.py` (`async_tasks_mapping`)
  + `AsyncTaskResolver`; el job de pentest se registra ahí (`RunScanCommand`,
  lo posee 05/06 — aquí solo se documenta el punto de enganche).
- **Settings**: `backend/src/common/settings.py` (`Settings(BaseSettings)`,
  `REDIS_HOST/PORT/...`, propiedades `redis_url` / `async_database_url`). Los
  toggles del motor (`ENABLE_HEXSTRIKE`, paths de scans, límites) se añaden aquí.
- **Compose real**: `backend/docker-compose.yml` (dev: `api`, `postgres:17`,
  `redis:7`, `mailpit`; volumen `postgres_data`; red por defecto), más
  `docker-compose.dev.yml` / `.prod.yml` / `.debug.yml`. **No** existen servicios
  `worker`, `scanners`, `hexstrike` ni `scheduler` — los crea este plan.
- **Dockerfile**: multi-stage con `uv` (`ghcr.io/astral-sh/uv:python3.13-bookworm-slim`,
  targets `production_builder` / `development` / `production`). La imagen
  `scanners` se construye **encima** de esta base (§2.2).
- **Rate-limiter Redis**:
  `backend/src/common/infrastructure/services/rate_limiter.py` — es el límite de
  **API por usuario** (lo cablea 12); aquí solo se aplica el límite **por target**
  (flags `-rl`/delay, §3.4).
- **Tests**: `backend/tests/<área>/...` con `conftest.py`, `fixtures/`,
  `helpers/`; pytest async; corren con `just test-backend tests/scanning`.

## 1. Mapa de implementación (qué pieza vive dónde)

| # spec | Pieza | Código net-new | Dueño |
|---|---|---|---|
| §1–§3 | Helper `run_tool()` (subprocess + DooD unificado) | `src/scanning/runner.py` | 04 |
| §4.1 | Servicio `worker` sobre imagen `scanners`, `max_jobs` | `docker-compose.scanners.yml` + Dockerfile.scanners | 04 |
| §4.2 | Tabla canónica timeout por tool | `src/scanning/registry.py` (`TOOL_SPECS`) | 04 |
| §4.3 | Watchdog (budget global) + cancel Redis + fallo parcial | `src/scanning/watchdog.py` + `run_tool()` | 04 |
| §4 (whitelist) | `resolve_tools(is_gov, level)` validado contra `passive_profile` | `src/scanning/resolver.py` | 04 (whitelist 02, contrato 01) |
| §5 (02) | `RobotsPolicy` (impl del `Protocol` de `legal/robots.py`) | `src/scanning/robots.py` | 04 (contrato 01) |
| §5 | Aislamiento de egress (redes + bloqueo IP privada/metadata) | compose networks + `src/scanning/egress.py` | 04 |
| §7 | Cold-start: pre-pull imágenes pineadas + templates nuclei | `scripts/warm_scanners.sh` + volumen | 04 |
| §8 | Evidencia: archivos en `/data/scans/{id}/` + ruta estática | `src/scanning/evidence.py` + static mount en API | 04 (forma `evidence` = 06) |
| §10 | `ENABLE_HEXSTRIKE` + healthcheck al arrancar worker | `settings.py` + `src/scanning/health.py` | 04 |

## 2. Servicios docker-compose

### 2.1 Topología de servicios

> **Realidad de la topología actual (a autorar aquí):** hoy **no** existe un
> servicio `worker` dedicado — el worker SAQ está **co-ubicado** dentro del
> contenedor `api` (`docker/start-dev` lanza `saq config.tasks.worker_settings &`
> junto a `uvicorn` en el mismo proceso de arranque). Ese setup de dev **no es** el
> target para correr scanners. La feature 04 **debe autorar** la topología Docker
> dedicada de worker/scanners: un servicio `worker` separado + las imágenes de las
> herramientas scanner (DooD), que no existen aún.

Se añade un override **`backend/docker-compose.scanners.yml`** (sigue el patrón de
los overrides existentes `.dev/.prod/.debug.yml`) que agrega los servicios del
motor sin tocar `api`/`postgres`/`redis`/`mailpit` del compose base:

- `worker` — proceso SAQ, **corre dentro de la imagen `scanners`** (no es imagen
  aparte). `command: saq config.tasks.worker_settings`. Monta el socket Docker
  del host (DooD) y el directorio compartido de scans.
- `scanners` — sólo **build target**: la imagen fat con las CLIs preinstaladas
  (base de `worker`). No se levanta como servicio propio salvo para `docker build`.
- `hexstrike` — contenedor pesado opt-in (imagen Kali). `profiles: ["hexstrike"]`
  para que **no arranque** salvo `--profile hexstrike` (§10).
- `scheduler` — cron SAQ de re-escaneos gov. Reusa la misma imagen `scanners`
  con otro `command`; el guard `AUTOMATIC_ALLOWED_LEVELS` lo posee 08.

```yaml
# backend/docker-compose.scanners.yml  (override; se aplica con -f base -f scanners)
services:
  worker:
    build: { context: ., dockerfile: Dockerfile.scanners, target: worker }
    command: saq config.tasks.worker_settings
    env_file: [.env]
    environment: [PYTHONPATH=/app, PROCESS_LABEL=worker]
    depends_on: { postgres: { condition: service_started }, redis: { condition: service_started } }
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock      # DooD/sibling — NO DinD
      - /data/scans:/data/scans                         # path del HOST (ver §3.1)
      - nuclei_templates:/root/nuclei-templates         # warm (§7)
    networks: [owliver_internal, owliver_egress]        # habla con redis/pg y lanza siblings
    deploy: { resources: { limits: { memory: 2g } } }

  hexstrike:
    image: hexstrike/hexstrike-ai:stable
    profiles: ["hexstrike"]                              # off por defecto (§10)
    networks: [owliver_egress]

networks:
  owliver_internal: { internal: true }                  # sin egress: postgres/redis
  owliver_egress:   { driver: bridge }                  # salida a internet: scanners

volumes:
  nuclei_templates:
```

> **postgres/redis se mueven a `owliver_internal`** en el compose base (red
> `internal: true`, sin egress) y el `api`/`worker` los alcanzan ahí; sólo el
> `worker` toca además `owliver_egress` para lanzar los siblings. Ningún scanner
> sibling se une jamás a `owliver_internal` (§5).

### 2.2 `Dockerfile.scanners`

Imagen fat construida **sobre** la base `uv` existente. Trae preinstaladas las
**CLIs ligeras** (nuclei, testssl.sh, whatweb, nikto, katana, ffuf/gobuster,
sqlmap, subfinder, dnsx) + el cliente `docker` (sólo el CLI, para hablar con el
socket montado) + Playwright (para 03/05). ZAP y hexstrike **no** se incluyen
aquí: son siblings que se lanzan por imagen propia vía DooD.

```dockerfile
# Dockerfile.scanners
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS scanners-base
RUN apt-get update && apt-get install -y --no-install-recommends \
      docker.io ca-certificates dnsutils nmap nikto whatweb \
    && rm -rf /var/lib/apt/lists/*
# nuclei, testssl, katana, ffuf, subfinder, dnsx, sqlmap → binarios pineados
COPY scripts/install_scanners.sh /tmp/
RUN /tmp/install_scanners.sh                  # versiones pineadas, NO :latest (§7)

FROM scanners-base AS worker                  # = base del proceso SAQ
WORKDIR /app
# ... uv sync idéntico al Dockerfile principal (deps Python + Agno) ...
COPY . /app
```

`just`-targets nuevos: `build-scanners` (`docker compose -f docker-compose.yml -f
docker-compose.scanners.yml build scanners worker`), `dev-worker` (levanta el
override), `warm-scanners` (§7).

## 3. El helper `run_tool()` y el resolutor de whitelist

### 3.1 Directorio compartido de scan

Cada scan tiene `/data/scans/{scan_id}/` en el **host**, bind-mounted en el
`worker` y en cada sibling pesado. **Regla DooD crítica**: el `-v` del `docker
run` sibling apunta al **path del HOST** (`/data/scans/{id}`), no al path interno
del worker, porque el daemon que recibe la orden por el socket sólo conoce paths
del host. `run_tool()` recibe `host_shared_dir` explícito para no equivocarse.

### 3.2 Firma de `run_tool()` — `src/scanning/runner.py`

Punto **único** de invocación. Las ligeras van por `subprocess`; las pesadas por
`docker run` sibling. Ambas pasan por el mismo guard de cancelación, timeout y
captura.

```python
@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool                     # False si expiró / no-zero / excepción
    stdout: str                  # crudo (JSON/JSONL) → lo parsea 05, no este módulo
    stderr: str
    duration_s: float
    timed_out: bool
    coverage_note: str | None    # "tool X no completó" → Finding-meta (§4.3)

async def run_tool(
    spec: ToolSpec,              # de TOOL_SPECS (§3.3): cmd, timeout, mechanism, image
    *, target: str,
    host_shared_dir: str,        # path del HOST para -v (§3.1)
    cancel: CancelToken,         # chequeado ANTES de arrancar la tool (§4.3)
) -> ToolResult: ...
```

Reglas internas:
- **Antes** de lanzar: `if cancel.is_set(): return ToolResult(ok=False, coverage_note="cancelado")`.
- **`subprocess`**: `await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=spec.timeout, text=True)`.
- **DooD**: construye `["docker","run","--rm","--network","owliver_egress",
  "--memory",spec.memory, "-v", f"{host_shared_dir}:/zap/wrk", spec.image, *spec.cmd]`
  con `timeout=spec.timeout + DOCKER_OVERHEAD`. Centraliza aquí `--network`,
  `--memory`/`--cpus`, tag pineado, `-v` host, y el bloqueo de egress lateral
  (§5) — uniforme para **toda** invocación pesada.
- **`try/except` total**: `TimeoutExpired` → `timed_out=True`; cualquier otra
  excepción → `ok=False, coverage_note`. **Nunca** propaga (§4.3).
- Inyecta `SCANNER_USER_AGENT` (de `common.legal.constants`), `-rl
  WORKER_NUCLEI_RATE` y delay `WORKER_REQUEST_DELAY_MS` según `spec` (§3.4).

### 3.3 `TOOL_SPECS` — `src/scanning/registry.py`

Tabla canónica spec→mecanismo→timeout (de [spec §4.2]); cada entrada lleva
`cmd_template`, `mechanism`, `image` (si DooD), `memory`, `timeout`, y el inyector
de rate-limit. **Fuente única**: ningún timeout suelto en el resto del código.

| Tool | Mecanismo | Timeout | Memoria |
|---|---|---|---|
| nuclei | subprocess | 90s | — |
| testssl | subprocess | 60s | — |
| security-headers / Observatory | subprocess (1 req raíz) | 30s | — |
| whatweb | subprocess | 30s | — |
| nikto | subprocess | 90s | — |
| katana | subprocess | 60s | — |
| ffuf / gobuster | subprocess | 90s | — |
| sqlmap | subprocess | 120s | — |
| subfinder / dnsx | subprocess | 60s | — |
| ZAP baseline | DooD (`run_tool`) | 120s | 2g |
| ZAP full active | DooD (`run_tool`) | 240s | 2g |
| garak | subprocess | 180s | — |
| promptfoo | subprocess | 120s | — |
| hexstrike-ai | DooD (MCP) | feature-flag / time-boxed | — |

### 3.4 Inyección de rate-limit / robots / UA

Importados de `common.legal.constants` (los posee 01): `SCANNER_USER_AGENT =
"Owliver-Scanner/1.0 (+contacto)"`, `WORKER_NUCLEI_RATE` (`nuclei -rl`),
`WORKER_REQUEST_DELAY_MS` (delay ffuf/katana). `run_tool()` los aplica de forma
uniforme; el motor **no** los redefine.

### 3.5 `resolve_tools(is_gov, level)` — `src/scanning/resolver.py`

Materializa la whitelist `(is_gov, level)` de [02-attack-levels §4] como una
lista concreta de `ToolInvocation` (tool + flags resueltos). Es **allow-list**:
lo que no está, no corre.

```python
def resolve_tools(*, is_gov: bool, level: ScanLevel) -> list[ToolInvocation]:
    tools = _WHITELIST[(is_gov, level)]              # tabla 02, acumulativa por nivel
    if is_gov and level is ScanLevel.basico:
        assert_within_passive_profile(tools)         # contrato de 01 (lanza si se sale)
    return tools
```

- Para `(gov, básico)` el resultado **debe** validar
  `assert_within_passive_profile()` del paquete legal (testssl /
  security-headers / whatweb / nuclei `-tags ssl,tech,http-misconfig` excluyendo
  `intrusive,dos,fuzzing,network`, sin spider; ZAP-spider y katana **ausentes**).
- 04 **posee** los perfiles intermedio/avanzado; 01 sólo aporta el predicado del
  pasivo gov.
- Defensa en profundidad (02 §4): al `owasp_agent` (05) sólo se le entregan las
  tools que devuelve `resolve_tools`, así ni siquiera puede elegir un activo
  contra gov en el camino automático.

### 3.6 `RobotsPolicy` — `src/scanning/robots.py`

Implementación del `Protocol RobotsPolicy` definido en `common/legal/robots.py`
(contrato de 01). Antes de **cualquier** request: descarga `robots.txt` con
`SCANNER_USER_AGENT`, lo parsea (`urllib.robotparser`), y expone
`is_allowed(path)`. Los paths `Disallow` quedan excluidos del set de targets que
recibe cada tool. Si `robots.txt` no existe → todo permitido; si es inaccesible →
fail-safe a "sólo raíz" para el perfil pasivo.

## 4. Concurrencia, watchdog, budget global

### 4.1 Concurrencia del worker

`worker` con `max_jobs=1` (subir a `2` sólo si el host aguanta) vía
`worker_settings["concurrency"]` en `config/tasks.py`. Dentro de un scan, las
tools del nivel corren **concurrentes** (`asyncio.gather` de `run_tool()`), de
modo que el wall-clock del básico ≈ timeout máximo, no la suma serial (objetivo
spec: básico <90s). El seed gob.mx **no** se encola de golpe: 5–8 sitios se
pre-escanean como fixtures antes del demo (lo posee 08); el resto va en
background.

### 4.2 Budget global + timeouts por tool

Dos capas de tiempo: el **timeout duro por tool** (de `TOOL_SPECS`, aplicado en
`subprocess.run(timeout=)` / `docker run` con timeout) y el **budget global ~8
min** por scan, vigilado por el watchdog (§4.3). El perfil demo `<90s` es **otro**
presupuesto (lo posee 02 §7); el motor sólo expone el config del budget global.

### 4.3 Watchdog + cancelación Redis + fallo parcial — `src/scanning/watchdog.py`

```python
SCAN_BUDGET_S = 8 * 60

class CancelToken:
    """Lee la flag de cancelación de Redis (ctx['redis'], ver §0)."""
    def __init__(self, redis, scan_id): ...
    async def is_set(self) -> bool:      # GET scan:{id}:cancel  (chequeado ENTRE tools)
```

- **Watchdog**: un `asyncio.create_task` con `asyncio.wait_for(scan_coro,
  timeout=SCAN_BUDGET_S)`; al agotarse el budget **cancela la corrutina del scan**
  → aborta las tools restantes en vuelo en lugar de dejar que una tardía consuma
  todo.
- **Cancel manual**: `CancelToken` chequeado **entre** tools (y al inicio de
  `run_tool`); la API publica `SET scan:{id}:cancel` para abortar un scan colgado
  sin matar el worker.
- **Fallo parcial**: cada tool en su `try/except` (dentro de `run_tool`). Si una
  falla/expira/la bloquea un WAF → `ToolResult.coverage_note` no nulo → el worker
  (05) lo convierte en **Finding-meta** `"tool X no completó"`
  (`confidence=baja`) y lo registra en `scans.coverage`; el flujo **CONTINÚA**.
  **Nunca** se propaga la excepción ni se pierden los findings ya acumulados.
- Todo esto es Python determinista, **sin** involucrar al LLM (05 §4): el agente
  decide *qué* tools correr; el aislamiento de fallos vive bajo él.

## 5. Aislamiento de egress (SSRF lateral)

Dos controles complementarios:

1. **Redes Docker** (§2.1): postgres/redis en `owliver_internal` (`internal:
   true`, sin egress y sin acceso desde `owliver_egress`); **todo** sibling
   `docker run` lleva `--network owliver_egress` (centralizado en `run_tool`).
   Ningún scanner alcanza la red interna.
2. **Bloqueo de destinos peligrosos** — `src/scanning/egress.py`: antes de
   resolver el target, `assert_public_target(url)` rechaza IPs privadas
   (RFC1918, loopback, link-local) y **`169.254.169.254`** (metadata cloud). Se
   aplica también al `RobotsPolicy` y a cualquier redirección seguida.
3. **Defensa en profundidad de host** (deploy, §8/§6 spec): el VPS del demo **no**
   monta credenciales cloud, así aunque un scanner alcanzara metadata no hay
   secreto que robar.

> Excepción controlada: el **perfil demo** corre contra targets en `localhost`
> (juice-shop / bot propio); `assert_public_target` admite un allow-list
> explícito de hosts demo vía config, nunca por defecto.

## 6. Cold-start / warm — `scripts/warm_scanners.sh`

Ejecutado en el bloque de setup (0–2h), **antes** de cualquier scan en vivo:

- `docker pull` de **todas** las imágenes pesadas con **tags pineados**
  (`zaproxy/zap-stable:<sha>`, hexstrike `:stable`) — **nunca `:latest`**.
- `nuclei -update-templates` **una vez** → volumen persistente `nuclei_templates`
  (montado en §2.1).
- Cada run de nuclei lleva **`-duc`** (disable update check) en su `cmd_template`
  de `TOOL_SPECS`, para evitar el fallo de DNS en el primer arranque del
  contenedor.
- **hexstrike NO se pre-carga** si el tiempo aprieta (§10).

`just warm-scanners` envuelve este script; corre como parte del provisioning del
VPS, no en el path de un scan.

## 7. Almacenamiento de evidencia — `src/scanning/evidence.py`

- Screenshots/artefactos se escriben como **archivos** en
  `/data/scans/{scan_id}/{n}.png` (volumen compartido, §3.1).
- El campo `evidence` (jsonb del `Finding`, forma de 06) guarda la **URL
  relativa** (`/static/scans/{id}/{n}.png`), **no** el binario. **NO** base64,
  **NO** MinIO.
- La API expone una **ruta estática FastAPI** (`app.mount("/static/scans",
  StaticFiles(directory="/data/scans"))` en `config/main.py`) que sirve el
  volumen; el export PDF (feature de reportes) embebe desde esa misma ruta.

## 8. hexstrike — opt-out desde el inicio — `src/scanning/health.py`

- Setting `ENABLE_HEXSTRIKE: bool = False` en `settings.py`. Por defecto, el
  servicio `hexstrike` no arranca (`profiles: ["hexstrike"]`, §2.1) y la tool
  **no** entra en `resolve_tools`.
- Si se habilita: **healthcheck al arrancar el worker** (`check_hexstrike()` en
  `startup`/`ctx`): si TCP:8888 no responde, `hexstrike_mcp` **no se pasa** al
  `owasp_agent` (05) y éste opera con el fallback garantizado (ZAP full active +
  Nuclei fuzzing + sqlmap, dentro del budget ~8 min). **Nunca** se invierte tiempo
  de deploy en él.
- `garak`/`promptfoo` son opt-in análogo: requieren target HTTP/REST derivado del
  crawl (03/05), defaults acotados, **nunca** sobre `.gob.mx` automáticos.

## 9. Secuencia de build

1. **06-data-model**: `Finding` / `coverage` / `scans` / enums (`ScanLevel`).
   Bloquea el resto.
2. **01-legal-ethics** (`common/legal`): `constants` (UA, `-rl`, delay),
   `passive_profile.assert_within_passive_profile`, `robots.RobotsPolicy`
   (Protocol). El motor importa de aquí.
3. **`Dockerfile.scanners` + `docker-compose.scanners.yml`**: imagen fat,
   servicio `worker`, redes `owliver_egress`/`owliver_internal`, socket mount,
   volúmenes. `just build-scanners` verde + DooD smoke (`docker run hello-world`
   desde dentro del worker).
4. **`src/scanning/`**: `registry.TOOL_SPECS`, `runner.run_tool`,
   `resolver.resolve_tools`, `robots`, `egress`, `watchdog`, `evidence`,
   `health`. Tests unitarios (§10).
5. **`scripts/warm_scanners.sh`** + `just warm-scanners`: pre-pull pineado +
   templates nuclei al volumen.
6. **05-agent-team**: enganche `RunScanCommand` en `tasks_mapping` + parsers que
   consumen `ToolResult.stdout`; cablea `run_tool`/`resolve_tools`/watchdog en el
   flujo del worker.
7. **Aislamiento**: mover postgres/redis a `owliver_internal`; verificar que un
   sibling **no** alcanza la red interna ni metadata.

El motor se considera `implemented`/coverage>0 cuando la suite §10 pasa y un scan
básico real produce `Finding[]` contra juice-shop dentro del budget.

## 10. Suite de tests — `backend/tests/scanning/`

Sigue la convención del repo (`tests/<área>/...`, pytest async, `conftest.py`,
`fixtures/`). Las tools externas se **mockean** (subprocess/`docker run`); los
tests prueban la **lógica del motor**, no las herramientas.

| Archivo | Asserts |
|---|---|
| `test_resolver_passive.py` | `resolve_tools(is_gov=True, level=basico)` ⊆ `GOV_PASSIVE_PROFILE`; **ZAP-spider y katana ausentes para gov**; nuclei excluye `intrusive,dos,fuzzing,network`; cualquier tool fuera del allow-list ⇒ falla. (Coordina con `01-legal-ethics/plan.md §4 test_passive_profile`; aquí se prueba el **resolutor**, no el contrato — no se duplica el predicado.) |
| `test_run_tool_timeout.py` | tool que excede `spec.timeout` ⇒ `ToolResult(ok=False, timed_out=True, coverage_note≠None)` y **no** propaga excepción |
| `test_run_tool_partial_failure.py` | tool que lanza/no-zero ⇒ `coverage_note` set, `ok=False`; las demás tools del lote **siguen** y sus findings sobreviven |
| `test_watchdog_budget.py` | al exceder `SCAN_BUDGET_S`, el watchdog cancela el scan y aborta tools restantes; el scan cierra (no cuelga) |
| `test_cancel_token.py` | `SET scan:{id}:cancel` en Redis ⇒ `CancelToken.is_set()` True ⇒ siguiente tool no arranca |
| `test_run_tool_dood_flags.py` | el `docker run` sibling incluye `--network owliver_egress`, `--memory`, tag **pineado** (no `:latest`), y `-v` con el **path del HOST** |
| `test_egress_guard.py` | `assert_public_target` rechaza IPs privadas y `169.254.169.254`; admite hosts demo sólo vía allow-list explícita |
| `test_rate_limit_ua.py` | runs nuclei llevan `-rl WORKER_NUCLEI_RATE` y `-duc`; ffuf/katana llevan delay; todo request saliente usa `SCANNER_USER_AGENT` |
| `test_robots_policy.py` | paths `Disallow` excluidos antes de cualquier request; UA usado = `SCANNER_USER_AGENT` (impl del contrato 01) |
| `test_hexstrike_flag.py` | `ENABLE_HEXSTRIKE=False` ⇒ `hexstrike_mcp` ausente de `resolve_tools`; con flag pero healthcheck KO ⇒ tampoco se entrega; fallback documentado |
| `test_evidence_relative_url.py` | `evidence` guarda URL relativa (`/static/scans/...`), nunca base64; archivo escrito en `/data/scans/{id}/` |

## 11. Decisiones / riesgos

1. **Híbrido subprocess + DooD, NO DinD** — congelado desde la hora 0 (spec §1/§3).
   DinD exige `--privileged`, es lento y rompe en cloud. Riesgo: el socket mount
   no funciona en el PaaS → mitigado deployando en **VPS Linux** con socket y
   egress (spec §6), validado con un DooD smoke en el build (§9.3).
2. **`run_tool()` único punto de invocación** — centraliza red, límites, tag
   pineado, timeout, `-v` host y rate-limit. Evita que un flag de aislamiento se
   olvide en una llamada suelta. El test `test_run_tool_dood_flags` lo blinda.
3. **`-v` apunta al path del HOST** (no del worker) bajo socket mount — el bug más
   sutil de DooD; `run_tool` exige `host_shared_dir` explícito y hay test.
4. **Fallo parcial > scan perfecto** — una tool colgada nunca tumba el scan;
   degrada a Finding-meta + `coverage` y sigue. El básico (camino del ranking gov)
   **nunca** se corta.
5. **El motor no parsea ni decide tools** — sólo ejecuta y entrega `stdout` crudo;
   el parseo a `Finding[]` y el "qué tool por nivel" los poseen 05 y 02
   respectivamente. Mantiene el LLM fuera del path de datos (05 §2).
6. **Contrato pasivo importado, no redefinido** — `resolve_tools(gov, básico)`
   valida contra `assert_within_passive_profile` de 01; si 02 cambia la whitelist
   gov de forma que viole el perfil pasivo, el test **rompe**. Es el invariante
   legal aplicado en el motor.
7. **hexstrike a CERO desde el inicio** (spec §10) — `ENABLE_HEXSTRIKE=False` +
   `profiles`; el avanzado se narra con ZAP full + Nuclei fuzzing + sqlmap.
   Libera la hora 18–19 para deploy/pulido.
8. **Cold-start es un riesgo de demo real** (spec §7) — sin pre-pull pineado +
   templates nuclei al volumen + `-duc`, el primer run falla por DNS y el básico
   no produce findings. `warm-scanners` corre en el provisioning, no en un scan.
