---
status: implemented
title: Owliver — Frontend Flows & Actions
description: Mapa de todos los flujos, pantallas y acciones del frontend (Next.js 15 App Router) — qué ve y qué hace el usuario, y a qué endpoint BFF/backend dispara cada acción.
---

# Owliver — Frontend Flows & Actions

Documento de referencia de **todos los flujos del frontend**: cada pantalla, las
acciones que el usuario puede ejecutar, y el endpoint BFF (`/api/*`) + backend
(`/v1/*`) que cada acción dispara.

El frontend tiene **dos superficies**:

1. **Producto Owliver** (motor de pentest) — público (leaderboard, formulario,
   theater en vivo, reportes) + protegido (watchlist/monitoreo).
2. **Fundación SaaS** (boilerplate) — autenticación, tenants, miembros, roles,
   settings, API keys, perfil.

> Fuentes: specs en `product/spec.md` + `product/features/` (el QUÉ) y el código
> en `frontend/src/` (el CÓMO). Donde el código aún no implementa lo que el spec
> describe, se anota como **(pendiente)** o **(stub)**.

---

## 0. Arquitectura transversal (vale para todos los flujos)

### Patrón BFF obligatorio
Ningún código de navegador llama al backend directamente. Todo pasa por:

```
Client component  →  fetch("/api/<feature>/...")        (mismo origen, relativo)
                  →  BFF route handler (src/app/api/**/route.ts, server-side)
                  →  serverHttp → backend /v1/*          (lee env server-only, mete X-Api-Key)
```

Para tráfico ya autenticado, `authHttp`/`localHttp` (axios `baseURL: "/api"`)
pegan al **proxy/middleware** (`src/proxy.ts`), que reescribe `/api/v1/*` →
`BACKEND_API_HOST` y adjunta `X-Api-Key`.

- **Clientes HTTP** (`src/infrastructure/http/client.ts`):
  - `serverHttp` — solo server, directo a backend `/v1`. Lo usan los route handlers.
  - `localHttp` / `authHttp` — cliente, vía `/api` (BFF/proxy), con interceptores de auth.

### Sesión, cookies y refresh
- **Cookies HttpOnly** (`src/constants.ts`):
  | Cookie | Nombre | Vida | Propósito |
  |---|---|---|---|
  | Access token | `___AT5___` | 10 min | JWT para llamadas API |
  | Refresh token | `___RT5___` | 7 días | Largo, rotable |
  | Refresh attempts | `___RA5___` | 60 s | Detección de bucle (3 → wipe) |
  | Pending destination | `___OWL_NEXT___` | 10 min | Redirect post-OAuth |
- **Session store** (Zustand `persist`, `src/application/contexts/session-store.ts`):
  guarda `user`, `tenant`, `tenantRole`, `accessToken` (en memoria, no persistido).
  `isAuthenticated()` = user + tenant + accessToken presentes.
- **Auto-refresh**: interceptor en `localHttp`/`authHttp`. Ante `401` /
  `auth.NotAuthenticated`, deduplica, `POST /api/auth/refresh`, actualiza store y
  reintenta. Si falla: `clearSession()` + redirect a `/login`.

### Gating de rutas (`src/proxy.ts` middleware)
- **Públicas exactas**: `/`, `/register`, `/reset-password`, `/login`, `/scan`.
- **Prefijos públicos** (anónimo / token): `/invitations/`, `/reset-password/`,
  `/login/`, `/scans/`, `/sites/`, `/r/`.
- **Auth-entry** (`/login`, `/register`, `/reset-password`): si ya hay sesión →
  redirect a `/dashboard`.
- **Protegidas** (todo lo demás): sin refresh-cookie → redirect a `/login`.
- El **layout protegido** (`(protected)/layout.tsx`) revalida server-side
  (`refreshServerSession()`): sin sesión → `/login`; con sesión pero sin tenant →
  `/unassigned`.

### SSE (live view)
El theater usa un helper `subscribeSSE()` basado en `fetch` (no `EventSource`
nativo) con `credentials: "same-origin"` (auth por cookie). Patrón
**replay-then-tail**: reproduce `scan_events` persistidos (`?since_seq=`) y luego
hace tail. Cliente deduplica por `seq`.

