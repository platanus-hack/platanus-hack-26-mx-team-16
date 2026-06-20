---
feature: frontend
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §10, §11, §12, §14, §15, §17; owliver-frontend.md §F1–§F16; spec-gaps.md §5
---

# Owliver — Frontend (Next.js) — superficies y sistema

> Esta subspec define **todo el frontend de Owliver** (Next.js 15 / App Router): las reglas de arquitectura (BFF, RSC, SSE), la dirección visual "claro de día, SOC de noche", el mapa de rutas, y cada superficie — el leaderboard gov "Hall of Shame" (`/`), el form de escaneo con gate de atestación, el **Live Pentest Theater** (`/scans/[id]`, el centerpiece cinematográfico en modo SOC), el reporte interactivo "Owliver te explica", el reporte público redactado `/r/[token]`, sitios/histórico, las 4 pantallas de magic-link, y watchlist + monitoreo. Incluye estados transversales, a11y, responsive e i18n, el sistema de componentes shadcn+custom, tres features wow opcionales, el mapeo al plan de 20h con su orden de recorte y el checklist de pantallas. Es la **superficie**: los contratos subyacentes viven en las subspecs hermanas (se cruzan, no se duplican). El brief visual de alta fidelidad está en [design-prompt.md](../../design-prompt.md) ("claro de día, SOC de noche").

## Decisiones de diseño (cerradas con el equipo)

| # | Decisión | Elección |
|---|----------|----------|
| FE-1 | **Dirección visual** | **Híbrido claro + SOC**: app clara y confiable (ángulo gov-audit, "The Inspection Bench") **+ live-view en modo oscuro tipo sala de operaciones** (el pentest theater es el momento cinematográfico) |
| FE-2 | **Centerpiece del wow** | **Live Pentest Theater** (§F6): agentes + herramientas + findings apareciendo en vivo. Es donde se concentra el detalle y la ambición. El reporte es el *payoff* |
| FE-3 | **Tono del ranking gov** | **Hall of Shame**: peores primero, rojo, provocador, máximo potencial viral. Marco "datos públicos no intrusivos" para defendibilidad legal — ver [01-legal-ethics](../01-legal-ethics/spec.md) |
| FE-4 | **Alcance del doc** | Spec consolidado **+ 3 features wow opcionales** (§F14), marcadas como recortables |

> ⚠️ **Nota de identidad.** `PRODUCT.md` / `DESIGN.md` y el frontend actual del repo (`dashboard`, `members`, `roles`…) son del **boilerplate Doxiq**, no de Owliver. Owliver es un producto nuevo sobre ese boilerplate: reusamos la **infraestructura** (route-groups, BFF `/api/auth/*`, `serverHttp`/`authHttp`, tokens base de Tailwind v4) pero **Owliver tiene su propia piel** (§F2). En particular, `/` (raíz) hoy está ocupado por la app autenticada `(protected)`: casi todo lo público de Owliver se construye desde cero en un nuevo route-group `(public)`.

---

## §F1 · Stack y reglas de arquitectura frontend

- **Next.js 15 (App Router) + React 19 + TypeScript**, Tailwind CSS v4 (oklch, `@theme inline`), **shadcn + Base UI**. Charts con **recharts** (^3.6.0, ya presente). Toasts con **sonner** (hay que añadirlo). **Accordion** se añade con `npx shadcn add accordion` (el repo solo trae `collapsible`).
- **Cliente → backend SIEMPRE vía BFF** (regla del repo): los componentes `"use client"` hacen `fetch("/api/…")` same-origin; las `route.ts` server-side reenvían con `serverHttp` y manejan cookies HttpOnly + `X-Api-Key`. Nunca `fetch` directo a `Settings.apiBaseUrl` desde el browser.
- **Route-groups:** `(public)` para todo lo anónimo (leaderboard, scan básico, reporte, `/r/[token]`, magic-link) y `(protected)` para watchlist/monitoreo y scans activos. Decisión de superficie en §F10 / [11-auth-magic-link](../11-auth-magic-link/spec.md). El `(public)` lleva **layout propio** (logo Owliver + CTA "Escanear mi sitio", sin sidebar).
- **SSE (live-view):** `EventSource` con `withCredentials: true` (no permite headers custom → auth por cookie). **Replay-then-tail** sobre `Last-Event-ID` / `?since_seq=`. Compresión desactivada en la ruta. El contrato completo del stream vive en [10-realtime-live-view](../10-realtime-live-view/spec.md).
- **Server Components por defecto**, Client Components solo donde hay estado/SSE (theater, form, filtros, gauges animados). `/r/[token]` es **server component** sin login.

