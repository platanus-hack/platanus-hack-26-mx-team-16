# Owliver — Sub-spec de Frontend 🦉

> ⚠️ **ARCHIVO / HISTÓRICO (2026-06-20).** Este sub-spec se movió y formalizó como
> [`product/features/13-frontend/spec.md`](../features/13-frontend/spec.md)
> (fusionando los refinamientos de frontend de `spec-gaps.md` §5). La **fuente de
> verdad** del frontend es esa feature; este archivo se conserva solo como
> referencia. Las referencias internas `[spec.md](spec.md)` de abajo apuntan al
> overview, hoy en [`../spec.md`](../spec.md).

> **Qué es este documento.** Un sub-spec derivado de [`spec.md`](spec.md) que
> recoge **solo las funcionalidades que debe tener el frontend** (Next.js).
> Consolida en un único lugar lo que en el spec vive disperso (§10 ranking, §11
> reporte, §12 live-view + magic-link, §14 API que consume, §15 carril P4, §17
> guion del demo), añade los **estados y componentes** que el spec no detalla, y
> propone **features wow opcionales**. No toca backend salvo para nombrar el
> endpoint/evento que cada pantalla consume.
>
> Contexto: hackathon 20h, equipo 3–4, carril **P4** (§15). Fecha: 2026-06-20.

## Decisiones de diseño (cerradas con el equipo)

| # | Decisión | Elección |
|---|----------|----------|
| FE-1 | **Dirección visual** | **Híbrido claro + SOC**: app clara y confiable (ángulo gov-audit, "The Inspection Bench") **+ live-view en modo oscuro tipo sala de operaciones** (el pentest theater es el momento cinematográfico) |
| FE-2 | **Centerpiece del wow** | **Live Pentest Theater** (§F6): agentes + herramientas + findings apareciendo en vivo. Es donde se concentra el detalle y la ambición. El reporte es el *payoff* |
| FE-3 | **Tono del ranking gov** | **Hall of Shame**: peores primero, rojo, provocador, máximo potencial viral. Marco "datos públicos no intrusivos" para defendibilidad legal (§3) |
| FE-4 | **Alcance del doc** | Spec consolidado **+ 3 features wow opcionales** (§F14), marcadas como recortables |

> ⚠️ **Nota de identidad.** `PRODUCT.md` / `DESIGN.md` y el frontend actual
> (`dashboard`, `members`, `roles`…) son del **boilerplate Doxiq**, no de
> Owliver. Owliver es un producto nuevo sobre ese boilerplate: reusamos la
> **infraestructura** (route-groups, BFF `/api/auth/*`, `serverHttp`/`authHttp`,
> tokens base de Tailwind v4) pero **Owliver tiene su propia piel** (§F2).

---

## §F1 · Stack y reglas de arquitectura frontend

- **Next.js 15 (App Router) + React 19 + TypeScript**, Tailwind CSS v4 (oklch,
  `@theme inline`), **shadcn + Base UI**. Charts con **recharts** (^3.6.0, ya
  presente). Toasts con **sonner**.
- **Cliente → backend SIEMPRE vía BFF** (regla del repo): los componentes
  `"use client"` hacen `fetch("/api/…")` same-origin; las `route.ts` server-side
  reenvían con `serverHttp` y manejan cookies HttpOnly + `X-Api-Key`. Nunca
  `fetch` directo a `Settings.apiBaseUrl` desde el browser.
- **Route-groups:** `(public)` para todo lo anónimo (leaderboard, scan básico,
  reporte, `/r/[token]`, magic-link) y `(protected)` para watchlist/monitoreo y
  scans activos. Decisión de superficie en §12.2 del spec.
- **SSE (live-view):** `EventSource` con `withCredentials: true` (no permite
  headers custom → auth por cookie, §12.1). **Replay-then-tail** sobre
  `Last-Event-ID` / `?since_seq=`. Compresión desactivada en la ruta.
- **Server Components por defecto**, Client Components solo donde hay estado/SSE
  (theater, form, filtros, gauges animados). `/r/[token]` es **server component**
  sin login (§11.3).

---

## §F2 · Dirección visual — "claro de día, SOC de noche"

