# Owliver — Especificación de Producto

> **Owliver** 🦉 — El búho que vigila la seguridad de los sitios web. Pentesting
> automático orquestado por agentes IA, con un ángulo único: además del OWASP
> clásico, audita la **superficie agéntica** (chatbots, cajas de prompt, widgets
> LLM) buscando prompt-injection y jailbreaks.
>
> Documento de handoff para desarrollo. Contexto: **hackathon de 20 horas**.
> Fecha: 2026-06-20.

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
| 1 | **Postura de intrusividad** | Los 3 niveles = intrusividad creciente, sobre cualquier URL, con **gate de autorización obligatorio** (checkbox + términos) antes de encolar |
| 2 | **Motor de pentesting** | **Híbrido**: capa base garantizada (Nuclei + ZAP baseline + testssl.sh + WhatWeb) que SIEMPRE produce findings, + **hexstrike-ai** como power-up para nivel avanzado |
| 3 | **Runtime IA / orquestación** | **Agno** (Teams): un coordinador + 2 miembros. Modelos: **Sonnet** para subagentes, **Opus** para orquestador + redacción del reporte |
| 4 | **Stack de app + cola** | **Next.js** (UI) + **FastAPI** (API) + **Redis** (cola RQ/Arq + pub/sub) + **Postgres** + **worker Python/Agno** |
| 5 | **Motor LLM red-team** | **Híbrido**: detección propia (crawl + clasificación LLM + fingerprints de vendors) + **garak** / **promptfoo** para el ataque |
| 6 | **Score** | **Doble sub-score** 0–100 (🛡️ Web/OWASP y 🤖 Agéntico/LLM) → score global + **grado A–F** estilo Mozilla Observatory |
| 7 | **Ranking gov seed** | **México** (`.gob.mx`), ~30–50 dominios, auto-escaneados en nivel básico/pasivo en schedule |
| 8 | **Alcance 20h** | Núcleo + las 4 swing features (monitoreo+alertas, live view, PDF+share, hexstrike) — TODAS in-scope, con orden de recorte documentado |

---

## 3. ⚖️ Nota legal / ética (requisito, no opcional)

El pentesting **activo** (niveles intermedio/avanzado) contra sistemas sin
autorización es ilegal en casi cualquier jurisdicción. Mitigaciones obligatorias
del MVP:

1. **Gate de autorización**: antes de encolar un escaneo activo, checkbox
   obligatorio *"Declaro tener autorización para auditar este dominio"* +
   aceptación de términos. Se persiste `authorized=true` + timestamp + user en
   la tabla `scans` (registro de consentimiento).
2. **Ranking público gov = SOLO nivel básico/pasivo.** Los `.gob.mx` del
   leaderboard global se escanean **únicamente** con técnicas no intrusivas
   (headers, TLS, fingerprint, templates pasivos de Nuclei) — equivalente a lo
   que hacen públicamente Mozilla Observatory / SSL Labs / Shodan. Nunca se lanza
   un escaneo activo automático contra un sitio del Estado.
3. **Niveles activos (intermedio/avanzado)** solo se permiten sobre dominios que
   el usuario declara propios/autorizados.
4. **Rate-limiting** y `User-Agent` identificable (`Owliver-Scanner/1.0
   (+contacto)`) en todos los escaneos para minimizar impacto.

---

## 4. Definición precisa de los 3 niveles

Cada nivel define qué herramientas/intensidad usa **cada subagente**.

### Subagente OWASP (Web)

