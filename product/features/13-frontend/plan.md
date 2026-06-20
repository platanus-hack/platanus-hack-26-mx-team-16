---
feature: frontend
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §F1–§F16; 12-api/plan.md §1; auth/frontend-auth.md (BFF, serverHttp/authHttp); 10-realtime-live-view §; 09-reporting §; 08-ranking-watchlists §; 02-attack-levels §; 01-legal-ethics §2.4; PRODUCT.md; DESIGN.md; product/design-prompt.md (brief visual de alta fidelidad, copy literal por pantalla)
---

# Owliver — Frontend (Next.js) — plan de implementación (CÓMO)

> El entregable medular **no** es "muchas pantallas", sino **(1)** la **piel
> Owliver** sobre el shell SaaS existente — un route-group `(public)` con layout
> propio que sirve las superficies anónimas virales (Hall of Shame, reporte
> público, scan básico) sin sidebar — y **(2)** las cuatro piezas que el demo
> exige funcionando contra **fixtures desde la hora 2**: el **leaderboard gov RSC**,
> el **form + gate de atestación**, el **Live Pentest Theater** (SSE
> replay-then-tail, modo SOC) y el **reporte "Owliver te explica"** (doble gauge +
> acordeón). Todo lo demás (histórico, watchlist, login, features wow) cuelga
> de esas cuatro.
>
> Principio operativo: **el browser nunca habla con el backend directo.** Cada
> superficie lee vía BFF (`fetch("/api/…")` → `route.ts` server → `serverHttp`) o
> vía el proxy `/api/v1/*` de `src/proxy.ts`; el front **no calcula** score,
> `dedupe_key`, `is_gov` ni grado — los pinta tal como llegan de [12-api](../12-api/plan.md).
> La UI es composición + estado + diseño; los contratos viven en las features
> hermanas (se enlazan, no se duplican).

## 0. Estado de las dependencias

El frontend hoy es el **shell SaaS Doxiq** (login password, dashboard, members,
roles, settings). Owliver reusa su **infraestructura** y construye su **piel nueva**
encima. Lo que **ya existe** y se reutiliza tal cual (rutas reales verificadas):

- **HTTP / BFF:** `frontend/src/infrastructure/http/client.ts` exporta `serverHttp`
  (axios `baseURL = ${Settings.apiBaseUrl}/v1`, server-only), `localHttp` y
  `authHttp` (axios `baseURL "/api"`, con interceptor de auth + refresh
  deduplicado). `frontend/src/infrastructure/requests.ts` aporta `getCommonHeaders`
  (inyecta `X-Api-Key` solo en server). **No se reinventa** ningún cliente HTTP.
- **Proxy / middleware:** `frontend/src/proxy.ts` reescribe `/api/v1/*` → backend
  con `X-Api-Key` (y CF-Access headers), y define `PUBLIC_EXACT_ROUTES` /
  `PUBLIC_PREFIX_ROUTES`. Aquí **se amplían esas listas** con las rutas públicas de
  Owliver (`/scan`, `/r/`, `/sites/`, `/login`, `/auth/callback`); el mecanismo no
  se toca.
- **Auth BFF de referencia:** `frontend/src/app/api/auth/{login,refresh,logout,reset-password}/route.ts`
  + `frontend/src/app/page.tsx` (form login) son el patrón canónico
  cliente→`/api/auth/*`→`serverHttp`→cookies HttpOnly (documentado en
  [auth/frontend-auth.md](../auth/frontend-auth.md)). El login Google de §F10 **espeja
  exactamente** este patrón (mismo BFF/cookies HttpOnly del boilerplate).
- **Route-groups:** `frontend/src/app/(public)/` (register, reset-password,
  invitations, unassigned) y `frontend/src/app/(protected)/` (dashboard, members,
  roles, settings, profile) **ya existen**. Owliver añade superficies a ambos; el
  `(protected)/layout.tsx` con `force-dynamic` + `refreshServerSession()` se reusa
  para watchlist.
- **Sesión (cliente):** `frontend/src/application/contexts/session-store.ts` +
  `session.tsx` (zustand, tokens en memoria, `user`/`tenant` persistidos). El
  login Google setea sesión por el mismo store.
- **i18n:** `frontend/src/i18n/{config.ts,request.ts}` + `frontend/src/i18n/messages/{en,es}.json`
  (next-intl, `useTranslations`). **es-MX es primario** — todos los copys de Owliver
  entran como claves nuevas en `frontend/src/i18n/messages/es.json` (y `en.json`).
  `frontend/src/app/actions/locale.ts` ya existe. (La ruta real es
  `src/i18n/messages/`; **no** existe `src/messages/`.)
