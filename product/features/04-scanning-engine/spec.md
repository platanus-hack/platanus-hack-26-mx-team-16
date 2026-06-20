---
feature: scanning-engine
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §5, §13; spec-gaps.md §1, §7
---

# Owliver — Motor de escaneo (Docker, ejecución, aislamiento)

> El motor de escaneo es la maquinaria que convierte una URL en evidencia
> cruda explotable: cómo el worker (que **ya es** un contenedor) lanza cada
> scanner, con qué mecanismo (subprocess dentro de la imagen `scanners` vs.
> sibling/DooD por socket Docker), bajo qué timeouts y budget global, sobre
> qué redes aisladas, con qué imágenes pre-calentadas y plantillas
> pre-descargadas, y con qué watchdog aborta la batería antes de tumbar el
> host o colgar el live-view. No cubre el parseo de salida cruda a `Finding[]`
> ni la orquestación del equipo Agno (eso vive en
> [05-agent-team](../05-agent-team/spec.md)), ni la forma del `Finding`
> (ver [06-data-model](../06-data-model/spec.md)).

## 1. Principio rector

El worker **es** un contenedor; nunca se invoca un scanner "en el aire". El
patrón de ejecución es **híbrido pragmático**, decidido por adelantado para no
descubrir el agujero a las 3am: las CLIs ligeras corren por `subprocess` dentro
de una sola imagen fat `scanners`, y los contenedores pesados (ZAP, hexstrike)
se lanzan como **siblings vía el socket Docker del host (DooD), nunca DinD**.

Esta es la pieza que más fácil se rompe en producción: descubrir tarde que el
socket mount no funciona en el PaaS quema 3–4 h, y sin un patrón funcional no
hay **ni un solo finding real**. Por eso la decisión de mecanismo está congelada
desde la hora 0 (ver también §6, deploy en VPS).

## 2. Servicios (docker-compose)

El stack se compone de los siguientes servicios:

- `web` — Next.js (frontend).
- `api` — FastAPI.
- `worker` — Python/Agno. **Corre dentro de la imagen `scanners`** (no es una
  imagen aparte): el proceso del worker vive en el mismo contenedor que trae
  preinstaladas las CLIs de pentest.
- `redis` — cola (Arq) + pub/sub para el live-view.
- `postgres` — findings, scans, sites.
- `scanners` — imagen fat con las CLIs de pentest preinstaladas (es la base del
  worker).
- `hexstrike` — MCP server, contenedor pesado aparte (imagen Kali, varios GB).
- `scheduler` — cron de re-escaneos.

## 3. Patrón de ejecución de scanners (DooD vs DinD)

La decisión de invocación Docker estaba sin cerrar en versiones tempranas de la
spec ("cada herramienta corre en su contenedor" sin decir *cómo* el worker, que
ya es un contenedor, los lanza). Las opciones consideradas —`docker run` por
invocación, `docker exec` a un contenedor vivo, DinD, socket mount
(siblings/DooD), o CLIs preinstaladas en la imagen del worker— cambian
radicalmente filesystem compartido, red y permisos. La decisión congelada es el
**híbrido pragmático**:

- **CLIs ligeras → `subprocess` dentro de la imagen `scanners`.** El worker corre
  dentro de la imagen fat `scanners`, que trae preinstaladas **nuclei, testssl,
  whatweb, nikto, katana, ffuf, sqlmap, subfinder y dnsx**. Cada una se ejecuta
  con `subprocess.run([...], capture_output=True, timeout=N)`. Sin socket, sin
  DinD para el caso común.
- **Contenedores pesados (ZAP, hexstrike) → sibling/DooD.** ZAP
  (`zap-baseline.py` / `zap-full-scan.py`) y hexstrike (MCP) van en su propio
  contenedor. El worker monta el socket del host (`/var/run/docker.sock`, patrón
  **DooD/sibling — NO DinD**, que exige `--privileged`, es lento y rompe en
  cloud) y los lanza por un **único helper** `run_tool(image, cmd, shared_dir)`.
- **NO DinD.** Docker-in-Docker requiere `--privileged`, es lento y se rompe en
  cloud; queda descartado.

### 3.1 Directorio compartido de scan

Un directorio del host `/data/scans/{scan_id}/` se monta en el worker y en cada
scanner pesado. **Con socket mount, el flag `-v` apunta al path del HOST, no del
contenedor worker** (porque el socket habla con el daemon del host, que solo
conoce paths del host). Este directorio es también donde se persiste la
evidencia (ver §8).