---

## §F2 · Dirección visual — "claro de día, SOC de noche"

Dos modos que conviven, no dos temas que el usuario alterna. El brief de alta fidelidad con copy literal por pantalla está en [design-prompt.md](../../design-prompt.md). North star: *"La mesa de inspección"* (the inspection bench) — rigor técnico presentado con claridad. Personalidad: **afilada, confiable, cercana**. Anti-referencias a evitar: plantillas SaaS genéricas, el look "app de IA" trendy y morado, el desorden de enterprise legacy.

**A) App shell — claro, institucional, confiable (default).**
La mayor parte de la app (leaderboard, form, reporte, auth) vive aquí. Hereda los tokens cool-gray + teal del repo, pero con **acento ámbar/oro = "ojos del búho"** para Owliver.

```
--ow-primary:   oklch(0.59 0.095 180.54)   /* teal — confianza, marca */
--ow-ink:       oklch(0.222 0.029 253.225)  /* texto */
--ow-surface:   oklch(0.984 0.002 252.121)  /* fondo app */
--ow-card:      oklch(1 0 0)
--ow-accent:    oklch(0.78 0.15 75)          /* ámbar — ojos del búho, CTAs vivos */
```

**B) Live-view (theater) — oscuro, "war room", monospace.**
El momento estrella entra en modo SOC: near-black, telemetría, **Geist Mono**, scanlines sutiles, neón funcional (no decorativo).

```
--soc-bg:       oklch(0.16 0.02 250)         /* casi negro azulado */
--soc-grid:     oklch(0.24 0.02 250)         /* líneas/scanlines */
--soc-live:     oklch(0.80 0.13 195)         /* cian — actividad en curso */
--soc-tool:     oklch(0.80 0.14 75)          /* ámbar — tool corriendo */
--soc-hit:      oklch(0.64 0.22 25)          /* rojo — finding crítico (pulse) */
```

**Escala de grados A–F (única fuente de color para chips/gauges/filas):**

| Grado | Token | Uso |
|---|---|---|
| **A** ≥90 | `oklch(0.72 0.16 150)` verde | seguro |
| **B** ≥80 | `oklch(0.75 0.15 130)` verde-lima | |
| **C** ≥70 | `oklch(0.80 0.14 90)` ámbar | cap de cobertura parcial — ver [07-scoring](../07-scoring/spec.md) |
| **D** ≥60 | `oklch(0.72 0.16 55)` naranja | |
| **E** ≥40 | `oklch(0.66 0.19 35)` naranja-rojo | zona poblada del leaderboard gov |
| **F** <40 | `oklch(0.58 0.22 25)` rojo | "hall of shame" |

- **Tipografía:** **Figtree** (UI) + **Geist Mono** (telemetría, payloads, evidencia, scores). Grados y scores siempre en mono → lectura "instrumento".
- **Radio** base 0.75rem (~12px), near-flat (hairline rings + whisper shadows) en claro; glow funcional en SOC.
- **Mascota 🦉:** el búho aparece como indicador de actividad (parpadea/gira la cabeza mientras escanea), no como clipart. Estados: dormido (idle), vigilando (running), encontró algo (alerta —ojos ámbar encendidos—).
- **Motion:** entradas de findings con `fade+slide` corto; gauges animan de 0 al valor; grados hacen "count-up"; críticos laten una vez en rojo. Respetar `prefers-reduced-motion`. Contraste AA en ambos modos; foco visible.

---

## §F3 · Mapa de superficies (rutas)