- **Tokens de diseño:** `frontend/src/app/globals.css` (`@theme inline`): `--primary`
  teal `oklch(0.59 0.095 180.54)`, `--font-sans` **Figtree**, `--font-mono`
  **Geist Mono**, `--radius: 0.75rem`, neutrales cool-gray. Owliver **extiende** este
  bloque con los tokens `--ow-*`, `--soc-*` y la escala A–F (§3), no lo reemplaza.
  Gobernado por `PRODUCT.md` + `DESIGN.md` (+ `product/design-prompt.md` como brief
  visual de alta fidelidad). El mirror machine-readable `.impeccable/design.json` que
  menciona `CLAUDE.md` **aún no existe** en el repo (solo `.impeccable/briefs/` y
  `.impeccable/critique/`); si se genera vía `/impeccable`, prevalece — hasta entonces
  la fuente de tokens es `globals.css` + `DESIGN.md`.
- **Componentes shadcn + Base UI:** `frontend/src/presentation/components/ui/`
  (`table.tsx`, `card.tsx`, `dialog.tsx`, `checkbox.tsx`, `switch.tsx`, `badge.tsx`,
  `skeleton.tsx`, `tabs.tsx`, `select.tsx`, `collapsible.tsx`, `alert.tsx`,
  `tooltip.tsx`, `button.tsx`, `field.tsx`, `input.tsx`, …) y comunes
  (`components/common/empty-state.tsx`, `status-ring.tsx`, `page-content.tsx`). Se
  reusan; **faltan** `accordion`, `chart` (recharts) y `sonner` (ver §0.1).
- **Data fetching client:** `@tanstack/react-query` (^5) ya en `package.json` +
  hooks en `frontend/src/application/hooks/queries/`. Watchlist/filtros lo reusan.

### 0.1 Dependencias que faltan y hay que añadir

> **Corrección a la spec:** la spec §F1 afirma `recharts (^3.6.0, ya presente)`. Es
> **incorrecto** — **verificado: `recharts` NO está en `frontend/package.json` y no
> existe `components/ui/chart.tsx`**. Este plan **overridea** la spec en este punto:
> recharts y su `chart.tsx` son **net-new**. Un revisor **no** debe "restaurar" la
> suposición de que ya están instalados. `sonner` la spec sí lo marca como faltante.

Se añaden en la hora 0–2 (no bloquean fixtures pero sí el reporte/gauges):

| Pieza | Acción | Dónde se usa |
|---|---|---|
| **recharts** | `npm i recharts` | gauges semicirculares §F7/§F9 (`RadialBarChart`, `endAngle=180`) + mini line chart de tendencia |
| **chart.tsx** | `npx shadcn add chart` (genera `components/ui/chart.tsx`, wrapper recharts) | base de los gauges |
| **accordion** | `npx shadcn add accordion` | capa técnica del reporte §F7 (un panel por finding) |
| **sonner** | `npm i sonner` + `npx shadcn add sonner` + `<Toaster/>` en el layout raíz | toasts de share/PDF/errores 403/410 §F12 |

> El resto (count-up, pulse, scanlines, mascota 🦉) se hace con CSS/`@keyframes` en
> `globals.css` + framer-motion **opcional** (si no, transiciones CSS); no se añade
> dependencia de animación obligatoria.

## 1. Decisión de superficies / route-groups

Dos grupos, dos audiencias (§F1/§F10). La regla de corte es **auth**, no tema:

| Group | Layout | Rutas Owliver | Auth |
|---|---|---|---|
| `(public)` | **nuevo** `(public)/layout.tsx` Owliver: header logo + "Leaderboard" + "Escanear" (sin sidebar) | `/`, `/scan`, `/scans/[id]`, `/scans/[id]/report`, `/sites/[id]`, `/r/[token]`, `/login`, `/login/check-email`, `/auth/callback` | anónimo (o token) |
| `(protected)` | reusa `(protected)/layout.tsx` (`force-dynamic` + `refreshServerSession`) | `/watchlist` | sesión |

> **Decisión clave (§F1, nota de identidad):** `/` (raíz) hoy lo ocupa el **login
> password** del boilerplate (`src/app/page.tsx`). Owliver **mueve** el login a
> `/login` (Google, §F10) y **reescribe `/` como el Hall of Shame** RSC. El form
> password se retira (Owliver no usa password). El `(public)` Owliver lleva **layout
> propio** que NO comparte el `AuthContainer` centrado del shell.
>
> **Scans `public` vs `private`:** `/scans/[id]` y `/scans/[id]/report` viven en
> `(public)` pero su acceso lo decide el **backend por `visibility`**
> ([12-api](../12-api/plan.md) §4: 404 no-403 para privado sin permiso). El front
> no duplica la decisión de AuthZ: pasa la cookie (vía BFF/SSE `withCredentials`) y
> renderiza lo que le devuelvan (200 → theater/reporte; 404 → "no encontrado").