Dos modos que conviven, no dos temas que el usuario alterna:

**A) App shell — claro, institucional, confiable (default).**
La mayor parte de la app (leaderboard, form, reporte, auth) vive aquí. Hereda los
tokens cool-gray + teal del repo, pero con **acento ámbar/oro = "ojos del búho"**
para Owliver.

```
--ow-primary:   oklch(0.59 0.095 180.54)   /* teal — confianza, marca */
--ow-ink:       oklch(0.222 0.029 253.225)  /* texto */
--ow-surface:   oklch(0.984 0.002 252.121)  /* fondo app */
--ow-card:      oklch(1 0 0)
--ow-accent:    oklch(0.78 0.15 75)          /* ámbar — ojos del búho, CTAs vivos */
```

**B) Live-view (theater) — oscuro, "war room", monospace.**
El momento estrella entra en modo SOC: near-black, telemetría, **Geist Mono**,
scanlines sutiles, neón funcional (no decorativo).

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
| **C** ≥70 | `oklch(0.80 0.14 90)` ámbar | cap de cobertura parcial (§9.2) |
| **D** ≥60 | `oklch(0.72 0.16 55)` naranja | |
| **E** ≥40 | `oklch(0.66 0.19 35)` naranja-rojo | zona poblada del leaderboard gov |
| **F** <40 | `oklch(0.58 0.22 25)` rojo | "hall of shame" |

- **Tipografía:** **Figtree** (UI) + **Geist Mono** (telemetría, payloads,
  evidencia, scores). Grados y scores siempre en mono → lectura "instrumento".
- **Radio** base 0.75rem, near-flat (hairline rings + whisper shadows) en claro;
  glow funcional en SOC.
- **Mascota 🦉:** el búho aparece como indicador de actividad (parpadea/gira la
  cabeza mientras escanea), no como clipart. Estados: dormido (idle), vigilando
  (running), encontró algo (alerta).
- **Motion:** entradas de findings con `fade+slide` corto; gauges animan de 0 al
  valor; grados hacen "count-up". Respetar `prefers-reduced-motion`.

---

## §F3 · Mapa de superficies (rutas)

| Ruta | Group | Auth | Propósito | Consume (§14) |
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
| `/watchlist` | protected | sesión | Watchlist + monitoreo (§F11) | `GET/POST/DELETE /watchlist` |

Acciones transversales: `POST /scans/{id}/share` (genera `/r/{token}`),
`GET /scans/{id}/report.pdf` (export), `POST /scans/{id}/cancel` (mata scan).

---

## §F4 · Hall of Shame — leaderboard gov (`/`) 🔴

**Propósito.** La portada. "El Estado bajo la lupa": ranking de `.gob.mx`
**peores primero**, poblado desde el segundo 0 (fixtures, §10/§15). Es la primera
impresión y el gancho viral.

**Datos.** `GET /ranking?country=mx` (cursor-paginado). Orden **autoritativo**:
`(overall_grade ASC, penalty_raw DESC)` (§9.4) — la fila muestra `penalty_raw`
(o el conteo ponderado) para que el contraste entre sitios en **F** sea visible.

**Layout / componentes.**
- **Hero provocador:** titular grande ("¿Qué tan segura es la IA del gobierno?"),
  contador de sitios auditados + cuántos en **F**. Marco de defendibilidad:
  micro-copy *"Datos 100% pasivos y públicos — equivalente a Mozilla Observatory
  / SSL Labs. No intrusivo (§3)."*
- **Tabla / cards ranking** (cada fila):
  - Posición + **grado grande A–F** (mono, color de escala §F2).
  - Nombre de la dependencia + hostname.
  - **Doble mini-gauge / chips:** 🛡️ Web vs 🤖 Agéntico — el contraste es el
    diferenciador. Una fila estrella tipo *SAT "C web / **F** agéntico"*.
  - Badge **"IA detectada, sin auditar"** cuando `agentic_status=detected_not_tested`
    (§9.1) — nunca se muestra como "sin riesgo".
  - Badge **"cobertura parcial"** cuando aplica el cap-C (§9.2).
  - `penalty_raw` visible (desempate) + tendencia (▲▼ vs scan previo, si hay).