### 3.2 El helper `run_tool()`

Toda invocación de contenedor pesado pasa por un **único** helper
`run_tool(image, cmd, shared_dir)`. Centralizar aquí el `docker run` permite
aplicar de forma uniforme: el `--network=owliver_egress` (ver §5), los límites
`--memory`/`--cpus` (ver §4), el montaje `-v` del directorio compartido apuntando
al path del host, los tags pineados de imagen (ver §7) y el timeout duro (ver §4).

## 4. Concurrencia, límites de recursos y watchdog

### 4.1 Concurrencia del worker

El worker corre con `max_jobs=1` (subir a `2` solo si el host aguanta). El seed
gob.mx **no** se encola de golpe (50 escaneos simultáneos tumban el host justo
en el demo, dejándolo sin RAM/CPU en la presentación): se pre-escanean 5–8 sitios
antes del demo y se persisten como fixtures (ver
[08-ranking-watchlists](../08-ranking-watchlists/spec.md) y la persistencia de
fixtures descrita en spec.md (overview)), y el resto corre en background.

Cada `docker run` pesado lleva `--memory` / `--cpus` (ZAP `-m 2g`), porque ZAP
full + garak full consumen GBs de RAM cada uno. El nivel básico apunta a cerrar
en **<90s por sitio** corriendo sus tools de forma **concurrente** (el wall-clock
es ≈ el timeout máximo, no la suma serial de timeouts).

### 4.2 Timeouts duros por tool + budget global

Cada tool tiene un **timeout duro** en `subprocess.run(timeout=)` (o en el
`run_tool()` para las pesadas) y existe un **budget global de scan ~8 min**. La
tabla canónica tool → mecanismo → timeout es:

| Tool | Mecanismo | Timeout |
|---|---|---|
| nuclei | `subprocess` (imagen `scanners`) | 90s |
| testssl | `subprocess` | 60s |
| security-headers / Observatory | `subprocess` (1 request a la raíz) | 30s |
| whatweb | `subprocess` | 30s |
| nikto | `subprocess` | 90s |
| katana | `subprocess` | 60s |
| ffuf / gobuster | `subprocess` | 90s |
| sqlmap | `subprocess` | 120s |
| subfinder / dnsx | `subprocess` | 60s |
| ZAP baseline | `run_tool()` (DooD, `-m 2g`) | 120s |
| ZAP full active | `run_tool()` (DooD, `-m 2g`) | 240s |
| garak | `subprocess` | 180s |
| promptfoo | `subprocess` | 120s |
| hexstrike-ai | `run_tool()` (MCP, DooD) | feature-flag / time-boxed |

### 4.3 Watchdog y política de fallo parcial

Un scan colgado bloquea el worker y la cola, mata el live-view y arruina el
demo; con ZAP active / sqlmap / nikto colgarse es lo normal. Por eso el motor
implementa una política explícita de cancelación y fallo parcial:

- **Timeout duro por tool** (los de la tabla de §4.2) más el **budget global
  ~8 min**. Un **watchdog** vigila el budget global y el time-box: cuando se
  agota el presupuesto o el límite de tiempo, **aborta la batería** restante en
  lugar de dejar que una tool tardía consuma todo.
- **Cada tool se ejecuta en su propio `try/except`.** Si una tool falla o expira,
  el motor emite un Finding meta `"tool X no completó"` con confidence baja y
  **CONTINÚA**; **nunca** propaga la excepción ni mata los findings ya
  acumulados.
- Como las tool-functions devuelven `Finding[]` deterministas (parseo en Python,
  no en el LLM — ver [05-agent-team](../05-agent-team/spec.md)), toda esta
  gestión de timeouts, cancelación y fallo parcial se maneja en Python **sin
  involucrar al LLM**. El agente Agno solo decide *cuáles* tools correr por
  nivel; el aislamiento de fallos vive bajo él.

## 5. Aislamiento de egress (SSRF lateral)

Los scanners atacan URLs externas con egress a internet; con sibling containers
arrancarían en la red por defecto de Docker y podrían alcanzar postgres/redis o
el endpoint de metadata del cloud (`169.254.169.254`) — un SSRF lateral. El
aislamiento se hace por **redes Docker dedicadas**:

- Red `owliver_egress` (bridge, salida a internet) — **todo scanner siempre** se
  lanza con `--network=owliver_egress`.
- Red `owliver_internal` para postgres/redis — **sin** egress y sin acceso desde
  `owliver_egress`. postgres/redis viven aquí, aislados de los scanners.