| Ruta | Group | Auth | Propósito | Consume |
|---|---|---|---|---|
| `/` | public | anon | **Hall of Shame** leaderboard gov (§F4) | `GET /ranking?country=mx` |
| `/scan` (o modal en `/`) | public | anon (básico) | Form de escaneo + gate (§F5) | `POST /scans` |
| `/scans/[id]` | public/priv | según visibility | **Live Pentest Theater** (§F6) | `GET /scans/{id}` · `GET /scans/{id}/stream` |
| `/scans/[id]/report` | public/priv | según visibility | Reporte "Owliver te explica" (§F7) | `GET /scans/{id}` · `/findings` |
| `/sites/[id]` | public | anon | Histórico del sitio (§F9) | `GET /sites/{id}` |
| `/r/[token]` | public | token | Reporte público redactado (§F8) | `GET /r/{token}` |
| `/login` (pedir email) | public | anon | Magic-link p.1 (§F10) | `POST /auth/magic-link` |
| `/login/check-email` | public | anon | Magic-link p.2 | — |
| `/auth/callback` | public | token | Magic-link p.3 (verify) | `GET /auth/callback?token=` |
| `/watchlist` | protected | sesión | Watchlist + monitoreo (§F11) | `GET/POST/DELETE /watchlist` · `PATCH /watchlist/{id}` (toggle `monitor`) |

Acciones transversales: `POST /scans/{id}/share` (genera `/r/{token}`), `GET /scans/{id}/report.pdf` (export), `POST /scans/{id}/cancel` (mata scan). Contrato completo de endpoints en [12-api](../12-api/spec.md).

**Nav global.** Header público: logo Owliver + Leaderboard + Escanear + (con sesión) Watchlist/avatar. Sirve a las dos audiencias (anónima viral / cuenta vigilante) sin un sidebar pesado.

---

## §F4 · Hall of Shame — leaderboard gov (`/`) 🔴

**Propósito.** La portada. "El Estado bajo la lupa": ranking de `.gob.mx` **peores primero**, poblado desde el segundo 0 (fixtures — ver [07-scoring](../07-scoring/spec.md) y spec.md §10/§15). Es la primera impresión y el gancho viral. Renderizada como **RSC** (`GET /ranking?country=mx`).

**Datos.** `GET /ranking?country=mx` (cursor-paginado). Orden **autoritativo**: `(overall_grade ASC, penalty_raw DESC)` — la fila muestra `penalty_raw` (o el conteo ponderado) para que el contraste entre sitios en **F** sea visible. El criterio de desempate lo define [07-scoring](../07-scoring/spec.md). **Nota:** el `penalty_raw` persistido refleja **solo el sub-score Web**; la penalización agéntica se rastrea aparte vía `agentic_status` — no presentarlo en la UI como una penalización combinada.

**Layout / componentes.**
- **Hero provocador:** titular grande (**"¿Qué tan segura es la IA del gobierno?"**), subcopy con contador de sitios auditados + cuántos en **F** (ej. *"128 sitios auditados · 41 reprobados (grado F)"*). Marco de defendibilidad, discreto: micro-copy *"Datos 100% pasivos y públicos — equivalente a Mozilla Observatory / SSL Labs. No intrusivo."* (ver [01-legal-ethics](../01-legal-ethics/spec.md)).
- **CTA primario** (ámbar): **"Audita cualquier URL →"** → abre el form (§F5).
- **Tabla / cards ranking** (reusa `table.tsx`; cada fila):
  - Posición + **grado grande A–F** (mono, color de escala §F2).
  - Nombre de la dependencia + hostname (ej. *Servicio de Administración Tributaria · sat.gob.mx*) + favicon.
  - **Doble mini-gauge / chips:** 🛡️ Web vs 🤖 Agéntico — el contraste es el diferenciador. Una fila estrella tipo *SAT "C web / **F** agéntico"*.
  - Badge **"IA detectada, sin auditar"** cuando `agentic_status=detected_not_tested` — nunca se muestra como "sin riesgo". (estados de `agentic_status` y reglas en [07-scoring](../07-scoring/spec.md)).
  - Badge **"cobertura parcial"** cuando aplica el cap-C.
  - `penalty_raw` visible (desempate) + tendencia (▲▼ vs scan previo, si hay) + fecha del último scan.
  - Click en la fila → `/sites/{id}`.