- **Filtros:** por grado, por `source` peor (web/agéntico), por país (MX). Cursor
  "cargar más".
- **CTA:** "Audita cualquier URL" → abre el form (§F5).

**Estados.** Skeleton de filas (no spinner); empty solo teórico (fixtures
garantizan poblado); fila `failed`/`partial` con su etiqueta, nunca grado A
inflado.

**Wow.** Al cargar, los grados hacen **count-up** y las filas en **F** laten en
rojo una vez. Hover de una fila revela el "por qué" (top finding). Orden
"peores primero" hace que lo rojo domine la pantalla → impacto inmediato.

---

## §F5 · Form de escaneo + gate de atestación

**Propósito.** Entrada universal: URL + nivel. Es el control legal (§3) en UI.

**Componentes.**
- **Input URL** con validación + normalización (muestra el `host` detectado).
- **Selector de nivel** (3 cards): **Básico** (pasivo, anónimo, sin gate) ·
  **Intermedio** · **Avanzado** (activo). Cada card explica en lenguaje llano qué
  hace y su intrusividad.
- **Gate condicional de atestación** (§3, §14.3): si el nivel es activo
  (intermedio/avanzado) aparece:
  - Advertencia prominente: *"Vas a lanzar pruebas intrusivas contra **{host}**;
    hacerlo sin autorización es ilegal."*
  - **Checkbox obligatorio**: *"Declaro tener autorización para auditar este
    dominio."* + aceptar términos. Sin checkbox, el submit queda deshabilitado.
  - **Advertencia reforzada (copy en rojo)** si el host es `.gob.mx` u otro
    sensible — pero **se puede proceder** (la atestación es el control, no un
    bloqueo). Excepción: gov + activo lo rechaza el backend con **422** (§14.3) →
    el form lo muestra como error inline ("los sitios gov solo admiten escaneo
    pasivo").
- **Nivel activo** requiere sesión → si no hay, redirige a magic-link guardando
  el destino pendiente.

**Flujo.** submit → `POST /scans` → recibe `scan_id` → **redirect a
`/scans/[id]`** (theater). Idempotencia: si el backend devuelve 200 con un
`scan_id` existente, igual redirige (no crea duplicado).

**Estados.** Validación inline; loading en el botón; error 422 (gov/validación)
con copy claro; doble-submit deshabilitado.

---

## §F6 · ★ Live Pentest Theater (`/scans/[id]`) — EL CENTERPIECE 🌑

> El momento cinematográfico. Aquí Owliver **deja de ser un formulario y se
> convierte en un búho cazando en vivo.** Modo **SOC oscuro** (§F2-B).

**Propósito.** Renderizar el pentest en tiempo real: subagentes activos,
herramientas corriendo, findings apareciendo. Alto impacto en demo (§12, §17).

**Datos.**
- Estado inicial: `GET /scans/{id}` (status, progress, current_phase,
  tools_status, scores parciales).
- Stream: `GET /scans/{id}/stream` (SSE) con **replay-then-tail** (§12.1) —
  `EventSource(url, {withCredentials:true})`, cursor `Last-Event-ID`/`since_seq`.
- Eventos tipados: `agent_status | tool_start | tool_end | finding | phase |
  score | done | error`. `seq` monótono = orden + idempotencia de cliente
  (descartar `seq <= lastSeq`).

**Layout (war room).**
- **Header:** host objetivo + nivel + grado-en-construcción (placeholder hasta
  `done`) + **barra de progreso** (0–100, `current_phase` legible) + timer (con
  el **timeout demo <90s** visible como tranquilizador).
- **Dos carriles de agente** lado a lado, cada uno con su 🦉:
  - 🛡️ **OWASP Scanner (Sonnet)** — chips de tools (nuclei, zap, testssl…) que
    **se encienden** (`tool_start` → ámbar/pulse) y **se apagan** (`tool_end` →
    verde ok / rojo fail/timeout, alimentando `coverage`).
  - 🤖 **Agentic Surface Auditor (Sonnet)** — fases: detección → inventario →
    sondas. Muestra el chatbot detectado (vendor, modelo inferido) y cada probe.
- **Feed de findings en vivo** (centro/derecha): cada `finding` entra con
  `fade+slide`, chip de severidad (color §F2) + categoría OWASP/LLM + título. Los
  **críticos** laten en rojo (`--soc-hit`).
- **Telemetría inferior:** scores parciales (🛡️/🤖) actualizándose con eventos
  `score`; log monospace scrolleable (estilo terminal).
- **Cierre:** evento `done` → botón **"Ver reporte completo"** → `/scans/[id]/report`.

**Interacciones / control.**
- **Cancelar** (`POST /scans/{id}/cancel`) → evento terminal `done` con
  `{outcome:'cancelled'}` (§14.4); UI muestra "escaneo cancelado".
- **Reconexión / recarga:** al recargar, el **replay** desde Postgres repinta
  TODO el progreso (no queda vacío) — esto se demuestra en vivo (§17 paso 2).
- Heartbeat cada ~20s mantiene viva la conexión.

**Estados.**
- `queued` → "en cola" con 🦉 dormido.
- `running` → theater activo.
- `partial` → banner "cobertura parcial" (algún scanner falló, §9.2).
- `failed`/`error` → estado de error con `error` + `tools_status` para depurar.
- `cancelled` → estado terminal limpio.
- **Sin auth en scan privado** → 404 (no confirmar existencia, §14.2).

**Wow.**
- Es literalmente ver a la IA atacar. Los chips encendiéndose + findings cayendo
  + el rojo del crítico = tensión.
- **Demo-level:** perfil rápido (Nuclei subset + testssl + 1 probe al bot propio)
  con timeout duro <90s (§12.1); lo pesado (ZAP full/garak) se muestra desde
  resultados pre-horneados. El theater **nunca** se queda colgado en el pitch.
- Plan B: si el SSE falla (checkpoint H16 rojo) → **video de respaldo de 90s**
  (§17). El front debe degradar a un `<video>` sin romper el resto del guion.

---

## §F7 · Reporte "Owliver te explica" (el payoff)

Reporte interactivo in-app de **dos capas** (§11). Vuelve al **modo claro**
(confianza/lectura).

**Capa 1 — Ejecutiva (lenguaje llano, generada por Opus).**
- **Grado grande A–F** arriba (count-up) + **dos gauges semicirculares** 🛡️ Web /
  🤖 Agéntico (`RadialBarChart` recharts, `endAngle=180`, label central con score
  + grado).
- Párrafo **"Owliver te explica"** — qué encontramos y por qué importa, sin jerga.
- **Top 3 riesgos** priorizados con su impacto de negocio.
- **Inventario de superficie agéntica** detectada (qué chatbots/IA tiene el
  sitio, vendor, modelo inferido o "modelo no expuesto").
- **Badges de estado:** "IA detectada, sin auditar" (`detected_not_tested`,
  §9.1) y "cobertura parcial" (cap-C, §9.2).

**Capa 2 — Técnica (acordeón por finding).**
- **Accordion** (shadcn): header = chip severidad + categoría OWASP/LLM + título;
  body = `evidence` (payload + req/resp + screenshot), `impact`, `remediation`
  paso a paso, `references` (CWE/OWASP), `confidence`.
- **El finding agéntico estrella:** system-prompt leak del bot con su **canary**
  como evidencia incontestable — `evidence = {payload, respuesta_cruda,
  token_filtrado}` en bloque monospace destacado.
- **Filtros:** por severidad / source / categoría.
- **Findings `info`** (peso 0, §9): conteo aparte, no afectan score; incluye los
  meta "tool X no completó" (cobertura).
- **Tendencia histórica** (si hay scans previos, §11.2): cómo cambió el grado +
  findings nuevos/resueltos (vía `dedupe_key` + `first_seen`/`last_seen` a nivel
  site).

**Acciones.** Export **PDF** (`/scans/{id}/report.pdf`) · **Compartir** →
`POST /scans/{id}/share` genera `/r/{token}` (toast con el link, TTL 7 días).

**Estados.** Screenshots servidos desde ruta estática FastAPI
(`/data/scans/{id}/{n}.png`); placeholder si falta. Toasts (sonner) para
share/PDF/errores 403/410.

---

## §F8 · Reporte público `/r/[token]` (redactado)

**Propósito.** Link compartible sin login — **server component** (§11.3). El
gancho viral del hall of shame, pero seguro.

**Funcionalidad.**
- Renderiza la **capa ejecutiva completa** + findings técnicos **con los payloads
  de explotación redactados/ocultos** por defecto: muestra tipo, categoría,
  severidad, `impact`, `remediation`; **nunca** el exploit crudo (payload de
  prompt-injection, request de sqlmap, system-prompt filtrado).
- **Estados del token** (§11.3): inexistente → **404**; `expires_at < now()` o
  `revoked_at` → **410 Gone** con copy *"Este enlace expiró"*; válido → reporte
  redactado.
- Banner de compartir social + (opcional) **Report Card** (§F14-1).

---

## §F9 · Sitio / histórico (`/sites/[id]`)

**Propósito.** Vista por dominio: último escaneo + histórico. Anónimo.
**Datos.** `GET /sites/{id}` (último scan + histórico).
**Componentes.** Encabezado del sitio (host, `is_gov`, grado actual), línea de
tiempo de escaneos (grado por fecha), enlace al reporte de cada uno, gráfico de
tendencia del grado. Reusa los chips/gauges de §F7.

---

## §F10 · Auth magic-link — 4 pantallas (`(public)`)

Solo watchlist/monitoreo y scans activos exigen sesión (§12.2). Reusa el patrón
BFF `/api/auth/*`. Las **4 pantallas/rutas**:

1. **Pedir email** — input + envío → `POST /auth/magic-link`.
2. **"Revisa tu correo"** — confirmación con cooldown/reenvío.
3. **Callback / verify** — `GET /auth/callback?token=` (estados: verificando, ok,
   token inválido/expirado). TTL 10 min, 1 uso (§14.1).
4. **Sesión** — post-login: cookie HttpOnly seteada, redirect a la watchlist o al
   **destino pendiente** (ej. el form de scan activo que disparó el login).

**Estados.** Errores de token (inválido/expirado/consumido) con copy claro +
reenvío. Cooldown visible en la p.2.

---

## §F11 · Watchlist + monitoreo (`(protected)`)

**Propósito.** Un usuario agrega su(s) dominio(s), corre niveles activos (con
autorización), activa `monitor=true` para re-escaneos periódicos.
**Datos.** `GET /watchlist` · `POST /watchlist {url, monitor}` ·
`DELETE /watchlist/{id}`.
**Componentes.** Lista de sitios vigilados (grado actual + tendencia + toggle
`monitor`), botón "agregar dominio", acceso a correr scan activo, ajustes de
alertas (email/Slack — §12; alertas in-app son recorte). Los resultados de scans
activos son **privados** de la cuenta (§3/§10) salvo que el usuario genere un
`/r/{token}`.

---

## §F12 · Estados transversales, a11y, responsive, i18n

- **Loading:** skeletons (no spinners) en leaderboard, reporte, histórico.
- **Empty:** leaderboard (teórico), watchlist vacía ("agrega tu primer dominio"),
  sitio sin scans.
- **Error / códigos:** formato único `{error:{code,message,details}}` (§14.5).
  Mapeo UI: **422** (gov/validación → inline en el form), **404** (recurso/sin
  permiso → página "no encontrado", no confirmar existencia), **410** (token
  expirado → copy de enlace caducado), **403** (toast). Scan `partial` → banner
  "cobertura parcial". Scan colgado → estado con `tools_status`.
- **Toasts (sonner):** share generado, PDF listo, errores 403/410, copia de link.
- **Accesibilidad:** contraste AA en ambos modos (claro/SOC); foco visible;
  `prefers-reduced-motion` desactiva count-up/pulse; el theater no debe depender
  solo de color (íconos + texto en chips de severidad).
- **Responsive:** leaderboard y reporte mobile-first; el theater colapsa los 2
  carriles a stack vertical en móvil (el feed de findings manda).
- **i18n:** **español** primario (es-MX). Copys del demo en español.

---

## §F13 · Sistema de componentes (shadcn + custom)

| Componente | Origen | Uso |
|---|---|---|
| **Accordion** | `npx shadcn add accordion` | un panel por finding (§F7 capa 2) |
| **Gauge** semicircular | `chart.tsx` + recharts `RadialBarChart` | dos sub-scores 🛡️/🤖 |
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

Más allá del spec, para usefulness + viralidad. **Marcadas opcionales** — entran
solo si el núcleo (§F4–§F7) está verde.

1. **🎴 Report Card compartible (OG image).** Genera una imagen tipo "boletín de
   calificaciones" del sitio (grado grande A–F + 🛡️/🤖 + nombre de la dependencia
   + marca Owliver) vía `next/og` (`opengraph-image.tsx` en `/r/[token]` y
   `/sites/[id]`). **Por qué:** el hall of shame se comparte solo cuando al pegar
   el link en X/WhatsApp aparece la tarjeta con la **F** roja. Hook viral #1.
   *Costo:* bajo (Next nativo). *Recorte:* tras §F8.

