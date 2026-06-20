# Owliver — Especificación de Producto (overview + índice)

> **Owliver** 🦉 — El búho que vigila la seguridad de los sitios web. Pentesting
> automático orquestado por agentes IA, con un ángulo único: además del OWASP
> clásico, audita la **superficie agéntica** (chatbots, cajas de prompt, widgets
> LLM) buscando prompt-injection y jailbreaks.
>
> Documento de handoff para desarrollo. Contexto: **hackathon de 20 horas**.
> Fecha: 2026-06-20.
>
> **Este archivo es el _overview + índice_.** El detalle por feature vive en
> [`product/specs/NN-*`](specs/). Las secciones **§3–§14** se dividieron en
> subspecs numerados (ver [§ Índice de subspecs](#índice-de-subspecs)); aquí
> permanecen, con su numeración original intacta, las partes transversales:
> **§1** visión, **§2** decisiones cerradas, **§5** diagrama de arquitectura,
> **§12** alcance/features swing y **§15–§17** plan, riesgos y demo. Cualquier
> referencia `§N`/`§N.M` desde los subspecs sigue resolviendo (las §3–§14 vía el
> índice; las §1/§2/§5/§12/§15/§16/§17 a este documento).

---

## 1. Visión en una frase

Una plataforma donde cualquiera ingresa una URL + nivel de ataque, un equipo de
agentes IA ejecuta un pentest automático (OWASP **+** superficie agéntica), y se
genera un reporte **ultra fácil de entender pero técnicamente valioso**, con un
**score A–F**. Los resultados alimentan un **ranking público de sitios del Estado
(México, `.gob.mx`)** y **watchlists privadas** para monitoreo continuo.

El diferenciador frente a cualquier scanner existente: **medimos la seguridad de
los chatbots/IA embebidos**, algo que casi nadie audita hoy.

---

## 2. Decisiones de arquitectura (cerradas)

| # | Decisión | Elección |
|---|----------|----------|
| 1 | **Postura de intrusividad** | Los 3 niveles = intrusividad creciente **sobre cualquier URL** (sin verificación de propiedad). El modo activo se permite contra cualquier página detrás de **advertencia + gate de atestación** (checkbox + términos + consentimiento registrado) antes de encolar. **Escaneos automáticos (seed/cron) = solo pasivos.** La responsabilidad legal del activo recae en el usuario que atesta |
| 2 | **Motor de pentesting** | **Híbrido**: capa base garantizada (Nuclei + ZAP baseline + testssl.sh + WhatWeb) que SIEMPRE produce findings, + **hexstrike-ai** como power-up para nivel avanzado |
| 3 | **Runtime IA / orquestación** | **Agno** (Teams): un coordinador + 2 miembros. Modelos: **Sonnet** para subagentes, **Opus** para orquestador + redacción del reporte |
| 4 | **Stack de app + cola** | **Next.js** (UI) + **FastAPI** (API) + **Redis** (cola **Arq** + pub/sub) + **Postgres** + **worker Python/Agno** |
| 5 | **Motor LLM red-team** | **Híbrido**: detección propia (crawl + clasificación LLM + fingerprints de vendors) + **garak** / **promptfoo** para el ataque |
| 6 | **Score** | **Doble sub-score** 0–100 (🛡️ Web/OWASP y 🤖 Agéntico/LLM) → score global + **grado A–F** estilo Mozilla Observatory |
| 7 | **Ranking gov seed** | **México** (`.gob.mx`), ~30–50 dominios, auto-escaneados en nivel básico/pasivo en schedule |
| 8 | **Alcance 20h** | Núcleo + las 4 swing features (monitoreo+alertas, live view, PDF+share, hexstrike) — TODAS in-scope, con orden de recorte documentado |

---

## 5. Arquitectura del sistema

```
┌─────────────┐     HTTPS     ┌──────────────┐
│  Next.js    │ ────────────► │   FastAPI    │
│  (frontend) │ ◄──── SSE ──── │   (API)      │
└─────────────┘   live view   └──────┬───────┘
                                      │ enqueue (Arq)
                                      ▼
                               ┌────────────┐        ┌──────────────┐
                               │   Redis    │◄──────►│  Worker      │
                               │ queue +    │ pub/sub│  (Python/    │
                               │ pub/sub    │        │   Agno Team) │
                               └────────────┘        └──────┬───────┘
                                                            │
                       ┌────────────────────────────────────┼───────────────┐
                       ▼                                    ▼                ▼
              ┌─────────────────┐              ┌──────────────────┐  ┌──────────────┐
              │ Orquestador     │              │ Subagente OWASP  │  │ Subagente    │
              │ (Opus, coord.)  │─── llama ───►│ (Sonnet)         │  │ Agéntico     │
              │ coordina +      │              │ tools: scanners  │  │ (Sonnet)     │
              │ resumen ejec.   │              │ Docker (hx=off)  │  │ crawl+puente │
              └────────┬────────┘              └──────────────────┘  └──────────────┘
                       │ findings + scores
                       ▼
              ┌─────────────────┐        Herramientas en contenedores Docker:
              │   Postgres      │        nuclei · zap · testssl · whatweb · nikto
              │  (findings,     │        katana · ffuf · sqlmap · garak · promptfoo
              │   scans, sites) │        hexstrike-ai (MCP, opcional / off)
              └─────────────────┘
```

**Servicios (docker-compose):** `web` (Next.js), `api` (FastAPI), `worker`
(Python/Agno — corre **dentro** de la imagen `scanners`), `redis`, `postgres`,
`scanners` (imagen fat con las CLIs de pentest preinstaladas), `hexstrike` (MCP
server, contenedor pesado aparte), `scheduler` (cron de re-escaneos).

> El detalle de ejecución (patrón Docker DooD/subprocess, concurrencia, watchdog,
> aislamiento de egress, cold-start, almacenamiento de evidencia) vive en
> [`04-scanning-engine`](specs/04-scanning-engine/README.md); el diseño del Agno
> Team (orquestador + 2 subagentes, parsing fuera del LLM) en
> [`05-agent-team`](specs/05-agent-team/README.md).

---

## Índice de subspecs

El detalle por feature (§3–§14 de la spec original + el sub-spec de frontend) se
dividió en 13 subspecs numerados bajo [`product/specs/`](specs/). Cada uno fusiona
el contenido autoritativo de `spec.md` con la profundidad de implementación del
análisis de huecos, y lleva frontmatter (`status: pending`, `coverage: 0`).

| # | Subspec | § origen | Qué cubre |
|---|---------|----------|-----------|
| 01 | [legal-ethics](specs/01-legal-ethics/README.md) | §3 | La invariante legal/ética aplicada en código: atestación persistida, automáticos solo pasivos, ranking público solo pasivo y "pasivo" definido como whitelist verificable. |
| 02 | [attack-levels](specs/02-attack-levels/README.md) | §4 | Los tres niveles de intrusividad (pasivo/básico, intermedio, avanzado) y la batería de herramientas+flags del subagente OWASP web, con la whitelist `(is_gov, level)` y robots.txt. |
| 03 | [agentic-surface](specs/03-agentic-surface/README.md) | §4 | Sondeo de chatbots/widgets LLM embebidos: detección por fingerprints + LLM, puente Playwright y LLM-juez con evidencia tipada. **El diferenciador.** |
| 04 | [scanning-engine](specs/04-scanning-engine/README.md) | §5, §13 | Cómo el worker lanza los scanners: imagen fat vs. DooD por socket, redes aisladas, timeouts + watchdog, cold-start y stack de herramientas. |
| 05 | [agent-team](specs/05-agent-team/README.md) | §6 | El Agno Team (Opus orquestador + 2 Sonnet) donde las tool-functions parsean a `Finding[]` en Python y el LLM queda fuera del camino de datos. |
| 06 | [data-model](specs/06-data-model/README.md) | §7, §8 | El esquema Postgres del motor de pentest (sites, scans, findings, agentic_surface, scan_events, watchlist, magic_tokens) y los contratos Pydantic `Finding`/`AgenticResult`. |
| 07 | [scoring](specs/07-scoring/README.md) | §9 | Doble sub-score web/agéntico → overall + grado A–F, con `penalty_raw` sin cap, cap por cobertura parcial y `agentic_status` de tres estados. |
| 08 | [ranking-watchlists](specs/08-ranking-watchlists/README.md) | §10, §12 | Leaderboard público `.gob.mx` (solo pasivo, sembrado y pre-horneado), watchlists privadas y monitoreo/alertas vía cron de Arq + Resend/Slack. |
| 09 | [reporting](specs/09-reporting/README.md) | §11 | Reporte de dos capas (ejecutiva con doble gauge A–F + párrafo de Opus, técnica en acordeón), export PDF y link público `/r/[token]` con exploits redactados. |
| 10 | [realtime-live-view](specs/10-realtime-live-view/README.md) | §12.1 | Live view del pentest por SSE: Postgres es la verdad (`scan_events`), Redis solo el tail, con replay-then-tail y auth por cookie. |
| 11 | [auth-magic-link](specs/11-auth-magic-link/README.md) | §12.2, §14.1 | Flujo magic-link sin contraseña: 4 pantallas en `(public)`, canje de `magic_tokens` y cookie HttpOnly que autentica la live-view SSE. |
| 12 | [api](specs/12-api/README.md) | §14 | Superficie HTTP: encolado idempotente de scans, AuthZ anti-IDOR, cancelación/health, contrato SSE, CRUD watchlist, paginación y formato de error único. |
| 13 | [frontend](specs/13-frontend/README.md) | `owliver-frontend.md` | Todo el frontend Next.js: Hall of Shame, gate de atestación, el Live Pentest Theater en modo SOC, reporte "Owliver te explica" y superficies públicas/privadas. |

**Specs hermanas (boilerplate SaaS, no pentest):**
[`specs/data-model`](specs/data-model/README.md),
[`specs/roles-permissions`](specs/roles-permissions/README.md); los planes de
implementación (CÓMO) viven en [`product/plans/`](plans/).

**Insumos del split (ya fusionados, históricos):**
[`specs/_archive/`](specs/_archive/) contiene `spec-gaps.md` (refinamiento) y
`spec-consistency-review.md` (auditoría aplicada). El brief de dirección visual
es [`design-prompt.md`](design-prompt.md).

---

## 12. Alcance 20h y features swing

Núcleo (form → scan → `Finding[]` → reporte) + las **4 swing features** — todas
in-scope, con orden de recorte documentado en §15:

1. **Monitoreo recurrente + alertas:** el `scheduler` re-encola escaneos de
   `watchlist.monitor=true` (y del seed gov) vía el cron nativo de **Arq**.
   Alertas por **Resend** (email) y/o **Slack webhook** cuando baja el grado o
   aparece un finding `critical` (compara `findings.first_seen` a nivel site vía
   `dedupe_key`). Alertas in-app = recorte. Detalle en
   [`08-ranking-watchlists`](specs/08-ranking-watchlists/README.md).
2. **Vista en vivo del pentest:** el worker publica eventos a Redis pub/sub →
   FastAPI los expone por **SSE** → Next.js renderiza los pasos del agente. Alto
   impacto en demo. Esquema, replay y auth en
   [`10-realtime-live-view`](specs/10-realtime-live-view/README.md).
3. **Export PDF + link público:** [`09-reporting`](specs/09-reporting/README.md).
4. **hexstrike-ai (power-up avanzado):** servidor MCP como tool del subagente
   OWASP solo en nivel avanzado. **Recortado a CERO desde el inicio del plan**
   (ver §15 y
   [`04-scanning-engine`](specs/04-scanning-engine/README.md)); fallback = ZAP
   full active + Nuclei fuzzing.

**Auth (default):** JWT + magic-link por email. Multi-tenant vía `owner_user_id` /
`watchlist.user_id`. Las 4 pantallas del flujo en
[`11-auth-magic-link`](specs/11-auth-magic-link/README.md).

---

## 15. Plan de 20 horas (equipo ~3–4)

### Hora 0–2: congelar contratos + abrir 4 carriles

El plan **no es secuencial**. Con 3–4 personas, una línea de tiempo en serie es 1 carril con 3 espectadores. El bloque 0–2 existe para producir **artefactos congelados** que desbloquean los 4 carriles en paralelo; nadie los toca después de la hora 2 (cambiarlos rompe a tres personas a la vez).

**5 artefactos innegociables de la hora 0–2:**

1. **`finding.py`** — `Finding` + `AgenticResult` Pydantic + enums (`severity`, `confidence`, `source`, `category`). Contrato entre P2 (parsers), P3 (agéntico) y P4 (reporte).
2. **`events.py`** — shape de `scan_event` con `seq` (monótono por scan) + `type` discriminante (`agent_status|tool_start|tool_end|finding|phase|score|done|error`). Contrato worker→frontend. Se congela aunque el live-view sea recortable: todos los carriles emiten eventos.
3. **Stubs de API con fixtures** — endpoints de §14 devolviendo fixtures con el shape correcto. P4 (frontend) trabaja contra ellos desde la hora 2 en vez de la hora 11.
4. **Decisión de infra** — **VPS Linux** (DigitalOcean/Hetzner, 8GB+ RAM) con docker-compose, redes aisladas `owliver_egress`/`owliver_internal`, `docker pull` + warm de imágenes (tags pineados, no `:latest`) + `nuclei -update-templates` a volumen con flag `-duc` en cada run. Patrón Docker: worker dentro de imagen `scanners` fat (`subprocess.run`) + socket mount (DooD, **no DinD**) solo para ZAP/hexstrike. **No PaaS gestionado.**
5. **Secretos + `is_gov`** — `settings.py` (pydantic-settings) que **falla ruidosamente** al arranque si falta una key; `.env` en `.gitignore` desde el commit 0; cap de tokens en el dashboard de Anthropic. `is_gov = hostname.endswith('.gob.mx')` calculado al insertar el site.

En el mismo bloque se fija **Arq** (no RQ: el worker hace `asyncio.gather`), el **partial unique index** de idempotencia, `scans.id` UUIDv4 y el `exception_handler` global de FastAPI, y se carga el **seed de fixtures del leaderboard** (ver §15 tabla y [`06-data-model`](specs/06-data-model/README.md)/[`08-ranking-watchlists`](specs/08-ranking-watchlists/README.md)).

**Carriles (no se bloquean entre sí):**

| Carril | Dueño de | Trabaja contra |
|---|---|---|
| **P1** | infra / cola / API + seed gov | el VPS y los contratos |
| **P2** | parsers OWASP + scoring (Python) | `finding.py` |
| **P3** | agéntico: bot propio plantado + puente Playwright + juez | `finding.py` + bot local |
| **P4** | frontend: leaderboard + form + reporte | **fixtures** de los stubs |

### Tabla de horas

| Horas | Entregable |
|---|---|
| **0–2** | **Congelar los 5 artefactos** + abrir carriles. Scaffolding: repo, docker-compose (postgres, redis, api, worker, web, scanners) con redes aisladas, migraciones, `settings.py` fail-loud, **fixtures del leaderboard** cargados por CLI, warm de imágenes + templates Nuclei |
| **2–5** | **P1/P2:** helper `run_tool()` + imagen `scanners` + **3 parsers de alta densidad** (Nuclei JSONL, testssl `-oJ`, security-headers/Observatory) → `Finding[]` en Python (NO vía `response_model`). `POST /scans` + cola Arq + pickup. **Nivel básico end-to-end con findings reales en la UI** |
| **5–8** | **P1/P2:** Agno Team (orquestador + 2 miembros; tools devuelven `Finding[]` ya parseado, el LLM solo elige qué tools correr). Scoring + dedup en Python (`penalty_raw`, `coverage`, grado E, cap-C si parcial). Whitelist tools+flags por `(is_gov, level)` + robots.txt + enforcement `is_gov→422` en `POST /scans`. ZAP baseline como 4º parser |
| **8–11** | **P3:** subagente agéntico — bot propio plantado + **detección por fingerprints deterministas (1ª pasada)** + lazy-load + **puente Playwright-maneja-conversación** + juez con canary/rúbrica → findings + `agentic_status` (3 estados). **P4** ya avanza contra fixtures |
| **11–14** | **P4:** route-group `(public)`, leaderboard RSC, form de scan (validación URL + gate condicional + redirect), **reporte** (doble gauge + resumen ejecutivo Opus + accordion), `/r/[token]` con redacción de exploits. **P1:** magic-link callback `GET /auth/callback` + tabla `magic_tokens` |
| **14–16** | Live view: `scan_events` con `seq`+`type`, **replay-then-tail**, auth por cookie, **demo-level <90s**. Correr seed `.gob.mx` **en el VPS** en pasivo → sobrescribe fixtures si termina a tiempo |
| **16–18** | Cron monitoreo + alertas (Resend/Slack) vía `dedupe_key` + first/last_seen a nivel site; watchlist; CRUD (`GET /scans`, cancel, `DELETE /watchlist`, `/health`, `/ready`) + rate-limit; export PDF + evidencia en volumen |
| **18–20** | **Deploy + pitch.** hexstrike YA en cero (ver abajo). Pre-escanear seed en el VPS, **grabar video de respaldo de 90s**, guion, pulido |

### Checkpoints binarios (recortar a tiempo, no a la hora 19)

Cada checkpoint = **demo del estado real**, no "casi listo". Si no está verde, se recorta en ese punto.

- **H8** — "nivel básico end-to-end con findings reales en la UI" verde. Si no → congelar todo y volcar a P1/P2 (núcleo).
- **H12** — agéntico mínimo (bot propio + 1 probe → 1 finding agéntico visible) funciona. Si no → cortar el ataque, dejar solo detección + inventario.
- **H16** — live-view SSE renderiza con replay. Si no → cortar live-view, usar el GIF/video pre-grabado.
- **H18** — **congelar features**; solo deploy + pulido + guion.

### Orden de recorte

**hexstrike-ai ya está en CERO desde el inicio del plan** (no es un slot de la hora 18: el "avanzado" es ZAP full active + Nuclei fuzzing + sqlmap sobre 1 param conocido, dentro del budget ~8 min (pre-horneado/time-boxed en el demo) — narrativa, no orquestación autónoma). El orden de recorte restante, si el tiempo aprieta, es:
`live view` → `monitoreo/alertas` → `PDF/share` → `watchlist UI`.

**Nunca se corta:** núcleo (form→scan→`Finding[]`→reporte) + ranking gov + doble score + el finding agéntico estrella contra el bot propio plantado.

---

## 16. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| **Trabajo en serie** (3–4 personas, 1 carril) | Congelar `finding.py` + `events.py` + stubs de API en la hora 0–2; abrir carriles P1–P4 contra contratos/fixtures (§15) |
| **Parsers subestimados** (8+ formatos heterogéneos, el corazón del producto en 1 renglón) | 1 persona full-time en parsers; priorizar **3 de alta densidad y buen JSON** (Nuclei/testssl/security-headers) → garantizan básico + ranking; mapeo OWASP = **dict/YAML estático curado**, nunca pedírselo al LLM |
| **El LLM arruina el `Finding[]`** (tools + `response_model` es zona de bug en Agno/Claude; re-teclea/alucina/trunca) | Sacar el parsing del LLM: las tool-functions devuelven `Finding[]` parseado en Python; el agente solo elige qué tools correr; `response_model` solo para el resumen ejecutivo de Opus. Smoke-test de structured-output antes del demo |
| **Puente agéntico inexistente** (garak/promptfoo no atacan una web; muere el diferenciador #1) | **Playwright maneja la conversación** (abre widget, inyecta payload, lee DOM, pasa al juez) — resuelve sesión/cookies/CSRF gratis; banco de payloads propio; finding estrella contra **bot propio plantado** (secreto en system-prompt) 100% reproducible |
| **Costo/latencia LLM del red-team** (garak `generations=10`; grader de promptfoo es OpenAI por default) | Camino Playwright + juez Claude propio elimina ambos; cap duro de N payloads/chatbot; garak/promptfoo **jamás** sobre `.gob.mx` automáticos |
| **Secretos / API keys** (worker sin credenciales no arranca; `.env` commiteado filtra keys con presupuesto) | `.env` en `.gitignore` desde el commit 0 + `.env.example`; `settings.py` **fail-loud** al arranque; inyección vía `env_file`; cap de tokens en el dashboard de Anthropic antes del pitch |
| **Live-view vacío en el momento estrella** (pub/sub at-most-once; entrar tarde/recargar) | `scan_events` persistido con `seq`+`type`; **replay-then-tail** desde Postgres; auth por cookie; compresión desactivada en la ruta SSE |
| **Scan lento en vivo** (ZAP full/garak/hexstrike duran minutos, el pitch dura minutos) | **demo-level** con timeout duro ~60–90s (Nuclei subset + testssl + 1 probe al bot propio); todo lo pesado se muestra desde resultados pre-horneados |
| **Leaderboard vacío/lleno de "failed"** en el pitch | **Pre-hornear fixtures** (30–50 filas con grados + 1 finding agéntico plantado) en la hora 0–2; los scans reales sobrescriben solo si terminan a tiempo |
| **Deploy "funcionaba en mi máquina"** | VPS Linux con socket + egress libre desde la hora 0 (no PaaS); pre-escanear el seed **en el VPS**; live-view contra targets en localhost; **video de respaldo de 90s** la noche anterior |
| **Egress de scanners sin aislar** (SSRF lateral a postgres/redis/metadata cloud) | Red `owliver_egress` separada de `owliver_internal`; scanners siempre `--network=owliver_egress`; bloquear IPs privadas + `169.254.169.254`; sin credenciales cloud montadas en el host |
| **Observabilidad nula a las 3am** | Logging estructurado con `scan_id` por línea (structlog); `tools_status jsonb` como fuente de debug; `GET /scans/{id}` expone `tools_status`+`coverage`+`error`; `docker compose logs -f worker \| grep scan_id` |
| **Cold start** (ZAP ~2GB, Nuclei descarga 12k templates y falla por DNS) | `docker pull` + `nuclei -update-templates` a volumen en la hora 0–2; flag `-duc`; tags pineados |
| **hexstrike pesado/frágil** | **Cero desde el inicio** (no en la hora 18); "avanzado" = ZAP full active + Nuclei fuzzing + sqlmap, dentro del budget ~8 min (pre-horneado en el demo); libera la hora 18–19 para deploy/pulido |
| **Scan colgado bloquea worker y cola** | Timeout duro por tool en `subprocess.run`; budget global ~8 min; `try/except` por tool → Finding-meta "tool X no completó" y **continuar**; `POST /scans/{id}/cancel` |
| **Scan parcial premia al sitio que rompe el scanner** | `coverage jsonb`; si faltó ≥1 scanner base → **cap del grado en C** + etiqueta "cobertura parcial"; nunca mostrar A con cobertura parcial |
| **Empate F/0 en el leaderboard** (mayoría de `.gob.mx` en 0) | Persistir `penalty_raw` sin clamp; ordenar por `(overall_grade ASC, penalty_raw DESC)`; grado E intermedio |
| **Legal (sitios gov / activos)** | Enforcement en `POST /scans` (`is_gov→422`); automáticos solo pasivos; ranking público solo pasivo; activo iniciado por usuario = privado de su cuenta (§3) |
| **Falsos positivos** | Campo `confidence` + triage del orquestador (Opus); juez agéntico con assertion explícito por técnica (canary determinista) |

---

## 17. Criterios de demo / pitch

> **Regla de oro del pitch:** nada que tarde minutos corre en vivo. La data del leaderboard está **pre-horneada**, el live-view es un **perfil controlado <90s** contra targets en localhost, y existe un **video de respaldo de 90s** grabado la noche anterior. El presentador nunca hace clic en "escanear avanzado" contra un `.gob.mx` en vivo.

### Guion

1. **Abrir `/`** → leaderboard de `.gob.mx` **ya poblado** (fixtures cargados en la hora 0–2, sobrescritos por scans reales solo si terminaron a tiempo). Grados A–F ordenados peores-primero (`overall_grade ASC, penalty_raw DESC`), con el contraste 🛡️ Web vs 🤖 Agéntico visible y al menos una fila estrella (ej. SAT "C web / F agéntico").
2. **Live-view controlado:** ingresar la URL del **bot propio plantado** (target agéntico) o de **OWASP Juice Shop** (target web), ambos en localhost, a **demo-level** → live-view renderizando los 2 subagentes, herramientas corriendo y findings apareciendo, con **timeout garantizado <90s** por config. Al recargar la página, el **replay** desde Postgres repinta el progreso (no queda vacío).
3. **Abrir el reporte:** grado grande A–F, párrafo "Owliver te explica" (Opus), y el **finding agéntico estrella** — system-prompt leak del bot propio con su **canary** como evidencia incontestable (`evidence = {payload, respuesta_cruda, token_filtrado}`). 100% reproducible porque el secreto vive en su system-prompt.
4. **Mostrar export PDF + link público** `/r/{token}` — destacando que el link público **redacta los payloads de explotación** (muestra tipo + impacto, no el exploit).
5. **Cierre:** *"Owliver vigila la seguridad del Estado y de tu IA — lo que nadie más está midiendo."*

### Plan B (en orden de degradación)

- **Si el live-view SSE falla** (checkpoint H16 en rojo) → reproducir el **video de respaldo de 90s**; el resto del guion sigue igual sobre data pre-horneada.
- **Si el bot propio no responde** → mostrar el finding agéntico estrella desde los **fixtures** (ya plantado en el seed del leaderboard).
- **Si la red del venue bloquea egress** → todo el demo corre contra el **VPS + targets en localhost**; no se depende de la wifi del venue ni de alcanzar `.gob.mx` en vivo.
- **Si PDF/share se recortó** (orden de recorte, §15) → mostrar la **página in-app del reporte** con la redacción de exploits ahí mismo; se omiten el PDF y el `/r/{token}` sin perder el clímax del guion.