- **Bloquear IPs privadas y `169.254.169.254`** en el camino de los scanners.
- El host del demo **no** debe tener credenciales cloud montadas (defensa en
  profundidad: aunque un scanner alcance metadata, no hay secreto que robar).

## 6. Deploy: VPS, no PaaS gestionado

El stack completo (`web` + `api` + `worker` + `redis` + `postgres` + `scanners`
+ `hexstrike` + `scheduler`) **no** levanta en free-tier ni necesariamente en un
PaaS gestionado, porque el patrón DooD exige el **socket del host**, que los PaaS
gestionados no exponen. Además los scanners necesitan **egress** a los `.gob.mx`,
y la wifi del venue o un WAF pueden bloquearlo.

Decisión (desde la hora 0): un **VPS Linux** (DigitalOcean / Hetzner, 8GB+ RAM)
con docker-compose, socket disponible y egress libre. **NO PaaS gestionado.** El
seed gob.mx se pre-escanea **en el VPS** antes del demo (no se depende de la wifi
del venue). El live-view del pitch corre contra **targets controlados en
localhost** (el bot propio + juice-shop / DVWA dockerizado), **no** contra
`.gob.mx` en vivo, y se graba un **video de respaldo de 90s** la noche anterior
como fallback. (La estrategia de tiempo de demo / "demo level" y el live-view
pertenecen a [10-realtime-live-view](../10-realtime-live-view/spec.md); aquí solo
se fija la restricción de infraestructura que la habilita.)

## 7. Cold start / warm de imágenes y plantillas

ZAP pesa ~1.5–2 GB, la imagen Kali de hexstrike varios GB, y Nuclei descarga
12k+ templates en el primer run — que **falla por DNS dentro del contenedor sin
pre-pull**. Si el primer `docker run nuclei` en vivo intenta descargar templates
y falla, el nivel básico (que **nunca** se corta) no produce findings. Por eso,
en el bloque de setup (0–2h), antes de cualquier scan en vivo:

- `docker pull` de **todas** las imágenes con **tags pineados** (`:stable`,
  **nunca** `:latest`).
- Pre-descarga de nuclei-templates a un **volumen persistente**
  (`nuclei -update-templates` una sola vez).
- Flag **`-duc`** (disable update check) en cada run de nuclei, para evitar el
  fallo de DNS dentro del contenedor en el primer arranque.
- **hexstrike (imagen Kali, varios GB) NO se pre-carga** si el tiempo aprieta.

## 8. Almacenamiento de evidencia

Screenshots y artefactos de cada hallazgo se escriben como **archivos** en el
volumen compartido `/data/scans/{scan_id}/{n}.png`, servidos por una **ruta
estática de FastAPI**. El campo `evidence` (jsonb del `Finding`) guarda la **URL
relativa**, no el binario:

- **NO** base64 en jsonb (infla la DB).
- **NO** MinIO (servicio extra inútil para el demo).

El export PDF embebe las imágenes desde esa misma ruta estática. (La forma del
campo `evidence` dentro del `Finding` pertenece a
[06-data-model](../06-data-model/spec.md); aquí solo se fija dónde y cómo se
persiste el binario.)

## 9. Stack completo de herramientas ("máximas herramientas")

| Herramienta | Rol | Docker |
|---|---|---|
| **Nuclei** | Templates CVE/misconfig (base + avanzado) | ✅ |
| **OWASP ZAP** | Baseline (pasivo) + full active scan | ✅ |
| **testssl.sh** | Auditoría TLS/SSL | ✅ |
| **WhatWeb / Wappalyzer** | Fingerprint de tecnologías | ✅ |
| **Nikto** | Web server scanner | ✅ |
| **katana** | Crawler (web + JS) | ✅ |
| **ffuf / gobuster** | Fuzzing de dirs/endpoints | ✅ |
| **sqlmap** | Inyección SQL (avanzado) | ✅ |
| **subfinder / dnsx** | Recon DNS/subdominios (pasivo) | ✅ |
| **Mozilla Observatory / security-headers** | Headers de seguridad | ✅ |
| **hexstrike-ai** | MCP, 150+ tools, orquestación autónoma. **Power-up OPCIONAL, recortado a CERO desde el inicio del plan** (no en la hora 18) — ver §10 | ⚠️ opcional |
| **garak** (NVIDIA) | Scanner de vulnerabilidades LLM (fallback agéntico) | ✅ |
| **promptfoo** | Red-team de prompts / evals (fallback agéntico) | ✅ |
| **Playwright** | Crawl agéntico + **puente de conversación** (maneja sesión/cookies/CSRF) + screenshots + PDF | ✅ |