2. **💬 "Owliver te explica" — chat sobre tu reporte.** Caja de chat en el reporte
   donde el usuario pregunta en lenguaje llano ("¿qué es prompt injection?",
   "¿cómo arreglo el header faltante?") y Opus responde acotado a los findings de
   ESE scan (resumen compacto, sin evidence crudo, <2k tokens, igual que la
   síntesis §6). **Por qué:** materializa el lema "ultra fácil de entender";
   convierte el reporte en conversación. *Costo:* medio (1 endpoint + UI).
   *Recorte:* es lo primero que cae si aprieta el tiempo.

3. **🎬 Replay cinematográfico del ataque.** Botón "revivir el escaneo" en el
   reporte que **reproduce los `scan_events`** (ya persistidos, §12.1) como una
   línea de tiempo acelerada — el theater en diferido, sin necesidad de un scan en
   vivo. **Por qué:** garantiza el momento wow aunque el live falle, y permite
   revivir el ataque estrella contra el bot propio en loop durante el pitch.
   *Costo:* bajo-medio (reusa el render del theater + cursor sobre eventos).
   *Recorte:* tras el theater en vivo.

> Las tres reusan datos/infra que el backend **ya** produce (scores, `scan_events`,
> findings) → ninguna pide modelo de datos nuevo.