| Nivel | Técnicas | Herramientas |
|-------|----------|--------------|
| **Básico** (pasivo, no intrusivo) | Fingerprint, TLS, headers de seguridad, templates pasivos, recon DNS | WhatWeb/Wappalyzer, testssl.sh, security-headers/Observatory, Nuclei (`exposures`, `misconfiguration`, `ssl`, `tech`, `dns`), robots/sitemap, subfinder/dnsx (passive) |
| **Intermedio** (activo suave, rate-limited) | Spider + scan pasivo, CVEs, enum ligero, CORS/cookies | + ZAP **baseline** scan, Nuclei full (CVEs, default-logins low-risk), Nikto, katana (crawl), ffuf/gobuster (dir enum ligero), checks CORS/cookie/clickjacking |
| **Avanzado** (activo / explotación, requiere autorización) | Active scan, inyección, orquestación autónoma | + ZAP **full active** scan, sqlmap (sobre params detectados), Nuclei fuzzing templates, **hexstrike-ai** (el agente decide herramientas: nmap, sqlmap, ffuf, etc.), pruebas de auth |

### Subagente Superficie Agéntica (LLM)

**Detección (en TODOS los niveles):** crawl con katana/Playwright → captura DOM +
tráfico de red → clasificador LLM + fingerprints de vendors (Intercom, Drift,
Zendesk, Tidio, LivePerson, Crisp, endpoints `/chat` custom, "ask AI" search,
llamadas a SDK de OpenAI/Anthropic en el JS) → **inventario de superficie
agéntica** (tabla `agentic_surface`).

| Nivel | Testing |
|-------|---------|
| **Básico** | Solo detección + clasificación. Reporta presencia, vendor y modelo inferido. **Sin payloads.** |
| **Intermedio** | Sondas acotadas (1–2 turnos) vía **promptfoo**: canary, *"ignore previous instructions"*, system-prompt leak probe, jailbreak simple. LLM-juez evalúa si fue comprometido. |
| **Avanzado** | Batería completa: **garak** (probes `promptinject`, `dan`, `leakreplay`, `encoding`, `xss`…) + **promptfoo red-team** multi-turn. Pruebas de exfiltración/PII, abuso de herramientas, inyección indirecta. |

Findings agénticos se mapean a **OWASP Top 10 for LLM Applications** (LLM01
Prompt Injection, LLM02 Insecure Output Handling, LLM06 Sensitive Info
Disclosure, etc.).

---

## 5. Arquitectura del sistema

```
┌─────────────┐     HTTPS     ┌──────────────┐
│  Next.js    │ ────────────► │   FastAPI    │
│  (frontend) │ ◄──── SSE ──── │   (API)      │
└─────────────┘   live view   └──────┬───────┘
                                      │ enqueue (RQ/Arq)
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
              │ merge+score+    │              │ tools: scanners  │  │ (Sonnet)     │
              │ reporte         │              │ Docker + hexstrike│  │ crawl+garak  │
              └────────┬────────┘              └──────────────────┘  └──────────────┘
                       │ findings + scores
                       ▼
              ┌─────────────────┐        Herramientas en contenedores Docker:
              │   Postgres      │        nuclei · zap · testssl · whatweb · nikto
              │  (findings,     │        katana · ffuf · sqlmap · garak · promptfoo
              │   scans, sites) │        hexstrike-ai (MCP)
              └─────────────────┘
```

**Servicios (docker-compose):** `web` (Next.js), `api` (FastAPI), `worker`
(Python/Agno), `redis`, `postgres`, `scanners` (imagen con las CLIs de pentest) o
contenedores individuales, `hexstrike` (MCP server), `scheduler` (cron de
re-escaneos).

---

## 6. Diseño del agente (Agno Team)