- **Filtros:** por grado, por `source` peor (web/agéntico), por país (MX). Cursor "cargar más".

**Estados.** Skeleton de filas (no spinner); empty solo teórico (fixtures garantizan poblado); fila `failed`/`partial` con su etiqueta, nunca grado A inflado. Estados loading/empty/error definidos explícitamente.

**Wow.** Al cargar, los grados hacen **count-up** y las filas en **F** laten en rojo una vez. Hover de una fila revela el "por qué" (top finding). Orden "peores primero" hace que lo rojo domine la pantalla → impacto inmediato.

---

## §F5 · Form de escaneo + gate de atestación

**Propósito.** Entrada universal: URL + nivel. Es el control legal convertido en UI — el **invariante de atestación** lo posee [01-legal-ethics](../01-legal-ethics/spec.md).

**Componentes.**
- **Input URL** grande con validación + normalización en cliente: usar `new URL()`, prefijar `https://` si falta, extraer y mostrar el `host` detectado (preview *"Vas a escanear: sat.gob.mx"*). **Rechazar** IPs privadas / localhost / hostnames sin punto.
- **Selector de nivel** (3 cards radio): **Básico** (*pasivo, no intrusivo, anónimo, sin permisos* — default) · **Intermedio** (*activo suave, rate-limited*) · **Avanzado** (*explotación, requiere autorización*). Cada card explica en lenguaje llano qué hace y su intrusividad.
- **Gate condicional de atestación** (aparece **solo** si el nivel es activo — intermedio/avanzado — y queda **oculto** en básico; en básico `authorized=false`):
  - Advertencia prominente: *"Vas a lanzar pruebas intrusivas contra **{host}**; hacerlo sin autorización es ilegal."*
  - **Checkbox obligatorio**: *"Declaro tener autorización para auditar este dominio."* + link "Ver términos" (Dialog). Sin marcar el checkbox, el submit queda **deshabilitado**.
  - **Advertencia reforzada (copy en rojo)** si el host es `.gob.mx` u otro sensible (*"Sitio del Estado: el escaneo activo es de tu entera responsabilidad legal; los escaneos automáticos del ranking público solo corren en modo pasivo."*) — pero **se puede proceder** bajo atestación: la atestación es el control, **no** un bloqueo por dominio (ver [01-legal-ethics](../01-legal-ethics/spec.md) §2.4). El resultado de un activo gov queda **privado** (fuera del ranking público).
- **Nivel activo** requiere sesión → si no hay, redirige a magic-link guardando el destino pendiente (§F10).

**Flujo.** submit → loading en el botón → `POST /scans` → recibe `scan_id` → **redirect a `/scans/[id]`** (theater). Idempotencia: si ya hay un scan running, el backend devuelve el `scan_id` existente y se redirige igual (no crea duplicado — ver [12-api](../12-api/spec.md)).

**Estados.** Validación inline; loading en el botón; error 422 (atestación faltante / validación) y 403 (backend) con copy claro (403 → toast); doble-submit deshabilitado.

---

## §F6 · ★ Live Pentest Theater (`/scans/[id]`) — EL CENTERPIECE 🌑

> El momento cinematográfico. Aquí Owliver **deja de ser un formulario y se convierte en un búho cazando en vivo.** Modo **SOC oscuro** (§F2-B). Es la pantalla que más debe impresionar.

**Propósito.** Renderizar el pentest en tiempo real: subagentes activos, herramientas corriendo, findings apareciendo. Alto impacto en demo (spec.md §17).

**Datos.**
- Estado inicial: `GET /scans/{id}` (status, progress, current_phase, tools_status, scores parciales).
- Stream: `GET /scans/{id}/stream` (SSE) con **replay-then-tail** — `EventSource(url, {withCredentials:true})`, cursor `Last-Event-ID`/`since_seq`.
- Eventos tipados: `agent_status | tool_start | tool_end | finding | phase | score | done | error`. `seq` monótono = orden + idempotencia de cliente (descartar `seq <= lastSeq`). El contrato del stream y el detalle de cada evento están en [10-realtime-live-view](../10-realtime-live-view/spec.md).