---

## §F15 · Mapeo al plan de 20h (§15) y orden de recorte

Carril **P4** trabaja contra **fixtures de los stubs** desde la hora 2 (§15).

| Horas | Entregable frontend |
|---|---|
| 0–2 | Consumir stubs/fixtures; piel Owliver (§F2 tokens); shell de rutas (§F3) |
| 2–8 | **Leaderboard** (§F4) + **form/gate** (§F5) contra fixtures; chips/gauges base |
| 8–14 | **Reporte** (§F7: doble gauge + resumen + accordion) + `/r/[token]` (§F8); magic-link callback |
| 14–16 | **Live Pentest Theater** (§F6) con replay-then-tail; demo-level <90s |
| 16–18 | Watchlist (§F11) + PDF/share + features wow que alcancen (§F14) |

**Núcleo que NUNCA se corta (§15):** `form → scan → Finding[] → reporte` +
**leaderboard gov** + **doble score** + el **finding agéntico estrella** en el
reporte.

**Orden de recorte frontend** (si aprieta el tiempo), alineado con §15
(`live view → monitoreo/alertas → PDF/share → watchlist UI`):
`Theater en vivo (→ usar Replay §F14-3 o video)` → `chat Owliver (§F14-2)` →
`PDF/share (→ Plan B: reporte in-app, §17)` → `watchlist UI` → `Report Card`.

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

> **Guion del demo (§17) mapeado a pantallas:** `/` (hall of shame poblado) →
> `/scans/[id]` (theater <90s + recarga muestra replay) → `/scans/[id]/report`
> (grado + "Owliver te explica" + finding agéntico estrella con canary) →
> `/r/[token]` (redacción de exploits). Cierre: *"Owliver vigila la seguridad del
> Estado y de tu IA — lo que nadie más está midiendo."*