```python
# Pseudocódigo de referencia
class Finding(BaseModel):           # salida estructurada estándar (sección 8)
    source: Literal["owasp", "agentic"]
    tool: str
    category: str                   # A01..A10 o LLM01..LLM10
    title: str
    severity: Literal["critical","high","medium","low","info"]
    cvss: float | None
    confidence: Literal["alta","media","baja"]
    description: str
    evidence: dict                  # payload, req/resp snippet, screenshot ref
    affected_url: str | None
    endpoint: str | None
    param: str | None
    impact: str                     # lenguaje de negocio
    remediation: str
    references: list[str]

owasp_agent = Agent(
    name="OWASP Scanner", model=Claude("sonnet"),
    tools=[run_nuclei, run_zap, run_testssl, run_whatweb, run_nikto,
           run_katana, run_ffuf, run_sqlmap, hexstrike_mcp],
    instructions="Ejecuta el pentest OWASP al nivel indicado. "
                 "Devuelve SOLO una lista de Finding válidos.",
    response_model=list[Finding])

agentic_agent = Agent(
    name="Agentic Surface Auditor", model=Claude("sonnet"),
    tools=[crawl_site, classify_dom_llm, fingerprint_vendors,
           run_promptfoo, run_garak],
    instructions="Detecta chatbots/inputs de prompt y pruébalos según el nivel. "
                 "Mapea a OWASP-LLM Top 10. Devuelve Finding[] + inventario.",
    response_model=AgenticResult)

orchestrator = Team(
    mode="coordinate", model=Claude("opus"),
    members=[owasp_agent, agentic_agent],
    instructions="Coordina ambos subagentes EN PARALELO sobre {url} a nivel "
                 "{level}. Deduplica findings, calcula sub-scores y grado, "
                 "y redacta el resumen ejecutivo en lenguaje llano.")
```

**Flujo del worker:**
1. Recoge job de Redis → marca `scan.status=running`, publica evento.
2. Lanza `orchestrator.run(url, level)` — los 2 subagentes corren en paralelo.
3. Cada herramienta corre en su contenedor Docker; su salida cruda se parsea a
   `Finding[]`. Cada paso publica un evento a Redis pub/sub (live view).
4. Orquestador deduplica, calcula `web_score`, `agentic_score`,
   `overall_score`, `overall_grade`, y genera el **resumen ejecutivo** (Opus).
5. Persiste `scans` + `findings` + `agentic_surface` en Postgres → `status=done`.

---

## 7. Modelo de datos (Postgres)

```sql
users(id, email, name, created_at)

sites(id, url, hostname, is_gov bool, country, owner_user_id NULL,
      latest_scan_id NULL, created_at)

scans(id, site_id, level ENUM(basico,intermedio,avanzado),
      status ENUM(queued,running,done,failed),
      requested_by, authorized bool, authorized_at,
      web_score int, agentic_score int NULL, overall_score int,
      overall_grade char(1), started_at, finished_at, error)

findings(id, scan_id, site_id, source, tool, category, title,
         severity, cvss, confidence, description, evidence jsonb,
         affected_url, endpoint, param, impact, remediation,
         references jsonb, status ENUM(open,fixed,accepted),
         first_seen, last_seen)

agentic_surface(id, scan_id, site_id, type, vendor, location_url,
                inferred_model, detected_at)

watchlist(id, user_id, site_id, monitor bool, created_at)   -- watchlist privada
                                                            -- global = sites.is_gov

alerts(id, user_id, site_id, scan_id, type, message, channel, sent_at)

scan_events(id, scan_id, ts, level, agent, message)  -- opcional persistir live view
public_reports(token, scan_id, created_at, expires_at)  -- links compartibles
```

---

## 8. Formato estándar de findings

Ver `Finding` en §6. Campos clave y su propósito:

- `source` — separa Web vs Agéntico (alimenta los dos sub-scores).
- `category` — código OWASP `A01–A10` **o** OWASP-LLM `LLM01–LLM10`.
- `severity` + `cvss` — severidad para el score.
- `confidence` (alta/media/baja) — **crítico para falsos positivos**; el
  orquestador (Opus) puede hacer triage y bajar confianza a hallazgos dudosos.
- `evidence` (jsonb) — payload enviado, snippet request/response, ref a
  screenshot. Es lo que da **valor técnico**.
- `impact` + `remediation` — lenguaje de negocio + pasos accionables (lo que da
  **valor "fácil de entender"**).
- `first_seen` / `last_seen` + `status` — habilitan el **monitoreo en el tiempo**
  (detectar findings nuevos/resueltos entre escaneos).

---

## 9. Modelo de scoring