**Layout (war room).**
- **Header:** host objetivo + nivel + grado-en-construcción (placeholder hasta `done`) + **barra de progreso** (0–100, `current_phase` legible — ej. "Detectando tecnologías…", "Sondeando chatbot…") + timer (con el **timeout demo <90s** visible como tranquilizador).
- **Dos carriles de agente** lado a lado, cada uno con su 🦉 (el diseño de equipo Opus+2 Sonnet vive en [05-agent-team](../05-agent-team/spec.md)):
  - 🛡️ **OWASP Scanner (Sonnet)** — chips de tools (nuclei, zap, testssl, nikto, sqlmap…) que **se encienden** (`tool_start` → ámbar/pulse) y **se apagan** (`tool_end` → verde ok / rojo fail/timeout, alimentando `coverage`).
  - 🤖 **Agentic Surface Auditor (Sonnet)** — fases: detección → inventario → sondas. Muestra el chatbot detectado (vendor, modelo inferido) y cada probe lanzado.
- **Feed de findings en vivo** (centro/derecha): cada `finding` entra con `fade+slide`, chip de severidad (color §F2) + categoría OWASP A01–A10 / LLM01–LLM10 + título. Los **críticos** laten en rojo (`--soc-hit`).
- **Telemetría inferior:** scores parciales (🛡️/🤖) actualizándose con eventos `score`; log monospace scrolleable (estilo terminal).
- **Cierre:** evento `done` → botón grande **"Ver reporte completo →"** → `/scans/[id]/report`.

**Interacciones / control.**
- **Cancelar** (`POST /scans/{id}/cancel`) → evento terminal `done` con `{outcome:'cancelled'}`; UI muestra "escaneo cancelado".
- **Reconexión / recarga:** al recargar, el **replay** desde Postgres repinta TODO el progreso (no queda vacío) — esto se demuestra en vivo (spec.md §17 paso 2). Diséñalo asumiendo replay.
- Heartbeat cada ~20s mantiene viva la conexión.

**Estados.**
- `queued` → "en cola" con 🦉 dormido.
- `running` → theater activo.
- `partial` → banner "cobertura parcial" (algún scanner falló — ver [07-scoring](../07-scoring/spec.md)).
- `failed`/`error` → estado de error con `error` + `tools_status` para depurar.
- `cancelled` → estado terminal limpio.
- **Sin auth en scan privado** → 404 (no confirmar existencia — ver [12-api](../12-api/spec.md)).

**Wow.**
- Es literalmente ver a la IA atacar. Los chips encendiéndose + findings cayendo + el rojo del crítico = tensión.
- **Demo-level:** perfil rápido (Nuclei subset + testssl + 1 probe al bot propio) con timeout duro <90s; lo pesado (ZAP full/garak) se muestra desde resultados pre-horneados. El theater **nunca** se queda colgado en el pitch.
- Plan B: si el SSE falla (checkpoint H16 rojo) → **video de respaldo de 90s** (spec.md §17). El front debe degradar a un `<video>` sin romper el resto del guion.

---

## §F7 · Reporte "Owliver te explica" (el payoff)

Reporte interactivo in-app de **dos capas**. Vuelve al **modo claro** (confianza/lectura). El contenido y la estructura de datos del reporte (síntesis Opus, `evidence`, `dedupe_key`, histórico) los posee [09-reporting](../09-reporting/spec.md); aquí se especifica su **render**.

**Capa 1 — Ejecutiva (lenguaje llano, generada por Opus).**
- **Grado grande A–F** arriba (count-up) + **dos gauges semicirculares** 🛡️ Web / 🤖 Agéntico (`RadialBarChart` recharts, `endAngle=180`, Label central con score + grado). El cálculo de los scores lo posee [07-scoring](../07-scoring/spec.md).
- Párrafo **"Owliver te explica"** — qué encontramos y por qué importa, sin jerga, tono cercano.
- **Top 3 riesgos** priorizados con su impacto de negocio.
- **Inventario de superficie agéntica** detectada (qué chatbots/IA tiene el sitio, vendor, modelo inferido o "modelo no expuesto").
- **Badges de estado:** "IA detectada, sin auditar" (`detected_not_tested`) y "cobertura parcial" (cap-C).