### Fixtures / modo demo
Cada endpoint GET del producto tiene **fallback a fixture** (ranking, scan,
report, site, stream). La página renderiza sin backend; el stream sintetiza una
cadencia realista para que el theater corra completo en demo.

### i18n y diseño
- **Español (es-MX)** primario; copy literal.
- **Dos modos visuales**: *claro/institucional* (leaderboard, formulario,
  reportes) y *SOC/war-room oscuro* (theater en vivo).
- Mascota 🦉: idle (dormida) → running (alerta) → found (ojos ámbar).

---

## 1. Mapa de rutas

| Ruta | Acceso | Pantalla |
|---|---|---|
| `/` | público | ranking (ranking `.gob.mx`) |
| `/scan` | público | Formulario de escaneo + attestation gate |
| `/scans/[id]` | público* | Live pentest theater (SSE) |
| `/scans/[id]/report` | público* | Reporte interactivo (ejecutivo + técnico) |
| `/sites/[id]` | público | Histórico del sitio |
| `/r/[token]` | público | Reporte compartido (exploits redactados) |
| `/watchlist` | protegido | Watchlist + monitoreo + alertas |
| `/login` | público | Login con Google |
| `/login/callback` | público | Callback OAuth |
| `/register` | público | Registro (stub) |
| `/reset-password` | público | Solicitar reset de contraseña |
| `/reset-password/[token]` | público | Confirmar nueva contraseña |
| `/invitations/[token]` | público | Aceptar invitación |
| `/unassigned` | público (redirigido) | Usuario sin tenant |
| `/dashboard` | protegido | Dashboard (perm `dashboard.view`) |
| `/members` | protegido | Miembros (perm `tenant_users.view`) |
| `/roles` | protegido | Roles (perm `tenant_roles.view`) |
| `/settings` | protegido | Ajustes del tenant (perm `tenant_settings.update`) |
| `/api-keys` | protegido | API keys (perm `tenant_settings.update`) |
| `/profile` | protegido | Perfil (sin guard) |
| `/forbidden` | protegido | Permiso denegado |

\* *Público si el scan es básico/pasivo; los scans activos/privados devuelven 404
a quien no es dueño (no se confirma su existencia).*

---

## 2. Producto Owliver — flujos públicos

### F1 · Ranking (`/`)
**Actor:** visitante anónimo · **Componente:** `(public)/(owliver)/page.tsx` (RSC)
· **Datos:** `GET /api/owliver/ranking` → `GET /v1/ranking?country=mx`
(cursor-paginado, fallback `rankingFixture`).