```
Peso por severidad:  critical=40  high=20  medium=8  low=3  info=0
Factor de confianza: alta=1.0  media=0.7  baja=0.4

penalty(sub) = Σ (peso_severidad × factor_confianza)   sobre findings del source
sub_score    = max(0, 100 − min(100, penalty))

web_score     = score sobre findings source="owasp"
agentic_score = score sobre findings source="agentic"
                → N/A si NO se detectó superficie agéntica (no penaliza)

overall_score = round(0.6 × web_score + 0.4 × agentic_score)
                (si agentic = N/A → overall = web_score)

Grado:  A ≥90 · B ≥80 · C ≥70 · D ≥60 · F <60
```

**Por qué el doble score importa:** un `.gob.mx` puede salir **B en Web** pero
**F en Agéntico** (su chatbot filtra el system-prompt) → narrativa visual potente
y única en el demo.

---

## 10. Ranking público + watchlists

- **Ranking global (`/`):** leaderboard de `sites WHERE is_gov=true`, ordenado por
  `overall_score` asc (peores primero) o por grado. Filtrable por país (MX).
- **Seed:** archivo `seed/gob_mx.txt` con ~30–50 dominios `.gob.mx` (gob.mx, SAT,
  IMSS, INE, IMPI, Salud, Banxico, gobiernos estatales…). Un job de arranque los
  inserta como `sites(is_gov=true)` y encola escaneos **nivel básico** para cada
  uno → leaderboard poblado desde el minuto 0 del demo.
- **Watchlist privada:** un usuario agrega su(s) dominio(s); puede correr niveles
  activos (con autorización) y activar `monitor=true` para re-escaneos periódicos.
- Cualquier URL pública/gov que un usuario envíe entra también al ranking global.

---

## 11. Reporte ("Owliver te explica")

Reporte interactivo in-app, de **dos capas**:

**Capa 1 — Ejecutiva (lenguaje llano, generada por Opus):**
- Grado grande A–F + los dos sub-scores (gauges 🛡️ / 🤖).
- Párrafo "Owliver te explica" — qué encontramos y por qué importa, sin jerga.
- Top 3 riesgos priorizados con su impacto de negocio.
- Inventario de superficie agéntica detectada (qué chatbots/IA tiene el sitio).

**Capa 2 — Técnica (acordeón por finding):**
- Cada finding: severidad, categoría OWASP/LLM, `evidence` (payload + req/resp +
  screenshot), `impact`, `remediation` paso a paso, `references` (CWE/OWASP),
  `confidence`.
- Filtros por severidad / source / categoría.
- **Tendencia histórica** (si hay escaneos previos): cómo cambió el grado y qué
  findings son nuevos/resueltos.

**Entrega:** página in-app (núcleo) + **export PDF** (Playwright print-to-PDF o
WeasyPrint) + **link público compartible** (`/r/[token]`, tabla `public_reports`).

---

## 12. Features swing (todas in-scope) + defaults

1. **Monitoreo recurrente + alertas:** `scheduler` (APScheduler / rq-scheduler)
   re-encola escaneos de `watchlist.monitor=true` (y del seed gov) en cron.
   Alertas vía **Resend** (email) y/o **Slack webhook** cuando baja el grado o
   aparece un finding `critical`. Compara `findings.first_seen` para detectar
   nuevos.
2. **Vista en vivo del pentest:** worker publica eventos a Redis pub/sub →
   FastAPI los expone por **SSE** (`GET /scans/{id}/stream`) → Next.js renderiza
   los pasos del agente (subagentes activos, herramienta corriendo, findings
   apareciendo). Alto impacto en demo.
3. **Export PDF + link público:** §11.
4. **hexstrike-ai (power-up avanzado):** servidor MCP integrado como tool del
   subagente OWASP, solo en nivel avanzado. **Time-boxed** (ver §15). Fallback si
   el deploy falla: ZAP full active + Nuclei fuzzing.

**Auth (default):** JWT + magic-link por email (o Clerk si se quiere lo más
rápido). Multi-tenant vía `owner_user_id` / `watchlist.user_id`.

---