**Capa 2 — Técnica (acordeón por finding).**
- **Accordion** (shadcn): header = chip severidad + categoría OWASP/LLM + título; body = `evidence` (payload + req/resp + screenshot), `impact`, `remediation` paso a paso, `references` (CWE/OWASP), `confidence`.
- **El finding agéntico estrella:** system-prompt leak del bot con su **canary** (token secreto filtrado) como evidencia incontestable — `evidence = {payload, respuesta_cruda, token_filtrado}` en bloque monospace destacado, resaltado visualmente.
- **Filtros:** por severidad / source / categoría.
- **Findings `info`** (peso 0): conteo aparte, no afectan score; incluye los meta "tool X no completó" (cobertura).
- **Tendencia histórica** (si hay scans previos): cómo cambió el grado + findings nuevos/resueltos (vía `dedupe_key` + `first_seen`/`last_seen` a nivel site — ver [09-reporting](../09-reporting/spec.md)).

**Acciones.** Export **PDF** (`/scans/{id}/report.pdf`) · **Compartir** → `POST /scans/{id}/share` genera `/r/{token}` (toast con el link, TTL 7 días).

**Estados.** Screenshots servidos desde ruta estática FastAPI (`/data/scans/{id}/{n}.png`); placeholder si falta. Toasts (sonner) para share/PDF/errores 403/410.

---

## §F8 · Reporte público `/r/[token]` (redactado)

**Propósito.** Link compartible sin login — **server component**. El gancho viral del hall of shame, pero seguro: sin definirlo bien, el link puede **filtrar exploits reales**.

**Funcionalidad.**
- Renderiza la **capa ejecutiva completa** + findings técnicos **con los payloads de explotación redactados/ocultos** por defecto: muestra tipo, categoría, severidad, `impact`, `remediation`; **nunca** el exploit crudo (payload de prompt-injection, request de sqlmap, system-prompt filtrado). Diseña el estado "exploit redactado" (candado + *"Oculto en el reporte público"*).
- **Estados del token** (contrato en [11-auth-magic-link](../11-auth-magic-link/spec.md) / [12-api](../12-api/spec.md)): inexistente → **404**; `expires_at < now()` o `revoked_at` → **410 Gone** con copy *"Este enlace expiró"*; válido → reporte redactado.
- Banner de compartir social + (opcional) **Report Card** (§F14-1).

---

## §F9 · Sitio / histórico (`/sites/[id]`)

**Propósito.** Vista por dominio: último escaneo + histórico. Anónimo. Es el **destino del click** en una fila del leaderboard.
**Datos.** `GET /sites/{id}` (último scan + histórico).
**Componentes.** Encabezado del sitio (host, `is_gov`/badge gov, grado actual), **dos gauges** 🛡️/🤖, línea de tiempo de escaneos (grado por fecha), **gráfico de tendencia** del grado (mini line chart recharts), enlace al reporte de cada escaneo. Reusa los chips/gauges de §F7.

---

## §F10 · Auth magic-link — 4 pantallas (`(public)`)

El repo trae auth por **password**; Owliver necesita **magic-link**, que no existe aún. **Decisión de superficie:** leaderboard, `/sites/{id}`, `/r/{token}`, reporte y scan **básico** son **anónimos**; solo watchlist/monitoreo y scans activos exigen sesión. Reusa el patrón BFF `/api/auth/*` ya existente. El contrato de tokens (TTL, 1-uso) lo posee [11-auth-magic-link](../11-auth-magic-link/spec.md). Las **4 pantallas/rutas**:

1. **Pedir email** — input + botón "Enviar enlace" → `POST /auth/magic-link`.
2. **"Revisa tu correo"** — confirmación con cooldown/reenvío visible.
3. **Callback / verify** — `GET /auth/callback?token=` (estados: verificando, ok, token inválido/expirado/consumido).
4. **Sesión iniciada** — post-login: cookie HttpOnly seteada, redirect a la watchlist o al **destino pendiente** (ej. el form de scan activo que disparó el login).

**Estados.** Errores de token (inválido/expirado/consumido) con copy claro + reenvío. Cooldown visible en la p.2.

---