> Las CLIs ligeras de esta tabla (nuclei, testssl, whatweb, nikto, katana, ffuf,
> sqlmap, subfinder, dnsx, security-headers/Observatory) viven preinstaladas en
> la imagen `scanners` y corren por `subprocess`. ZAP y hexstrike son los
> contenedores pesados que pasan por `run_tool()` (DooD). Playwright, garak y
> promptfoo pertenecen a la superficie agéntica — su orquestación está en
> [05-agent-team](../05-agent-team/spec.md); aquí solo aparecen en el
> inventario del stack y en la tabla de timeouts (§4.2).

## 10. hexstrike-ai: power-up opcional, recortado a CERO desde el inicio

hexstrike es un **server TCP:8888 + wrapper MCP sobre imagen Kali** con 150+
tools instaladas aparte (Docker cubre solo ~27) y orquestación LLM
no-determinista; su deploy es pesado/frágil y el "fallback ZAP full" tampoco es
trivial (40 min – 2 h). Ambos caminos del slot de 1 h originalmente reservado son
inviables, y si el equipo lo intenta "por si acaso" quema el tiempo de
deploy/pulido que realmente decide si hay demo.

Decisión: **hexstrike se recorta a CERO desde el inicio del plan, no en la hora
18.** El nivel "avanzado" se **narra** con la batería garantizada —**ZAP full
active + Nuclei fuzzing templates + sqlmap** sobre los params detectados,
time-boxed dentro del **budget global ~8 min** (el `<90s` es exclusivo del
**perfil demo**, que pre-hornea lo pesado — ver
[02-attack-levels](../02-attack-levels/spec.md) §7)—; el "avanzado" del demo es
narrativa, no orquestación real de hexstrike. Esto libera la hora 18–19 entera
para deploy + pulido.

Si aun así se intenta, queda detrás de:

- Un **feature-flag `ENABLE_HEXSTRIKE`**.
- Un **healthcheck al arrancar el worker**: si hexstrike no responde, el
  `owasp_agent` **no recibe esa tool** y opera con el fallback (ZAP full + Nuclei
  fuzzing + sqlmap). Nunca se invierte tiempo de deploy en él.

### 10.1 garak / promptfoo requieren un target HTTP/REST configurado

garak y promptfoo **no atacan una web sola**: exigen un target HTTP/REST
por-vendor (`uri` + `req_template_json_object` + `response_json_field` en garak;
`url` + body con `{{prompt}}` + `transformResponse` en promptfoo) que el crawl
no produce. Por eso el camino **base** del ataque agéntico es **Playwright
manejando la conversación**, que descubre endpoint, sesión y shape gratis;
garak/promptfoo quedan como **fallback opcional** solo para targets cuyo provider
HTTP sea derivable del crawl, con defaults acotados (`generations=1`, subset de
probes, grader forzado a Anthropic). **Nunca** corren sobre `.gob.mx`
automáticos (todos pasivos). El detalle de la superficie agéntica y del puente de
conversación vive en [05-agent-team](../05-agent-team/spec.md); aquí solo se
fija que estas dos tools son contenedorizadas, opt-in y con los timeouts de §4.2.

## 11. Resumen de invariantes del motor

- El worker vive **dentro** de la imagen `scanners`; CLIs ligeras por
  `subprocess`, pesadas por `run_tool()` (DooD, socket del host).
- **NO DinD.**
- `-v` con socket mount apunta al path del **HOST**.
- Todo scanner con `--network=owliver_egress`; postgres/redis en
  `owliver_internal` sin egress; IPs privadas y `169.254.169.254` bloqueadas.
- Timeout duro por tool + **budget global ~8 min** + watchdog que aborta la
  batería; fallo de una tool → Finding meta + continuar, nunca propagar.
- `max_jobs=1` (o 2); seed gob.mx pre-escaneado como fixtures, no encolado de
  golpe; `--memory`/`--cpus` en cada `docker run` pesado.
- Tags pineados (`:stable`), nuclei-templates pre-descargados a volumen, `-duc`
  en cada run.
- Evidencia como archivos en `/data/scans/{scan_id}/`; jsonb guarda URL
  relativa, no binario.
- hexstrike opt-out desde el inicio, detrás de `ENABLE_HEXSTRIKE` + healthcheck.
- Deploy en **VPS Linux** con socket y egress, **no** PaaS gestionado.