**Dónde vive cada capa (Clean Arch del frontend, igual que el shell):**
- `frontend/src/app/**` — App Router (pages RSC + BFF `route.ts`).
- `frontend/src/presentation/owliver/**` — **net-new**: componentes y vistas de
  Owliver, separados de los del shell (`presentation/{auth,members,roles,…}`) para
  no mezclar pieles.
- `frontend/src/application/owliver/**` — **net-new**: hooks (react-query),
  stores zustand del theater (estado SSE), schemas zod del form.
- **Data-access:** por la regla nueva de `CLAUDE.md`, los hooks llaman a
  `authHttp`/`serverHttp` vía BFF **directo**; **no** se crean
  `domain/repositories` ni `infrastructure/repositories/http-*` para Owliver.

## 2. Mapa de archivos a crear

### 2.1 Tokens de diseño — `frontend/src/app/globals.css`

Se **extiende** el `@theme inline` y el bloque `:root` con los tokens de §F2
(verbatim de la spec), sin tocar los del shell:

```css
/* App shell Owliver (claro) */
--ow-accent: oklch(0.78 0.15 75);   /* ámbar — ojos del búho, CTAs vivos */
/* Live-view SOC (oscuro, scoped a .soc) */
--soc-bg: oklch(0.16 0.02 250);  --soc-grid: oklch(0.24 0.02 250);
--soc-live: oklch(0.80 0.13 195); --soc-tool: oklch(0.80 0.14 75);
--soc-hit: oklch(0.64 0.22 25);
/* Escala A–F — única fuente de color de grados (chips/gauges/filas) */
--grade-a: oklch(0.72 0.16 150); --grade-b: oklch(0.75 0.15 130);
--grade-c: oklch(0.80 0.14 90);  --grade-d: oklch(0.72 0.16 55);
--grade-e: oklch(0.66 0.19 35);  --grade-f: oklch(0.58 0.22 25);
```

El modo SOC se aplica **scoped** (clase `.soc` en el contenedor del theater), no como
tema global — así conviven "claro de día / SOC de noche" sin toggle (§F2). Las
`@keyframes` de count-up / pulse-crítico / scanline también aquí.

### 2.2 Rutas (App Router) — `frontend/src/app/`

```
(public)/
  layout.tsx                      # layout Owliver (header logo + nav, sin sidebar)
  page.tsx                        # «/» Hall of Shame (RSC)  §F4
  scan/page.tsx                   # form + gate (o modal montable desde «/»)  §F5
  scans/[id]/page.tsx             # Live Theater (client wrapper + SSE)  §F6
  scans/[id]/report/page.tsx      # reporte "Owliver te explica" (RSC + islas)  §F7
  sites/[id]/page.tsx             # histórico del sitio (RSC)  §F9
  r/[token]/page.tsx              # reporte público redactado (RSC, sin login)  §F8
  r/[token]/opengraph-image.tsx   # (opc.) Report Card OG  §F14-1
  login/page.tsx                  # login Google (botón OAuth del boilerplate)  §F10
(protected)/
  watchlist/page.tsx              # watchlist + monitoreo  §F11
api/                              # BFF (server) — §4
  scans/route.ts                  # POST /scans            → serverHttp POST /v1/scans
  scans/[id]/route.ts             # GET  estado inicial
  scans/[id]/findings/route.ts    # GET  findings
  scans/[id]/share/route.ts       # POST share → {token}
  scans/[id]/cancel/route.ts      # POST cancel
  ranking/route.ts                # GET  /ranking?country=mx (o fetch directo RSC)
  sites/[id]/route.ts             # GET  histórico
  watchlist/route.ts              # GET/POST
  watchlist/[id]/route.ts         # PATCH/DELETE
  # login Google: reusa el BFF /api/auth/login del boilerplate (sin rutas nuevas)
```

> **RSC vs BFF:** las superficies **RSC anónimas** (`/`, `/r/[token]`, `/sites/[id]`)
> leen server-side **directo con `serverHttp`** dentro del componente server (no
> necesitan `route.ts`). Las **client islands** (form, filtros, watchlist, theater)
> usan `route.ts` BFF + `authHttp`/`fetch("/api/…")`. El stream SSE **no** pasa por
> `route.ts`: usa `EventSource` contra el proxy `/api/v1/scans/{id}/stream` (§5).