## §F11 · Watchlist + monitoreo (`(protected)`)

**Propósito.** Un usuario agrega su(s) dominio(s), corre niveles activos (con autorización), activa `monitor=true` para re-escaneos periódicos.
**Datos.** `GET /watchlist` · `POST /watchlist {url, monitor}` · `PATCH /watchlist/{id} {monitor}` (toggle del Switch) · `DELETE /watchlist/{id}`.
**Componentes.** Tabla de sitios vigilados: hostname + grado actual + 🛡️/🤖 + último scan + **Switch `monitor`** + acción re-scan. Botón "Agregar dominio". Acceso a correr scan activo. Ajustes de alertas (email/Slack — ver spec.md §12). Los resultados de scans activos son **privados** de la cuenta salvo que el usuario genere un `/r/{token}`. **Alertas in-app son recorte** (solo email/Slack). Empty state: *"Agrega tu primer dominio para vigilarlo."*

---

## §F12 · Estados transversales, a11y, responsive, i18n

- **Loading:** skeletons (no spinners) en leaderboard, reporte, histórico.
- **Empty:** leaderboard (teórico), watchlist vacía ("agrega tu primer dominio"), sitio sin scans.
- **Error / códigos:** formato único `{error:{code,message,details}}` (ver [12-api](../12-api/spec.md)). Mapeo UI: **422** (atestación/validación → inline en el form), **404** (recurso/sin permiso → página "no encontrado", no confirmar existencia), **410** (token expirado → copy de enlace caducado), **403** (toast). Scan `partial` → banner "cobertura parcial". Scan colgado → estado con `tools_status`.
- **Toasts (sonner):** share generado, PDF listo, errores 403/410, copia de link.
- **Accesibilidad:** contraste AA en ambos modos (claro/SOC); foco visible; `prefers-reduced-motion` desactiva count-up/pulse; el theater no debe depender solo de color (íconos + texto en chips de severidad).
- **Responsive:** un solo breakpoint `md`. Leaderboard y reporte mobile-first; tabla→cards y 2-columnas→stack vertical; el theater colapsa los 2 carriles a stack vertical en móvil (el feed de findings manda). Variante móvil obligatoria para las 3 principales: Hall of Shame, Theater, Reporte.
- **i18n:** **español** primario (es-MX). Copys del demo en español literal (no lorem ipsum).

---

## §F13 · Sistema de componentes (shadcn + custom)

| Componente | Origen | Uso |
|---|---|---|
| **Accordion** | `npx shadcn add accordion` | un panel por finding (§F7 capa 2) |
| **Gauge** semicircular | `chart.tsx` + recharts `RadialBarChart` | dos sub-scores 🛡️/🤖 (`endAngle=180`, Label central score+grado) |
| **GradeBadge** A–F | custom | chip de grado con color de escala §F2 (mono) |
| **SeverityChip** | custom | critical/high/medium/low/info con ícono + color |
| **StatusBadge** | custom | "IA detectada, sin auditar", "cobertura parcial" |
| **Toasts** | `sonner` | feedback de acciones |
| **ToolChip** | custom (SOC) | herramienta encendida/apagada en el theater |
| **AgentLane** | custom (SOC) | carril de subagente con 🦉 + tools + estado |
| **FindingFeedItem** | custom (SOC→claro) | finding que entra en vivo / fila del reporte |
| **AttestationGate** | custom | advertencia + checkbox + términos (§F5) |
| **OwlMascot** | custom (SVG/Lottie) | estados idle/running/alert |
| **LiveProgress** | custom | barra 0–100 + `current_phase` + timer |

---

## §F14 · Features WOW opcionales (recortables)

Más allá del spec, para usefulness + viralidad. **Marcadas opcionales** — entran solo si el núcleo (§F4–§F7) está verde.

1. **🎴 Report Card compartible (OG image).** Genera una imagen tipo "boletín de calificaciones" del sitio (grado grande A–F + 🛡️/🤖 + nombre de la dependencia + marca Owliver, con la **F roja** bien visible) vía `next/og` (`opengraph-image.tsx` en `/r/[token]` y `/sites/[id]`). **Por qué:** el hall of shame se comparte solo cuando al pegar el link en X/WhatsApp aparece la tarjeta con la **F** roja. Hook viral #1. *Costo:* bajo (Next nativo). *Recorte:* tras §F8.