## 13. Stack completo de herramientas ("máximas herramientas")

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
| **hexstrike-ai** | MCP, 150+ tools, orquestación autónoma (avanzado) | ✅ |
| **garak** (NVIDIA) | Scanner de vulnerabilidades LLM (avanzado) | ✅ |
| **promptfoo** | Red-team de prompts / evals (intermedio+) | ✅ |
| **Playwright** | Crawl agéntico + screenshots + PDF | ✅ |

---

## 14. API (FastAPI) — endpoints

```
POST   /auth/magic-link            envía magic link
POST   /scans            {url, level, authorized}  → encola, devuelve scan_id
GET    /scans/{id}                 estado + scores
GET    /scans/{id}/findings        findings del escaneo
GET    /scans/{id}/stream          SSE live view
GET    /scans/{id}/report.pdf      PDF
POST   /scans/{id}/share           crea link público → token
GET    /sites/{id}                 último escaneo + histórico
GET    /ranking?country=mx         leaderboard global gov
GET    /watchlist                  (auth) sitios del usuario
POST   /watchlist        {url, monitor}
GET    /r/{token}                  reporte público
```

---

## 15. Plan de 20 horas (equipo ~3–4)

| Horas | Entregable |
|---|---|
| **0–2** | Scaffolding: repo, docker-compose (postgres, redis, api, worker, web), migraciones, auth stub, seed `gob_mx.txt` |
| **2–5** | Capa base de scanners en el worker (Nuclei + testssl + WhatWeb + ZAP baseline) → `Finding[]`. `POST /scans` + cola + pickup. **Nivel básico end-to-end con findings reales** |
| **5–8** | Agno Team (orquestador + 2 miembros), `Finding` Pydantic, scoring, persistencia. OWASP agent niveles intermedio/avanzado |
| **8–11** | Subagente agéntico: detección (crawl + clasificador + fingerprints) + runners promptfoo/garak → findings + agentic_score |
| **11–14** | Frontend: leaderboard ranking, form de scan, **reporte** (doble score + resumen ejecutivo Opus + acordeón) |
| **14–16** | Live view (Redis pub/sub → SSE), correr seed `.gob.mx` en básico → poblar ranking |
| **16–18** | Cron monitoreo + alertas (Resend/Slack), watchlist; export PDF + link público |
| **18–19** | Integración **hexstrike-ai** (avanzado), time-boxed; fallback ZAP full si falla |
| **19–20** | Pulido, seed data de demo, guion de pitch, deploy |

**Orden de recorte si el tiempo aprieta** (cortar en este orden):
`hexstrike-ai` → `PDF/share` → `live view` → `monitoreo/alertas`.
**Nunca se corta:** núcleo (form→scan→findings→reporte) + ranking gov + doble score.

---

## 16. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Deploy de hexstrike-ai pesado/frágil | Es power-up, no base. Time-box + fallback ZAP/Nuclei |
| Escaneos activos bloqueados por WAF/rate-limit | Rate-limiting, UA identificable, nivel básico siempre como respaldo de findings |
| Legal (sitios gov) | Ranking gov = solo pasivo; gate de autorización para activos (§3) |
| Costo/latencia LLM | Sonnet en subagentes, Opus solo en síntesis; cachear; correr tools en paralelo |
| garak/promptfoo tardan mucho | Time-box de probes; set reducido en intermedio |
| Falsos positivos | Campo `confidence` + triage del orquestador (Opus) |

---

## 17. Criterios de demo / pitch

1. Abrir `/` → leaderboard de `.gob.mx` ya poblado, con grados A–F y el contraste
   Web vs Agéntico visible.
2. Ingresar una URL propia + nivel avanzado → **live view** mostrando a Owliver
   trabajando (2 subagentes, herramientas corriendo, findings apareciendo).
3. Abrir el **reporte**: grado grande, "Owliver te explica", y un finding
   agéntico estrella (ej. system-prompt leak de un chatbot) con su evidencia.
4. Mostrar export PDF + link público compartible.
5. Cierre: "Owliver vigila la seguridad del Estado y de tu IA — lo que nadie más
   está midiendo."
```
```