### 2.3 Componentes — `frontend/src/presentation/owliver/`

Sistema de componentes de §F13 (todos net-new salvo lo que reusa shadcn):

| Archivo | Base | Uso |
|---|---|---|
| `components/grade-badge.tsx` | custom (mono) | chip A–F con color de escala §3 |
| `components/severity-chip.tsx` | custom (ícono+color) | critical…info; **no solo color** (a11y §F12) |
| `components/status-badge.tsx` | `ui/badge.tsx` | "IA detectada, sin auditar", "cobertura parcial" |
| `components/score-gauge.tsx` | `ui/chart.tsx` + recharts | semicircular 🛡️/🤖 (`RadialBarChart`, `endAngle=180`, Label central score+grado) |
| `components/owl-mascot.tsx` | SVG inline | estados idle/running/alert (ojos ámbar) |
| `leaderboard/ranking-table.tsx` | `ui/table.tsx` | filas peores-primero + doble mini-gauge §F4 |
| `leaderboard/ranking-filters.tsx` | `ui/select.tsx` (client) | grado / source / país |
| `scan/scan-form.tsx` | `ui/field,input,card` (client) | URL + nivel + gate §F5 |
| `scan/level-cards.tsx` | radio cards | básico/intermedio/avanzado §F5 |
| `scan/attestation-gate.tsx` | `ui/checkbox,dialog` (client) | advertencia + checkbox + términos §F5 |
| `theater/*` | custom SOC (client) | `tool-chip`, `agent-lane`, `finding-feed-item`, `live-progress`, `telemetry-log` §F6 |
| `report/*` | RSC + islas | `executive-summary`, `score-gauges`, `finding-accordion` (`ui/accordion`), `surface-inventory`, `trend-chart` §F7 |
| `report/share-actions.tsx` | `ui/button` + sonner (client) | PDF + share §F7 |
| `public-report/redacted-finding.tsx` | custom | estado "exploit redactado" (candado) §F8 |
| `watchlist/watchlist-table.tsx` | `ui/table,switch` (client) | monitor switch + re-scan §F11 |

### 2.4 Estado / hooks / schemas — `frontend/src/application/owliver/`

```
stores/theater-store.ts     # zustand: lastSeq, agentes, tools, findings[], scores, status
hooks/use-scan-stream.ts    # EventSource replay-then-tail (Last-Event-ID/since_seq)  §5
hooks/use-ranking.ts        # react-query: cursor "cargar más" + filtros  §F4
hooks/use-watchlist.ts      # react-query: GET/POST/PATCH/DELETE  §F11
schemas/scan-form.ts        # zod: url (new URL + reglas SSRF cliente) + level + authorized  §F5
lib/grade.ts                # gradeColor(grade)→var(--grade-x); gradeFromScore (solo display)
lib/url.ts                  # normalizeUrl, extractHost, rejectPrivateHost  §F5
lib/sse-event.ts            # tipos TS de ScanEvent (espejo de events.py de 06)  §5
```

> `lib/grade.ts` y `lib/sse-event.ts` **solo mapean para render**: el grado/score
> los calcula [07-scoring](../07-scoring/spec.md) en backend; el front nunca deriva
> el grado autoritativo, solo elige el color.

## 3. Sistema de diseño y modos (claro / SOC)

- **Tipografía instrumento:** grados y scores **siempre** en `--font-mono` (Geist
  Mono) — lectura "instrumento" (§F2). UI en Figtree.
- **Escala A–F como única fuente de color:** `grade-badge`, `severity-chip`, filas
  del leaderboard y gauges leen **solo** de `--grade-*` (§2.1). Prohibido hardcodear
  colores de grado fuera de `lib/grade.ts`.
- **Modo SOC scoped:** el theater monta un contenedor `className="soc"` que activa
  los `--soc-*`, scanlines (`background` con `repeating-linear-gradient`) y glow
  funcional. Fuera del theater, app clara institucional (default del shell).
- **Mascota 🦉 `owl-mascot.tsx`:** estados `idle|running|alert` (SVG con clases que
  animan ojos/cabeza); es indicador de actividad, no clipart.
- **Motion (§F2/§F12):** entradas de findings `fade+slide` corto; gauges 0→valor;
  grados `count-up`; críticos laten una vez en rojo. **Todo bajo
  `@media (prefers-reduced-motion: reduce)`** que desactiva count-up/pulse. Contraste
  AA en ambos modos; foco visible (no se elimina el outline).