2. **💬 "Owliver te explica" — chat sobre tu reporte.** Caja de chat en el reporte donde el usuario pregunta en lenguaje llano ("¿qué es prompt injection?", "¿cómo arreglo el header faltante?") y Opus responde acotado a los findings de ESE scan (resumen compacto, sin evidence crudo, <2k tokens, igual que la síntesis — ver [09-reporting](../09-reporting/spec.md)). **Por qué:** materializa el lema "ultra fácil de entender"; convierte el reporte en conversación. *Costo:* medio (1 endpoint + UI). *Recorte:* es lo primero que cae si aprieta el tiempo.

3. **🎬 Replay cinematográfico del ataque.** Botón "revivir el escaneo" en el reporte que **reproduce los `scan_events`** (ya persistidos — ver [10-realtime-live-view](../10-realtime-live-view/spec.md)) como una línea de tiempo acelerada — el theater en diferido, sin necesidad de un scan en vivo. **Por qué:** garantiza el momento wow aunque el live falle, y permite revivir el ataque estrella contra el bot propio en loop durante el pitch. *Costo:* bajo-medio (reusa el render del theater + cursor sobre eventos). *Recorte:* tras el theater en vivo.

> Las tres reusan datos/infra que el backend **ya** produce (scores, `scan_events`, findings) → ninguna pide modelo de datos nuevo.

---

## §F15 · Mapeo al plan de 20h (spec.md §15) y orden de recorte

Carril **P4** trabaja contra **fixtures de los stubs** desde la hora 2.

| Horas | Entregable frontend |
|---|---|
| 0–2 | Consumir stubs/fixtures; piel Owliver (§F2 tokens); shell de rutas (§F3) |
| 2–8 | **Leaderboard** (§F4) + **form/gate** (§F5) contra fixtures; chips/gauges base |
| 8–14 | **Reporte** (§F7: doble gauge + resumen + accordion) + `/r/[token]` (§F8); magic-link callback |
| 14–16 | **Live Pentest Theater** (§F6) con replay-then-tail; demo-level <90s |
| 16–18 | Watchlist (§F11) + PDF/share + features wow que alcancen (§F14) |

**Núcleo que NUNCA se corta:** `form → scan → Finding[] → reporte` + **leaderboard gov** + **doble score** + el **finding agéntico estrella** en el reporte.

**Orden de recorte frontend** (si aprieta el tiempo), alineado con spec.md §15 (`live view → monitoreo/alertas → PDF/share → watchlist UI`):
`Theater en vivo (→ usar Replay §F14-3 o video)` → `chat Owliver (§F14-2)` → `PDF/share (→ Plan B: reporte in-app)` → `watchlist UI` → `Report Card`.

---

## §F16 · Checklist de pantallas

- [ ] `/` — Hall of Shame leaderboard (poblado por fixtures) 🔴
- [ ] Form de escaneo + gate de atestación condicional ⚖️
- [ ] `/scans/[id]` — ★ Live Pentest Theater (SOC, replay-then-tail) 🌑
- [ ] `/scans/[id]/report` — "Owliver te explica" (2 capas, doble gauge, accordion)
- [ ] `/r/[token]` — reporte público redactado (404/410)
- [ ] `/sites/[id]` — histórico del sitio
- [ ] Magic-link (4 pantallas) + sesión
- [ ] `/watchlist` — watchlist + monitoreo (protected)
- [ ] Estados transversales (loading/empty/error/partial) + toasts + a11y
- [ ] (opc.) Report Card · (opc.) chat Owliver · (opc.) Replay cinematográfico

---

> **Guion del demo (spec.md §17) mapeado a pantallas:** `/` (hall of shame poblado) → `/scans/[id]` (theater <90s + recarga muestra replay) → `/scans/[id]/report` (grado + "Owliver te explica" + finding agéntico estrella con canary) → `/r/[token]` (redacción de exploits). Cierre: *"Owliver vigila la seguridad del Estado y de tu IA — lo que nadie más está midiendo."*