**Qué ve:** hero ("El Estado bajo la lupa" / *"¿Qué tan segura es la IA del
gobierno?"*) + contador de sitios auditados/reprobados; tabla ordenada **worst-first**
(`ORDER BY overall_grade ASC, penalty_raw DESC`). Cada fila: posición + **grado
A–F** (mono, color-escalado), dependencia + hostname, **doble gauge** 🛡️ web vs
🤖 agéntico, badges *"IA detectada, sin auditar"* / *"cobertura parcial"*, trend
▲▼, fecha de último scan. Disclaimer legal (*"Datos 100% pasivos y públicos"*).

**Acciones:**
- **Click en una fila** → navega a `/sites/[id]` (histórico).
- **CTA "Auditar un sitio / Audita cualquier URL →"** → abre `ScanFormDialog`
  (modal con `ScanForm`) o navega a `/scan`.
- **"Cargar más"** → paginación cliente (no re-ordena; el orden del server es la
  autoridad).
- **Filtros** por grado / fuente (web·agéntico) / país.

**Estados:** skeleton (carga), vacío (teórico — fixtures), animación count-up de
grados, filas F pulsan rojo, hover revela top finding.

---

### F2 · Formulario de escaneo + Attestation Gate (`/scan`)
**Actor:** anónimo (básico) o autenticado (intermedio/avanzado) · **Componente:**
`(public)/(owliver)/scan/page.tsx` → `presentation/owliver/scan/scan-form.tsx` ·
**Hook:** `useCreateScan()` · **Datos:** `POST /api/owliver/scans` → `POST /v1/scans`.

**Qué ve:** input de URL grande con validación inline (normaliza a `https://`,
muestra host detectado *"Vas a escanear: sat.gob.mx"*, rechaza IPs privadas /
localhost / hostnames sin punto) + **3 radio-cards de nivel**:
- 🟢 **Básico** (default) — *"Pasivo, no intrusivo, anónimo, sin permisos"*.
- 🟡 **Intermedio** — *"Activo suave, rate-limited"* (requiere autorización).
- 🔴 **Avanzado** — *"Explotación, requiere autorización"*.

**Attestation Gate (`AttestationGate`)** — solo aparece en intermedio/avanzado:
- Aviso rojo: *"Vas a lanzar pruebas intrusivas contra **{host}**; hacerlo sin
  autorización es ilegal."*
- **Checkbox obligatorio**: *"Declaro tener autorización para auditar este
  dominio."* + link "Ver términos" (dialog).
- **Refuerzo `.gob.mx`**: copy rojo recordando responsabilidad legal.
- Si nivel activo y **sin sesión** → redirect a `/login` guardando destino pendiente.

**Acciones:**
1. **Escribir URL** → normalización vía `extractHost()`.
2. **Elegir nivel** → toggle de visibilidad del gate.
3. **Atestiguar** (niveles activos) → habilita el submit.
4. **Submit** (`useCreateScan`): `POST /api/owliver/scans { url, level, authorized }`
   → respuesta `{ scanId }` (201 nuevo / **200 idempotente** si ya existe un scan
   `(site_id, level)` en `queued|running`). Éxito → `router.push("/scans/[id]")`.

**Errores (mapeados a es-MX, inline):** `422` atestación/URL inválida · `429`
rate-limit (incluye `Retry-After`) · `403` prohibido. Botón deshabilitado mientras
`pending` o nivel activo sin atestar (evita doble submit).

---

### F3 · Live Pentest Theater (`/scans/[id]`) — la pieza central
**Actor:** anónimo (básico) o dueño autenticado (privado) · **Page:**
`(public)/(owliver)/scans/[id]/page.tsx` (RSC shell) → `presentation/owliver/theater/theater-view.tsx`
(cliente) · **Hooks:** `useScanStream()`, `useTheaterStore()` (Zustand),
`useCancelScan()`, `useElapsed()`.

**Datos / endpoints:**
- `GET /api/owliver/scans/[id]` → `GET /v1/scans/{id}` — estado inicial (seed).
- `GET /api/owliver/scans/[id]/stream` → `GET /v1/scans/{id}/stream` — **SSE**
  (replay-then-tail; `?since_seq=` cursor; scans privados pasan `?stream_token=`).
- `POST /api/owliver/scans/[id]/cancel` → `POST /v1/scans/{id}/cancel`.

**Qué ve (UI oscura war-room, Geist Mono, scanlines):** header con host + nivel +
**timer** (<90 s) + **grado-en-construcción**; barra de progreso 0–100 con fase
actual (*"Detectando tecnologías…"*, *"Sondeando chatbot…"*); **dos carriles de
agente**:
- 🛡️ **OWASP Scanner (Sonnet)** — chips de tools (`nuclei`, `zap`, `testssl`,
  `nikto`, `sqlmap`…): `tool_start` → glow ámbar; `tool_end` → ✓ verde / ✗ rojo.
- 🤖 **Agentic Surface Auditor (Sonnet)** — detección → inventario → sondas;
  muestra el chatbot detectado (vendor/modelo) y cada probe.

Feed central de **findings en vivo** (entran con fade+slide, severidad
color-codeada, críticos pulsan rojo) + **gauges parciales** 🛡️/🤖 que animan con
eventos `score` + log monospace tipo terminal.

**Eventos SSE** (formato `event: <type>\nid: <seq>\ndata: <JSON>`):
`agent_status`, `tool_start`, `tool_end`, `score`, `finding`, `done`, `error`. El
store los aplica **idempotente** (descarta `seq <= lastSeq`); la UI se suscribe a
slices (`runStatus`, `progress`, `lanes`, `findings`, `log`).

**Acciones:**
- **Cancelar** → `useCancelScan().mutate()` → `POST .../cancel`; backend emite
  `done { outcome: 'cancelled' }`; la UI muestra estado terminal limpio.
- **Recargar la página** → replay desde Postgres repinta todo (sin pantalla en
  blanco); el cursor `since_seq` salta lo ya visto.
- Al completar (`done { outcome:'success' }`) aparece **"Ver reporte completo →"**
  → `/scans/[id]/report`.

**Estados (`runStatus`):** `idle` (en cola, búho dormido) · `running` · `done` ·
`cancelled` · `error` (banner + `tools_status` para debug) · *"cobertura parcial"*
si algún scanner falló. Scan privado sin permiso → `TheaterNotFound` (neutral, no
confirma existencia). **Plan B:** si SSE falla, video de respaldo de ~90 s.

---

### F4 · Reporte interactivo (`/scans/[id]/report`)
**Actor:** dueño (privado) o cualquiera (público pasivo) · **Page:**
`(public)/(owliver)/scans/[id]/report/page.tsx` (RSC + islas cliente) ·
**Componentes:** `ReportExecutive`, `ReportTechnical` + `ReportAccordion`,
`ReportActions` · **Datos:** `fetchReport(scanId)` → backend
`GET /v1/scans/{id}/report` (fallback fixture redactado; 404 → `notFound()`).

**Capa 1 — Ejecutiva:** grado **A–F** grande (count-up, color) + **dos gauges
semicirculares** (recharts `RadialBarChart`, `endAngle=180`) 🛡️ web / 🤖 agéntico;
párrafo **"Owliver te explica"** (generado por Opus, lenguaje llano + impacto de
negocio); **Top 3 riesgos** priorizados; **inventario de superficie agéntica**
(chatbots detectados: vendor, modelo o *"modelo no expuesto"*); badges
*"cobertura parcial"* / *"IA detectada, sin auditar"*.

**Capa 2 — Técnica:** **accordion** (un panel por finding). Cabecera: chip de
**severidad** + categoría OWASP/LLM + título. Cuerpo: `evidence` (payload +
req/resp + screenshot servido de `/data/scans/{id}/{n}.png`), `impact`,
`remediation`, `references` (CWE/OWASP), `confidence`. **Finding estrella
agéntico:** fuga de system-prompt con **canary token** como prueba
(`{payload, respuesta_cruda, token_filtrado}` resaltado en monospace). Filtros por
severidad/fuente/categoría. **Tendencia histórica** si hay scans previos
(`dedupe_key` + `first_seen`/`last_seen`).

**Acciones:**
- **Compartir** (`ReportActions` → `useShareReport`): `POST /api/owliver/scans/[id]/share`
  → `{ token, expiresAt }` (TTL 7 días) → arma link absoluto `/r/{token}` →
  `navigator.clipboard.writeText(url)` → estado *"Enlace copiado · válido 7 días"*.
- **Exportar PDF** → link `href=/api/v1/scans/{id}/report.pdf` (nueva pestaña;
  Playwright/WeasyPrint, screenshots embebidos).
- **Expandir finding** → accordion (cliente, sin request).
- **Volver al scan** → `/scans/[id]` · **Ver histórico** → `/sites/[id]`.

**Estado de share:** `idle | loading | done(url) | error(message)`.

---

### F5 · Reporte público compartido (`/r/[token]`)
**Actor:** cualquiera con el link (viral) · **Page:** `(public)/(owliver)/r/[token]/page.tsx`
(RSC, sin login) · **Datos:** `GET /api/r/[token]`.

**Qué ve:** **capa ejecutiva completa** (grado, gauges, "Owliver te explica", top
3, inventario agéntico) + **capa técnica con exploits REDACTADOS**: muestra
severidad, categoría, `impact`, `remediation`, `references`, `confidence`; **oculta**
payload crudo / req-resp / system-prompt filtrado (candado + *"Oculto en el reporte
público"*). **Regla de seguridad, no preferencia de UI:** el link público nunca
filtra exploits.

**Estados:** token inexistente → **404** (`notFound`) · token expirado/revocado
→ **410** (*"Este enlace expiró · Los enlaces caducan a los 7 días"*) · válido →
reporte redactado. **Acciones:** "Ir al inicio →" → `/`.

> Opcional (§F14): **Report Card** OG-image (`next/og`) con grado + 🛡️/🤖 +
> dependencia + **F** en rojo grande → gancho viral al pegarlo en X/WhatsApp.

---

### F6 · Histórico del sitio (`/sites/[id]`)
**Actor:** anónimo · **Page:** `(public)/(owliver)/sites/[id]/page.tsx` · **Datos:**
`loadSite(id)` → `GET /api/owliver/sites/[id]` → `GET /v1/sites/{id}` (fallback
`siteFixture`; 404 → `notFound()`).

**Qué ve:** resumen del último scan (grado + 2 gauges) + superficie agéntica
detectada + **timeline de grados** y mini line-chart de tendencia (`GradeTrend`) +
resumen new-vs-resolved derivado de los últimos 2 scans (`deriveChanges`: deltas
web/agéntico + transición de grado, p.ej. "B → A") + **lista de scans** (reverse
cronológico) con grado/fecha y link a `/scans/[id]/report`.

**Acciones:** click en un scan → `/scans/[id]/report`. **Estados:** vacío
(*"Aún no hay escaneos"*) · 1 vs varios scans.

---

## 3. Producto Owliver — flujos protegidos

### F7 · Watchlist + Monitoreo (`/watchlist`)
**Actor:** usuario autenticado · **Layout:** `(protected)/(owliver)/layout.tsx` ·
**Page:** `(protected)/(owliver)/watchlist/page.tsx` · **Hooks:** `useWatchlist()`,
`useAddWatchlist()`, `useToggleMonitor()`, `useRemoveWatchlist()`, `useAlertPrefs()`.

**Endpoints BFF:** `GET·POST /api/owliver/watchlist`,
`PATCH·DELETE /api/owliver/watchlist/[id]`, `GET·PATCH /api/owliver/me/alerts`.

**Qué ve:** header + **form "Agregar dominio"** (`AddDomainForm`: input URL +
checkbox *"Monitor automáticamente"* + submit) + filas (`WatchlistRowItem`,
keyed por `id` de fila, **no** por `siteId`): host, grado más reciente, **switch
de monitor**, link *"Re-escanear"*, *"Ver histórico"*, botón borrar. Panel lateral
de **preferencias de alerta**. Estados vacío / skeleton (3 filas).

**Acciones:**
1. **Agregar dominio** → `useAddWatchlist().mutate({ url, monitor })` →
   `POST /api/owliver/watchlist`; `onSuccess` invalida `owliverKeys.watchlist()`.
2. **Toggle monitor** → `useToggleMonitor().mutate({ id, monitor })` →
   `PATCH /api/owliver/watchlist/[id] { monitor }` (incluye al sitio en el scheduler).
3. **Re-escanear** → navega a `/scan?url=<host>` (form con URL pre-llenada).
4. **Borrar** → `useRemoveWatchlist().mutate(id)` → `DELETE /api/owliver/watchlist/[id]`.
5. **Preferencias de alerta** → `GET·PATCH /api/owliver/me/alerts` (email + Slack
   webhook). *(Alertas in-app fuera de MVP.)*

> **Monitoreo automático (background, sin UI):** un cron SAQ re-encola sitios
> `monitor=true` + seeds gov (pasivo). Idempotente por índice único parcial
> `scans(site_id, level) WHERE status IN ('queued','running')`. Dispara alerta
> (Resend / Slack) si **bajó el grado** o aparece un **finding `critical` nuevo**
> (vía `dedupe_key` + `first_seen`). Findings que dejan de aparecer → `fixed`
> (silencioso). Resultados de watchlist son **privados** (no entran al ranking).

---

## 4. Autenticación (fundación SaaS)

### F8 · Login con Google (OAuth) — `/login`
**Page:** `(public)/login/page.tsx` (card "Entrar con Google" + error oauth/config/exchange).
Flujo de 3 pasos:
1. **Inicio** — link a `GET /api/auth/google/start?next=<destino>`
   (`api/auth/google/start/route.ts`): valida `clientId`/`redirectUri`, valida que
   `?next=` sea ruta relativa same-site, setea cookie `___OWL_NEXT___` (10 min),
   redirige a `accounts.google.com/o/oauth2/v2/auth` (scopes `openid email profile`).
2. **Callback** — `(public)/login/callback/page.tsx`: Google redirige con `?code=`;
   sin code/`?error=` → `/login?error=oauth`; con code → `POST /api/auth/google-login { code }`.
3. **Exchange** — `api/auth/google-login/route.ts`: backend `googleLogin(code)` →
   `{ session, user, tenant, tenantRole }`; **setea `___AT5___` + `___RT5___`**,
   limpia `___RA5___` y `___OWL_NEXT___`; resuelve redirect
   (`body.next` → cookie `___OWL_NEXT___` → `/watchlist`). Cliente: `setSession(...)`
   y navega al destino.

### F9 · Registro — `/register` *(stub)*
`(public)/register/page.tsx`: form (nombre, email, password, confirmar) con
**validación solo cliente** (`console.log`, sin backend aún). "Continuar con
Google" sin implementar.

### F10 · Reset de contraseña
- **Solicitar** — `/reset-password` (`(public)/reset-password/page.tsx`): input
  email → `POST /api/auth/reset-password { email }` → `/v1/auth/reset-password`
  (backend envía email con token) → mensaje de éxito.
- **Confirmar** — `/reset-password/[token]`: password (≥8) + confirmar →
  `POST /api/auth/reset-password/confirm { token, password }`. Error
  `common.InvalidOrExpiredToken`; éxito → login.

### F11 · Aceptar invitación — `/invitations/[token]`
`(public)/invitations/[token]/page.tsx` (server, `cache: no-store`) consulta
`/v1/invitations/{token}`. Estados: `ok` (muestra `AcceptInvitationForm`) ·
`already_accepted` · `expired` · `not_found`. **Form:** nombre (req), apellido
(opt), y si `requiresPassword` → password (≥8) + confirmar. **Submit** →
`POST /api/auth/invitations/{token}/accept { firstName, lastName?, password? }` →
backend devuelve sesión; **setea las 3 cookies**; redirect a `/dashboard`.

### F12 · Logout y Refresh (transversales)
- **Logout** — `POST /api/auth/logout`: lee refresh-cookie, llama backend
  `logout()`, **limpia `___AT5___` + `___RT5___`**; cliente `clearSession()` →
  `/login` o `/`. Invocado desde `/forbidden`, `/unassigned` y en fallo de refresh.
- **Refresh** — `POST /api/auth/refresh`: valida refresh-cookie (sin ella → 401
  `invalidRefreshToken`), backend `refresh()` → **rota las 3 cookies**, devuelve
  `{ accessToken, data:{ user, tenant, tenantRole } }`. Llamado por el interceptor
  ante 401 (dedupe + retry; fallo → `clearSession()` + `/login`).

---

## 5. Administración de tenant (boilerplate protegido)

Todas envueltas en `(protected)/layout.tsx` (revalida sesión/tenant server-side) +
`PermissionGuard` cliente (`presentation/common/permission-guard.tsx`) que lee
`usePermissions()` (`tenantRole.permissions[]` + `isOwner`); sin permiso →
`router.replace("/forbidden")`. Todas montan `<AppShell>` (navegación).

| Ruta | Permiso | Vista | Acciones |
|---|---|---|---|
| `/dashboard` | `dashboard.view` | `DashboardView` | resumen |
| `/members` | `tenant_users.view` | `MembersView` | invitar (`InviteUserDialog`), editar rol (`EditMemberDialog`), quitar miembro, ver invitaciones pendientes |
| `/roles` | `tenant_roles.view` | `RolesView` | crear/editar/borrar rol (`CreateRoleDialog`, `EditRoleDialog`), seleccionar permisos (`PermissionSelector`) |
| `/settings` | `tenant_settings.update` | `SettingsView` | actualizar settings del tenant |
| `/api-keys` | `tenant_settings.update` | `ApiKeysView` | listar/crear/regenerar/borrar API keys |
| `/profile` | — (sin guard) | `ProfileView` | actualizar perfil |
| `/forbidden` | — | error card | "Go Home" → `/dashboard`; "Sign Out" → logout |
| `/unassigned` | — | `UnassignedView` | "Email Support" (`mailto:`); "Logout" → `/` |

Hooks CRUD (TanStack Query) en `application/hooks/queries/`:
`api-keys.ts`, `members.ts`, `roles.ts`, `settings.ts`.

---

## 6. Estados, grados y errores (referencia transversal)

### Estados de scan
`queued` → `running` → `done` | `cancelled` | `error`. Variante *"cobertura
parcial"* cuando un scanner falla (grado **capado a C**).

### Superficie agéntica (`agentic_status`)
`detected_not_tested` (badge *"IA detectada, sin auditar"*) · `tested_clean` ·
`tested_vulnerable` (🚨 finding estrella + canary).

### Grados A–F (color)
| Grado | Score | Color (oklch) |
|---|---|---|
| A | ≥90 | verde `0.72 0.16 150` |
| B | ≥80 | lima `0.75 0.15 130` |
| C | ≥70 | ámbar `0.80 0.14 90` (cap-parcial) |
| D | ≥60 | naranja `0.72 0.16 55` |
| E | ≥40 | rojo-naranja `0.66 0.19 35` |
| F | <40 | rojo `0.58 0.22 25` (reprobado) |

Regla: **A nunca se muestra con cobertura parcial** (se capa a C, etiquetado).

### Códigos de error → UI
| Código | Escenario | Trato |
|---|---|---|
| 422 | atestación faltante / URL inválida | error inline en el form |
| 404 | scan inexistente / sin permiso (privado) | "no encontrado" (no confirma existencia) |
| 410 | token expirado/revocado (reporte público) | página *"Este enlace expiró"* |
| 403 | permiso denegado | banner/toast |
| 429 | rate-limit (5 scans/h) | aviso + `Retry-After` |

---

## 7. Referencia de endpoints BFF

| Ruta BFF | Método | Backend | Devuelve |
|---|---|---|---|
| `/api/owliver/ranking` | GET | `GET /v1/ranking?country=mx` | filas paginadas |
| `/api/owliver/scans` | POST | `POST /v1/scans` | `{ scanId }` (201/200) |
| `/api/owliver/scans/[id]` | GET | `GET /v1/scans/{id}` | estado del scan |
| `/api/owliver/scans/[id]/stream` | GET | `GET /v1/scans/{id}/stream` | **SSE** (replay-then-tail) |
| `/api/owliver/scans/[id]/cancel` | POST | `POST /v1/scans/{id}/cancel` | ok/err |
| `/api/owliver/scans/[id]/share` | POST | `POST /v1/scans/{id}/share` | `{ token, expiresAt }` |
| `/api/owliver/scans/[id]/findings` | GET | `GET /v1/scans/{id}/findings` | `Finding[]` |
| `/api/owliver/sites/[id]` | GET | `GET /v1/sites/{id}` | histórico del sitio |
| `/api/owliver/watchlist` | GET·POST | `/v1/watchlist` | filas / fila creada |
| `/api/owliver/watchlist/[id]` | PATCH·DELETE | `/v1/watchlist/{id}` | fila / ok |
| `/api/owliver/me/alerts` | GET·PATCH | `/v1/me/alerts` | prefs de alerta |
| `/api/r/[token]` | GET | (endpoint redactado) | reporte redactado |
| `/api/auth/google/start` | GET | — (redirect a Google) | 302 |
| `/api/auth/google-login` | POST | `POST /v1/auth/google-login` | sesión + cookies |
| `/api/auth/login` | POST | `POST /v1/auth/login` | sesión + cookies |
| `/api/auth/logout` | POST | `POST /v1/auth/logout` | limpia cookies |
| `/api/auth/refresh` | POST | `POST /v1/auth/refresh` | rota cookies + `accessToken` |
| `/api/auth/reset-password` | POST | `POST /v1/auth/reset-password` | ok |
| `/api/auth/reset-password/confirm` | POST | `POST /v1/auth/reset-password/confirm` | ok |
| `/api/auth/invitations/[token]/accept` | POST | `POST /v1/invitations/{token}/accept` | sesión + cookies |

**Headers que inyecta el BFF/proxy:** `X-Api-Key` (siempre), `Authorization:
Bearer <cookie>` (si hay sesión), `X-Tenant-Slug` (desde el store). Sobre el
stream: `X-Accel-Buffering: no`, `Content-Encoding: identity`, `Cache-Control:
no-cache, no-transform` (para que el SSE no se buffee/comprima).

---

## 8. Notas de implementación vs. spec

- **Registro (`/register`)** es **stub**: validación solo cliente, sin backend.
  Login real = Google OAuth.
- **Alertas in-app** están **fuera de MVP**; las prefs (email/Slack) sí existen en
  `/watchlist`.
- **Monitoreo automático** es trabajo de background (cron SAQ), no una acción de
  UI; se documenta aquí por completitud.
- Wow opcionales (§F14) — **Report Card** OG-image, chat "Owliver te explica",
  **replay/timeline** del escaneo — son recortables; verificar su estado real
  antes de prometerlos en demo.
- Toda página GET del producto tiene **fallback a fixture** para correr la demo sin
  backend.