- Antes de tocar UI: leer `PRODUCT.md` (registro `product`, North Star "The
  Inspection Bench"), `DESIGN.md` (Do's/Don'ts) y **`product/design-prompt.md`** —
  el **brief visual de alta fidelidad** que la spec §F2 designa como fuente de **copy
  literal por pantalla** ("claro de día, SOC de noche"). Anti-referencias: SaaS
  genérico, look "app de IA" morado, enterprise legacy.

## 4. Data-access por superficie (RSC vs BFF)

Mapeo a [12-api](../12-api/plan.md) §1. Toda lectura cruza el límite servidor;
nunca hay `fetch` del browser a `Settings.apiBaseUrl`.

| Superficie | Cómo lee | Endpoint backend |
|---|---|---|
| `/` Hall of Shame | **RSC** `serverHttp.get` (+ react-query client para "cargar más"/filtros vía `route.ts`) | `GET /ranking?country=mx` (cursor) |
| `/scan` form | client → `fetch("/api/scans")` → BFF `serverHttp.post` | `POST /scans` |
| `/scans/[id]` theater | RSC estado inicial `serverHttp.get`; luego SSE | `GET /scans/{id}` + `…/stream` |
| `/scans/[id]/report` | **RSC** `serverHttp.get` ×2 | `GET /scans/{id}` · `/findings` |
| `/sites/[id]` | **RSC** `serverHttp.get` | `GET /sites/{id}` |
| `/r/[token]` | **RSC** `serverHttp.get` (sin cookie) | `GET /r/{token}` |
| `/watchlist` | client react-query → BFF | `GET/POST/PATCH/DELETE /watchlist` |
| share / PDF / cancel | client → `fetch("/api/scans/{id}/…")` → BFF | `POST …/share`·`…/cancel`; PDF = link directo proxied |
| login Google | client → redirect OAuth → BFF `/api/auth/login` (boilerplate) | flujo OAuth Google |

- **BFF cookies/X-Api-Key:** el `X-Api-Key` lo inyecta `proxy.ts` (proxy) o
  `getCommonHeaders` en server (BFF). El BFF de login **Google**
  (`api/auth/login/route.ts` del boilerplate) **setea las cookies HttpOnly** (mismo
  patrón de [auth/frontend-auth.md](../auth/frontend-auth.md)).
- **Formato de error** `{errors:[{code,message}], validation, timestamp}` ([12-api](../12-api/plan.md)
  §5.1): el BFF re-propaga status; el cliente mapea **422**→inline en form,
  **404**→página "no encontrado" (no confirma existencia), **410**→copy enlace
  caducado, **403**→toast (§F12).

## 5. Live Pentest Theater — SSE replay-then-tail (`/scans/[id]`)

La **mecánica del stream** (eventos, `seq`, heartbeat, `since_seq`) la posee
[10-realtime-live-view](../10-realtime-live-view/spec.md); aquí solo el **consumo
en cliente** y la **composición UI**:

- **Transporte:** `use-scan-stream.ts` abre `new EventSource("/api/v1/scans/{id}/stream", {withCredentials:true})`
  — pasa por `proxy.ts` (que añade `X-Api-Key`); `withCredentials` lleva la cookie de
  sesión (EventSource **no** permite headers custom → auth por cookie, §F1).
- **Replay-then-tail:** al (re)conectar, el navegador manda `Last-Event-ID`; el
  backend repinta todo desde Postgres y luego sigue en vivo. **Recargar repinta TODO
  el progreso** (demo §17 paso 2) — el store se diseña asumiendo replay idempotente:
  **descartar `event.seq <= lastSeq`** (`theater-store.ts`).
- **Reducer por tipo** (`agent_status|tool_start|tool_end|finding|phase|score|done|error`):
  enciende/apaga `tool-chip`, actualiza `agent-lane`, empuja `finding-feed-item`
  (con `fade+slide`; crítico → pulse `--soc-hit`), mueve `live-progress`
  (`current_phase` legible + timer con timeout demo <90s visible), actualiza scores
  parciales en la telemetría.
- **Control:** "Cancelar" → `fetch("/api/scans/{id}/cancel")` → evento terminal
  `done{outcome:'cancelled'}`. `done` → botón "Ver reporte completo →"
  `/scans/[id]/report`.
- **Estados** (§F6): `queued`→🦉 dormido; `running`→theater; `partial`→banner
  "cobertura parcial"; `failed/error`→error con `tools_status`; `cancelled`→terminal
  limpio; privado sin auth → 404.
- **Plan B (degradación):** si el SSE falla (checkpoint demo), el componente degrada
  a `<video>` de respaldo 90s y/o al **Replay cinematográfico** §F14-3 (cursor sobre
  `scan_events` ya persistidos) sin romper el resto del guion.

## 6. Form de escaneo + gate de atestación (`/scan`)

El **invariante de atestación** lo posee [01-legal-ethics](../01-legal-ethics/spec.md)
§2.4 y los **niveles** [02-attack-levels](../02-attack-levels/spec.md); aquí el
control convertido en UI:

- **Validación/normalización cliente** (`lib/url.ts` + `schemas/scan-form.ts`):
  `new URL()`, prefija `https://` si falta, extrae y muestra el `host`
  (preview *"Vas a escanear: sat.gob.mx"*), **rechaza** IP privada / `localhost` /
  hostname sin punto. Es UX, **no** seguridad: el SSRF real lo valida el backend.
- **Selector de nivel** (`level-cards.tsx`, 3 radio cards): Básico (pasivo, anónimo,
  default) · Intermedio (activo suave) · Avanzado (explotación). Copy llano de
  intrusividad por card.
- **Gate condicional** (`attestation-gate.tsx`): aparece **solo** si nivel ∈
  {intermedio, avanzado}; en básico queda oculto y `authorized=false`. Checkbox
  obligatorio *"Declaro tener autorización…"* (submit deshabilitado sin marcar) +
  Dialog "Ver términos". Refuerzo en **rojo** si host `.gob.mx` (se **puede**
  proceder bajo atestación — la atestación es el control, no un bloqueo por dominio;
  el resultado queda **privado**).
- **Nivel activo requiere sesión:** si no hay, redirige a `/login` guardando el
  **destino pendiente** (querystring/cookie) que el callback de login Google consume al volver
  (§F10).
- **Flujo:** submit → loading en botón (doble-submit deshabilitado) →
  `fetch("/api/scans")` → `scan_id` → **redirect `/scans/[id]`**. Idempotente: si ya
  hay scan vivo el backend devuelve el `scan_id` existente (200) y se redirige igual.
  Errores: 422 (atestación/validación) inline; 403 → toast.

## 7. Reporte, reporte público, histórico, login, watchlist

Cada uno **renderiza** un contrato que vive en otra feature; aquí la composición:

- **Reporte "Owliver te explica" (`/scans/[id]/report`, §F7)** — contenido de
  [09-reporting](../09-reporting/spec.md). RSC con islas: **Capa 1 ejecutiva** =
  grado grande (count-up) + **dos `score-gauge`** 🛡️/🤖 + párrafo Opus + Top-3
  riesgos + inventario de superficie agéntica + badges. **Capa 2 técnica** =
  `finding-accordion` (`ui/accordion`): header chip severidad+categoría+título;
  body `evidence`/`impact`/`remediation`/`references`/`confidence`. **Finding
  agéntico estrella:** system-prompt leak con **canary** en bloque monospace
  destacado. Filtros por severidad/source/categoría; `info` (peso 0) aparte;
  tendencia histórica si hay scans previos. Acciones: PDF (`/scans/{id}/report.pdf`
  vía link proxied) + Compartir (`share-actions.tsx` → toast con `/r/{token}`).
- **Reporte público (`/r/[token]`, §F8)** — **RSC sin login**. Capa ejecutiva
  completa + findings con **payloads de explotación redactados** (`redacted-finding.tsx`:
  candado + *"Oculto en el reporte público"*; **nunca** el exploit crudo). Estados
  de token: inexistente→**404**, expirado/`revoked`→**410** ("Este enlace expiró"),
  válido→redactado. (Opc.) Report Card OG §F14-1.
- **Histórico (`/sites/[id]`, §F9)** — RSC anónimo, destino del click en el
  leaderboard. Encabezado (host, badge gov, grado actual) + dos gauges + timeline de
  scans + `trend-chart` (mini line recharts). Reusa chips/gauges de §F7.
- **Login Google (§F10)** — reusa el BFF `/api/auth/login` del boilerplate
  ([auth/frontend-auth.md](../auth/frontend-auth.md)): botón "Entrar con Google" →
  OAuth → cookie HttpOnly → redirect a watchlist o **destino pendiente**.
- **Watchlist (`/watchlist`, `(protected)`, §F11)** — `watchlist-table.tsx`:
  hostname + grado + 🛡️/🤖 + último scan + `Switch monitor` + re-scan; "Agregar
  dominio"; ajustes de alertas email/Slack ([08-ranking-watchlists](../08-ranking-watchlists/spec.md)).
  Resultados de scans activos **privados** salvo `/r/{token}`. Empty: *"Agrega tu
  primer dominio para vigilarlo."*

## 8. Estados transversales, a11y, responsive, i18n (§F12)

- **Loading:** `ui/skeleton.tsx` (filas del leaderboard, reporte, histórico) — **no
  spinners**.
- **Empty:** reusa `components/common/empty-state.tsx` (watchlist, sitio sin scans).
- **Error → UI:** 422 inline (form), 404 página "no encontrado" (no confirma
  existencia), 410 copy de enlace caducado, 403 → toast; `partial` → banner
  "cobertura parcial".
- **Toasts:** `sonner` `<Toaster/>` en layout raíz; share/PDF/copy-link/errores.
- **a11y:** AA en claro y SOC; foco visible; `prefers-reduced-motion` desactiva
  count-up/pulse; severidad con **ícono+texto** (no solo color).
- **Responsive (un breakpoint `md`):** leaderboard tabla→cards; reporte 2-col→stack;
  theater 2 carriles→stack vertical (manda el feed de findings). Variante móvil
  obligatoria para Hall of Shame, Theater y Reporte.
- **i18n:** copys en `frontend/src/i18n/messages/es.json` (es-MX literal, no lorem;
  el `en.json` hermano vive en el mismo dir). Copy literal por pantalla **se toma de
  `product/design-prompt.md`** (§3). Claves nuevas bajo namespaces `Leaderboard`,
  `ScanForm`, `Theater`, `Report`, `Auth`, `Watchlist`.

## 9. Suite de tests — `frontend/` (vitest + testing-library) y `backend/tests/`

Frontend: **vitest + @testing-library/react** para lógica de UI pura (sin red);
los flujos E2E reales (404/410/idempotencia HTTP) los cubre
[12-api](../12-api/plan.md) §8 en `backend/tests/api/`. Aquí se prueba **render,
estado y la mecánica de cliente** (reducer SSE, normalización de URL, gate).

| Archivo | Capa | Asserts |
|---|---|---|
| `application/owliver/lib/url.test.ts` | unit puro | `normalizeUrl` prefija `https://`; `extractHost` ok; `rejectPrivateHost` rechaza `localhost`/IP privada/host sin punto; acepta `sat.gob.mx` |
| `application/owliver/lib/grade.test.ts` | unit puro | `gradeColor('F')→var(--grade-f)`; mapeo A–F completo; no inventa grado fuera de rango |
| `application/owliver/stores/theater-store.test.ts` | unit (store) | reducer aplica `tool_start/end`, empuja `finding`, actualiza `score`; **descarta `seq<=lastSeq`** (replay idempotente); `done` marca terminal |
| `presentation/owliver/scan/attestation-gate.test.tsx` | componente | gate **oculto** en básico; visible en activo; submit **deshabilitado** sin checkbox; refuerzo rojo si host `.gob.mx`; términos abren Dialog |
| `presentation/owliver/scan/scan-form.test.tsx` | componente | nivel activo sin sesión → intención de redirect a `/login` con destino; preview de host; doble-submit deshabilitado |
| `presentation/owliver/leaderboard/ranking-table.test.tsx` | componente | filas en orden recibido (peores primero, **no reordena**); grado en mono+color escala; badge "IA detectada, sin auditar" cuando `detected_not_tested`; "cobertura parcial" en cap-C |
| `presentation/owliver/components/grade-badge.test.tsx` | componente | color por grado; render mono; accesible (texto, no solo color) |
| `presentation/owliver/report/finding-accordion.test.tsx` | componente | un panel por finding; `info` (peso 0) en conteo aparte; finding agéntico estrella resalta canary; filtros por severidad |
| `presentation/owliver/public-report/redacted-finding.test.tsx` | componente | exploit crudo **no** renderiza; estado candado "Oculto en el reporte público"; muestra impact/remediation |

> El consumo SSE end-to-end (replay real desde Postgres) se valida en
> [10-realtime-live-view](../10-realtime-live-view/spec.md); aquí se prueba el
> reducer con eventos sintéticos.

## 10. Secuencia de build

Mapea al carril **P4** del plan de 20h (§F15); trabaja contra **fixtures de los
stubs desde la hora 2**.

1. **Piel + deps (0–2):** tokens `--ow-*`/`--soc-*`/grades en `globals.css`;
   `npm i recharts sonner` + `shadcn add chart accordion sonner`; `(public)/layout.tsx`
   Owliver; mover login→`/login`, `/`→Hall of Shame stub; ampliar `proxy.ts`
   públicas; `<Toaster/>` en layout raíz; `grade-badge`/`severity-chip`/`status-badge`.
2. **Leaderboard + form/gate (2–8):** `/` RSC contra `GET /ranking` (fixtures) +
   filtros/cargar-más; `score-gauge` base; `scan-form` + `attestation-gate` →
   `POST /scans`. Tests de §9 (url, grade, gate, ranking).
3. **Reporte + público + login Google (8–14):** `/scans/[id]/report` (doble gauge +
   ejecutiva + `finding-accordion`); `/r/[token]` redactado (404/410); login Google
   cableado al gate de sesión. Tests de accordion/redacted.
4. **Live Theater (14–16):** `theater/*` + `use-scan-stream` replay-then-tail +
   `theater-store`; demo-level <90s; Plan B `<video>`/replay. Tests del store.
5. **Watchlist + acciones + wow (16–18):** `/watchlist` + monitor switch; PDF/share +
   toasts; histórico `/sites/[id]`; features wow que alcancen (Report Card OG → chat
   → replay cinematográfico).

**Núcleo que nunca se corta (§F15):** `form → scan → Finding[] → reporte` +
leaderboard gov + doble score + finding agéntico estrella. **Orden de recorte:**
Theater en vivo (→ Replay §F14-3 o video) → chat Owliver → PDF/share (→ reporte
in-app) → watchlist UI → Report Card.

Feature `implemented`/coverage>0 cuando las 4 superficies núcleo renderizan contra
fixtures, el BFF de cada una está montado y la suite de §9 pasa.

## 11. Decisiones y riesgos abiertos

1. **`/` se reescribe como Hall of Shame; login se mueve a `/login` (Google).**
   El form password del boilerplate (`src/app/page.tsx`) se retira — Owliver no usa
   password. Documentado para que un revisor no lo "restaure". (§F1 nota de identidad.)
2. **`recharts` + `sonner` NO estaban presentes** (verificado contra
   `frontend/package.json`; no hay `components/ui/chart.tsx`). La spec §F1 dice
   `recharts (^3.6.0, ya presente)` — ese dato es **incorrecto** y este plan lo
   override (ver §0.1): que nadie lo "restaure". Se añaden en la hora 0–2;
   `chart.tsx`/`accordion`/`sonner` se generan con `shadcn add`. Sin esto no hay
   gauges/acordeón/toasts.
3. **RSC directo con `serverHttp` para superficies anónimas** (`/`, `/r/[token]`,
   `/sites/[id]`) en vez de BFF `route.ts`: son server components, ya cruzan el
   límite servidor y no setean cookies → no necesitan ruta intermedia. Las **client
   islands** sí usan BFF. Cumple la regla (browser nunca pega al backend directo).
4. **SSE por `EventSource` + cookie, vía proxy `/api/v1/*`** (no por BFF `route.ts`):
   EventSource no admite headers custom; `withCredentials` lleva la cookie y
   `proxy.ts` añade `X-Api-Key`. El contrato del stream lo cierra
   [10-realtime-live-view](../10-realtime-live-view/spec.md); si exige
   `?stream_token=` efímero para privados, el hook lo soporta como query param.
5. **Modo SOC scoped (clase `.soc`), no tema global** — "claro de día, SOC de noche"
   conviven sin toggle de usuario; evita reflujo de todo el árbol de tema.
6. **El front no calcula nada autoritativo** (grado/score/`is_gov`/dedupe/redacción):
   los pinta tal cual de [12-api](../12-api/plan.md)/[07-scoring](../07-scoring/spec.md)/[09-reporting](../09-reporting/spec.md).
   `lib/grade.ts` solo elige color de display.
7. **`design-prompt.md` SÍ existe y es fuente de copy literal.** Vive en
   `product/design-prompt.md` y el link de la spec (`../../design-prompt.md`, §F2)
   resuelve correctamente. Es el **brief visual de alta fidelidad** con copy literal
   por pantalla ("claro de día, SOC de noche") — se **usa como fuente** junto a
   `PRODUCT.md`/`DESIGN.md`, **no** se sustituye. (Lo que **no** existe aún es el
   mirror `.impeccable/design.json` que cita `CLAUDE.md`; pendiente de generación vía
   `/impeccable`.)
8. **Tests de UI en vitest** (no presente aún como runner configurado): si el repo
   no trae vitest, se añade en la hora 0–2; los E2E HTTP reales quedan en
   `backend/tests/api/` ([12-api](../12-api/plan.md) §8), no se duplican aquí.
9. **Features wow §F14 recortables** — Report Card OG (`opengraph-image.tsx`), chat
   "Owliver te explica" (1 endpoint + UI) y Replay cinematográfico reusan datos que
   el backend ya produce; entran solo si §F4–§F7 están verdes.
