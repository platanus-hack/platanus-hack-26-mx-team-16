---
status: implemented
title: Owliver — Flujos de navegación principales (Gherkin / E2E)
description: Especificación en Gherkin de los flujos de navegación principales del frontend de Owliver, pensada para generar pruebas E2E automatizadas con Playwright o Cypress. Cada feature trae escenarios + una tabla de selectores reales (role/text/label) y notas de testabilidad.
---

# Owliver — Flujos de navegación principales (Gherkin)

Este documento describe, en **Gherkin**, los flujos de navegación que un usuario
puede recorrer en el frontend (Next.js 15 App Router). Está escrito para que un
equipo (o un agente) lo traduzca **directamente a pruebas E2E** con **Playwright**
o **Cypress**.

> Los datos (rutas, copy, selectores, validaciones, transiciones) se extrajeron
> leyendo el código real de `frontend/src/`. Donde el código difiere de
> `product/flows.md`, **manda el código** y se anota como **DISCREPANCIA**.

## Cómo leer este documento

- **Keywords en inglés** (`Feature`, `Background`, `Scenario`, `Scenario Outline`,
  `Given/When/Then/And/But`), **texto y aserciones en español** (es-MX), porque el
  copy de la UI es español. Es el formato más compatible con
  `@cucumber/cucumber` + Playwright y con `cypress-cucumber-preprocessor`.
  Si prefieres keywords en español, antepón `# language: es` a cada `.feature` y
  traduce `Feature→Característica`, `Scenario→Escenario`, `Given→Dado`,
  `When→Cuando`, `Then→Entonces`, `And→Y`.
- Cada `Feature` trae: bloque ```gherkin``` + **Tabla de selectores** (Playwright;
  para Cypress usa `cy.findByRole(...)` de `@testing-library/cypress` o el
  equivalente) + **Notas de testabilidad**.
- Los selectores usan la convención Playwright `getByRole/getByText/getByLabel/getByPlaceholder`.

## Glosario de tags

| Tag | Significado |
|---|---|
| `@smoke` | Camino crítico mínimo para humo/CI rápido |
| `@public` | Accesible sin sesión |
| `@auth` | Autenticación / sesión |
| `@protected` | Requiere sesión (+ tenant) |
| `@scan` `@theater` `@report` `@share` | Producto Owliver (motor de pentest) |
| `@ranking` `@watchlist` | Superficies gov ranking / monitoreo |
| `@admin` | Boilerplate SaaS (members/roles/settings/api-keys) |
| `@a11y` | Depende de roles/landmarks accesibles |
| `@redaction` | Regla de seguridad (no filtrar evidencia en links públicos) |
| `@stub` | Pantalla NO cableada al backend (no se puede aseverar éxito) |
| `@negative` | Validación / error / edge case |

---

## Mapa de rutas (corregido contra el código)

| Ruta | Acceso | Pantalla | Notas |
|---|---|---|---|
| `/` | público | **Landing marketing** (`ComoFuncionaView`) | NO es el ranking. Hero "Audita tu web…", FAQ, pricing |
| `/scan` | público | Form de escaneo + attestation gate | acepta `?url=<host>` |
| `/scans` | público\* | "Mis escaneos" (historial) | datos por fixture; link de nav sólo con sesión |
| `/scans/[id]` | público\* / token | **Live Pentest Theater** (SSE) | 404 → `TheaterNotFound` |
| `/scans/[id]/report` | público\* | Reporte ejecutivo + técnico | 404 → `not-found.tsx` propio |
| `/r/[token]` | público (token) | Reporte público **redactado** | 410 expirado; 404 → not-found raíz |
| `/sites/[id]` | público | Histórico del sitio | **no hay índice `/sites`** |
| `/watch` | **protegido** | **Ranking `.gob.mx`** | requiere sesión + tenant |
| `/watcher` | protegido | **Watchlist / monitoreo (canónico)** | destino de TopNav "Monitoreo" |
| `/watchlist` | protegido | — | `redirect()` permanente → `/watcher` |
| `/login` | público (auth-entry) | Login email+contraseña **y** Google | con sesión → `/dashboard` |
| `/login/callback` | público | Callback OAuth (auto-POST `?code`) | |
| `/register` | público (auth-entry) | Registro **(STUB)** | sin backend, sólo `console.log` |
| `/reset-password` | público (auth-entry) | Solicitar reset | real |
| `/reset-password/[token]` | público | Confirmar nueva contraseña | real |
| `/invitations/[token]` | público | Aceptar invitación | real |
| `/unassigned` | autenticado sin tenant | Crear organización | gateado por su propio server check |
| `/dashboard` | protegido `dashboard.view` | Dashboard | |
| `/members` | protegido `tenant_users.view` | Miembros | |
| `/roles` | protegido `tenant_roles.view` | Roles | |
| `/settings` | protegido `tenant_settings.update` | Ajustes del tenant | |
| `/settings/notifications` | protegido (sin guard) | Notificaciones (alert prefs) | |
| `/api-keys` | protegido `tenant_settings.update` | API Keys | |
| `/profile` | protegido (sin guard) | Perfil | |
| `/forbidden` | protegido (destino de guard) | Pantalla 403 | |

\* *Público por ruta, pero el backend devuelve 404 (sin confirmar existencia) para
scans privados/inexistentes.*

---

## Notas globales de testabilidad (leer antes de automatizar)

1. **Determinismo offline por fixtures.** Cada GET del producto degrada a un
   **fixture** si el backend no responde: ranking, historial de scans, scan,
   stream SSE, report, public report, site, watchlist y alert prefs. Las páginas
   **renderizan sin backend** y el **theater corre completo** (el stream BFF
   sintetiza eventos en un timer: lead-in ~350 ms, ~650 ms/evento, ~400 ms para
   `done`), avanzando solo a estado terminal en pocos segundos. → Puedes correr
   E2E del *happy path* **sin worker**. ⚠️ Para probar 404/410/429/403 reales
   **debes** mockear el BFF/backend con esos status (el BFF sólo reenvía ciertos
   códigos; lo demás cae al fixture).

2. **Deep-links deterministas (fixture de historial).**
   `frontend/src/application/owliver/fixtures/scan-history.ts`:
   - corriendo → `scan-salud-running-0007` (→ theater `/scans/{id}`)
   - en cola → `scan-mitienda-queued-0009`
   - fallido → `scan-sat-failed-0040`
   - terminados (→ `/scans/{id}/report`) → p. ej. `scan-tesoreria-0021`, `scan-imss-0062`
   - scan del theater/hero → `HERO_SCAN_ID` (también el id que devuelve el fallback de "crear scan").

3. **Sin `data-testid`** en la app, con **una única excepción**:
   `data-testid="canary"` en `report/finding-accordion.tsx` (token canario; sólo
   en el **reporte completo**, nunca en `/r/[token]`). Usa selectores
   **role/text/label**. Hooks estables disponibles:
   `header[data-slot="top-nav"]`, `footer[data-slot="owliver-footer"]`,
   `[data-slot="attestation-gate"]`, `[data-slot="agent-lane"][data-lane]`,
   `[data-slot="tool-chip"][data-tool][data-state]`,
   `[data-slot="finding-feed-item"][data-severity]`,
   `[data-slot="scan-status-glyph"|"scan-status-pill"][data-status]`, y en filas de
   ranking/historial `data-grade=<A–F>`.

4. **Sesión / cookies (autenticación en E2E).** Cookies **HttpOnly** (no legibles
   por `document.cookie`): `___AT5___` (access, 10 min), `___RT5___` (refresh, 7 d),
   `___RA5___` (intentos, 60 s). El gating real lo decide la cookie `___RT5___` +
   `refreshServerSession()` server-side, **no** el store de cliente. Para rutas
   protegidas (`/watch`, `/watcher`, `/dashboard`, …): corre el login real
   (`POST /api/auth/login`) contra un backend sembrado, **o** inyecta `___RT5___`
   con `context.addCookies(...)`. Crea un helper `loginAsUser()` y reúsalo en los
   `Background`.

5. **Stubs/discrepancias clave** (no aseverar éxito donde no existe):
   - `/register` es **STUB**: sólo valida en cliente y hace `console.log`; **no hay
     `/api/auth/register`**. Sólo se pueden aseverar los mensajes de validación.
   - El link "Iniciar sesión" de `/register`, `/reset-password` y el éxito de
     `/reset-password/[token]` navegan a **`/`** (landing), **no** a `/login`.
   - **Destino post-login inconsistente**: el login (email y Google) manda a
     **`/watcher`**; el middleware, cuando un usuario ya logueado visita una
     auth-entry, manda a **`/dashboard`**. Ambas rutas existen.
   - `ScanFormDialog` (modal de escaneo) está exportado pero **no está montado**
     en ningún JSX; los CTA "Audita cualquier URL →" son `<Link href="/scan">`
     (navegación completa, no modal). Maneja el flujo modal como **latente**.
   - `/r/[token]` **expirado** se renderiza como **200** con copy "Este enlace
     expiró" (el 410 del backend lo consume el loader). Aseméralo por **texto**,
     no por HTTP status. El **404** de `/r` no tiene `not-found.tsx` local: burbujea
     al not-found raíz (copy distinta a la del reporte).

6. **Variantes responsivas.** El CTA de cuenta del TopNav se renderiza **dos veces**
   (icono móvil con `aria-label`, y texto en `sm+`). Fija viewport **≥ 640 px** para
   el texto ("Entrar"/"Mi Cuenta") o apunta al `aria-label` ("Entrar a cuenta"). El
   `HeroUrlForm` aparece **dos veces** en `/` (hero + CTA de cierre) con el **mismo
   `id="hero-url"`** → desambigua con `.first()` / `.last()`.

---

# Features

## F1 · Chrome de navegación pública (TopNav + Footer)

```gherkin
@public @smoke @a11y
Feature: Chrome de navegación pública (TopNav + Footer)
  El TopNav y el Footer envuelven toda la superficie Owliver. Su contenido
  cambia según haya o no sesión, pero el chrome nunca bloquea la página.

  Background:
    Given el viewport es de al menos 640px de ancho

  Scenario: Visitante anónimo ve el chrome anónimo
    Given que no tengo sesión
    When abro "/"
    Then veo el TopNav con la marca "Owliver — inicio"
    And veo el botón de cuenta "Entrar"
    And veo el CTA primario "Auditar URL"
    And NO veo los enlaces "Mis escaneos" ni "Monitoreo"

  Scenario Outline: Navegación desde el TopNav anónimo
    Given que estoy en "/"
    When hago clic en "<elemento>"
    Then la URL es "<destino>"

    Examples:
      | elemento     | destino |
      | Owliver — inicio | /     |
      | Auditar URL  | /scan   |
      | Entrar       | /login  |

  Scenario: Usuario autenticado ve el chrome con su cuenta
    Given que tengo una sesión válida con tenant
    When abro "/"
    Then el botón de cuenta dice "Mi Cuenta"
    And veo el enlace de navegación "Mis escaneos"
    And veo el enlace de navegación "Monitoreo"

  Scenario Outline: Navegación desde el TopNav autenticado
    Given que tengo una sesión válida con tenant
    And que estoy en "/"
    When hago clic en "<elemento>"
    Then la URL es "<destino>"

    Examples:
      | elemento      | destino   |
      | Mi Cuenta     | /dashboard|
      | Mis escaneos  | /scans    |
      | Monitoreo     | /watcher  |
      | Auditar URL   | /scan     |

  Scenario: El Footer ofrece soporte e iniciar sesión
    Given que estoy en "/"
    When me desplazo al Footer
    Then el enlace "Iniciar sesión" navega a "/login"
    And el enlace "Cómo se calcula la nota A-F" navega a "/"
    And el enlace "Reportar una vulnerabilidad" abre un mailto a contact@llamitai.com
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Marca / home | `getByRole('link', { name: 'Owliver — inicio' })` |
| Cuenta (anónimo, texto) | `getByRole('link', { name: 'Entrar' })` |
| Cuenta (anónimo, icono móvil) | `getByRole('link', { name: 'Entrar a cuenta' })` |
| Cuenta (autenticado) | `getByRole('link', { name: 'Mi Cuenta' })` |
| CTA primario | `getByRole('link', { name: 'Auditar URL' })` |
| Nav "Mis escaneos" | `getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Mis escaneos' })` |
| Nav "Monitoreo" | `getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Monitoreo' })` |
| Header landmark | `locator('header[data-slot="top-nav"]')` |
| Footer landmark | `locator('footer[data-slot="owliver-footer"]')` |
| Footer "Iniciar sesión" | `getByRole('link', { name: 'Iniciar sesión' })` |

**Notas:** el chrome anónimo vs. autenticado se decide server-side con
`refreshServerSession()` en ambos layouts; basta la cookie `___RT5___`.

---

## F2 · Landing de marketing (`/`)

```gherkin
@public @smoke
Feature: Landing de marketing "Cómo funciona"
  "/" es la landing (ComoFuncionaView), NO el ranking. Su objetivo es convertir:
  auditar una URL desde el hero. El formulario sólo valida en cliente y navega
  a /scan (no llama API).

  Background:
    Given que abro "/"
    Then veo el encabezado "Audita tu web y tu IA. Recibe un grado A–F."

  Scenario: Auditar una URL desde el hero (conversión principal)
    When escribo "ejemplo.gob.mx" en el campo de URL del hero
    Then la pista dice "Vas a auditar ejemplo.gob.mx"
    When hago clic en "Auditar" del hero
    Then la URL es "/scan?url=ejemplo.gob.mx"

  Scenario: La pista por defecto explica el nivel básico
    Then la pista del hero dice "Nivel básico: pasivo, anónimo y sin registro — listo en <90s."

  @negative
  Scenario Outline: Host inválido bloquea la navegación
    When escribo "<entrada>" en el campo de URL del hero
    And hago clic en "Auditar" del hero
    Then sigo en "/"
    And la pista del hero dice "Escribe un dominio público válido, p. ej. ejemplo.gob.mx"
    And el campo de URL tiene aria-invalid

    Examples:
      | entrada     |
      |             |
      | localhost   |
      | sinpunto    |
      | 192.168.0.1 |

  Scenario Outline: Otros CTA de la landing llevan a /scan
    When hago clic en "<cta>"
    Then la URL es "/scan"

    Examples:
      | cta                |
      | Lanza una auditoría|

  Scenario: Expandir una pregunta del FAQ
    When me desplazo a "Preguntas frecuentes"
    And hago clic en "¿Cómo funcionan los créditos?"
    Then se muestra la respuesta del acordeón

  Scenario: El CTA de cierre repite el formulario de auditoría
    When me desplazo a "Audita tu primer sitio en 90 segundos."
    And escribo "sat.gob.mx" en el segundo campo de URL (cierre)
    And hago clic en el botón "Auditar" de cierre
    Then la URL es "/scan?url=sat.gob.mx"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| H1 del hero | `getByRole('heading', { level: 1, name: 'Audita tu web y tu IA. Recibe un grado A–F.' })` |
| Campo URL (hero) | `getByPlaceholder('tu-sitio.gob.mx').first()` |
| Campo URL (cierre) | `getByPlaceholder('tu-sitio.gob.mx').last()` |
| Botón "Auditar" (hero) | `getByRole('button', { name: 'Auditar' }).first()` |
| Botón "Auditar" (cierre) | `getByRole('button', { name: 'Auditar' }).last()` |
| Pista/validación | `locator('#hero-url-hint').first()` |
| CTA teaser | `getByRole('link', { name: 'Lanza una auditoría' })` |
| FAQ item | `getByText('¿Cómo funcionan los créditos?')` |

**Notas:** el `id="hero-url"` está duplicado (bug a11y conocido) → usa
`.first()`/`.last()`. El submit es `router.push` puro (sin red).

---

## F3 · Iniciar un escaneo (`/scan`)

```gherkin
@public @scan @smoke
Feature: Iniciar un escaneo
  /scan permite elegir URL + nivel de ataque, atestiguar autorización para
  niveles activos, y enviar. Éxito → redirige al theater /scans/{id}.

  Background:
    Given que abro "/scan"
    Then veo el encabezado "Audita cualquier sitio"
    And el nivel "Básico" está seleccionado por defecto
    And NO veo el panel de atestación

  @smoke
  Scenario: Escaneo pasivo (Básico) — camino feliz
    When escribo "example.com" en "URL del sitio a auditar"
    Then veo la vista previa "Vas a escanear: example.com"
    When hago clic en "Auditar este sitio →"
    Then el botón muestra "Iniciando escaneo…" y se deshabilita
    And soy redirigido a una URL que coincide con "/scans/.+"

  Scenario: Escaneo activo (Intermedio) requiere atestación
    When escribo "ejemplo.gob.mx" en "URL del sitio a auditar"
    And selecciono el nivel "Intermedio"
    Then aparece el panel de atestación
    And veo el aviso "Vas a lanzar pruebas intrusivas contra ejemplo.gob.mx; hacerlo sin autorización es ilegal."
    And el botón "Auditar este sitio →" está deshabilitado
    When marco "Declaro tener autorización para auditar este dominio."
    Then el botón "Auditar este sitio →" se habilita
    When hago clic en "Auditar este sitio →"
    Then soy redirigido a una URL que coincide con "/scans/.+"

  Scenario: Ver términos de autorización
    When selecciono el nivel "Avanzado"
    And hago clic en "Ver términos"
    Then se abre el diálogo "Términos de autorización de auditoría"

  Scenario: Cambiar a Básico limpia la atestación
    When selecciono el nivel "Intermedio"
    And marco la casilla de atestación
    And selecciono el nivel "Básico"
    Then NO veo el panel de atestación
    And el botón "Auditar este sitio →" está habilitado

  @negative
  Scenario Outline: Validación de URL en el submit
    When escribo "<entrada>" en "URL del sitio a auditar"
    And hago clic en "Auditar este sitio →"
    Then veo el error "<mensaje>"
    And sigo en "/scan"

    Examples:
      | entrada      | mensaje                                                |
      |              | Ingresa una URL                                        |
      | http://      | URL inválida                                           |
      | localhost    | Solo dominios públicos (no IPs privadas ni localhost)  |
      | 10.0.0.5     | Solo dominios públicos (no IPs privadas ni localhost)  |

  @negative
  Scenario: Atestación faltante en nivel activo
    When escribo "ejemplo.gob.mx" en "URL del sitio a auditar"
    And selecciono el nivel "Intermedio"
    And hago clic en "Auditar este sitio →"
    Then veo el error "Debes declarar que tienes autorización para auditar este dominio"

  @scan
  Scenario: Deep-link con URL pre-llenada
    When abro "/scan?url=https://www.ejemplo.gob.mx/foo"
    Then el campo "URL del sitio a auditar" contiene "www.ejemplo.gob.mx"
    And veo la vista previa "Vas a escanear: www.ejemplo.gob.mx"

  @negative
  Scenario Outline: Errores del backend mapeados a la UI
    Given que el backend responde "<status>" al crear el scan
    When envío un escaneo Básico válido
    Then veo la alerta "<copy>"

    Examples:
      | status | copy                                                                |
      | 429    | Demasiados escaneos. Intenta de nuevo en un momento.                |
      | 403    | No tienes permiso para escanear este dominio.                       |
      | 422    | No pudimos validar la solicitud. Revisa la URL y la autorización.   |
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| H1 | `getByRole('heading', { name: 'Audita cualquier sitio' })` |
| Campo URL | `getByRole('textbox', { name: 'URL del sitio a auditar' })` (o `getByPlaceholder('example.com')`) |
| Vista previa host | `getByText(/Vas a escanear:/)` |
| Nivel Básico/Intermedio/Avanzado | `getByRole('radio', { name: 'Básico' \| 'Intermedio' \| 'Avanzado' })` |
| Panel atestación | `locator('[data-slot="attestation-gate"]')` |
| Casilla atestación | `locator('[data-slot="attestation-gate"]').getByRole('checkbox')` |
| Ver términos | `getByRole('button', { name: 'Ver términos' })` |
| Diálogo términos | `getByRole('dialog', { name: 'Términos de autorización de auditoría' })` |
| Submit | `getByRole('button', { name: 'Auditar este sitio →' })` |
| Submit (pendiente) | `getByRole('button', { name: 'Iniciando escaneo…' })` |
| Alerta de error | `getByRole('alert')` |

**Notas:** el submit se deshabilita si `pending` **o** (nivel activo **y** sin
atestar). En entorno fixture, cualquier error que NO sea 429/403/422 cae al
fallback y devuelve `{ scanId: HERO_SCAN_ID }` con 201 → el happy path redirige
solito. Para probar 429/403/422 mockea esos status en el BFF/backend. El `<Input>`
es Base UI (`onValueChange`): `fill()`/`type()` funcionan; un `onChange` crudo de
React se ignoraría. La URL se normaliza (prefija `https://`, slash final).

---

## F4 · Historial de escaneos (`/scans`)

```gherkin
@scan @protected
Feature: Mis escaneos (historial)
  /scans lista el historial del usuario con búsqueda, filtros por estado y
  ordenamiento. Las filas terminadas van al reporte; las demás, al theater.

  Background:
    Given que tengo una sesión válida con tenant
    And que abro "/scans"
    Then veo el encabezado "Mis escaneos"
    And veo el eyebrow "Banco de inspección"

  @smoke
  Scenario: Abrir el reporte de un scan terminado
    When hago clic en una fila con grado (estado done/partial)
    Then la URL coincide con "/scans/.+/report"

  Scenario: Abrir el theater de un scan en curso
    When hago clic en una fila en curso (running/queued)
    Then la URL coincide con "/scans/[^/]+$"

  Scenario: Buscar por dominio u organización
    When escribo "imss" en "Buscar por dominio u organización…"
    Then la lista se filtra por host u organización que coincidan

  Scenario Outline: Filtrar por estado con las pestañas
    When hago clic en la pestaña "<tab>"
    Then la pestaña "<tab>" queda seleccionada (aria-selected)

    Examples:
      | tab       |
      | Todos     |
      | En curso  |
      | Completos |
      | Fallidos  |

  Scenario: Ordenar por peor grado
    When hago clic en "Peor grado"
    Then los grupos de tiempo colapsan en un único grupo "Por gravedad"
    And las filas se ordenan de F a A
    When hago clic en "Recientes"
    Then la lista vuelve a agruparse por "Hoy" / "Esta semana" / "Anteriores"

  @negative
  Scenario: Filtros sin resultados
    When escribo "zzzznoexiste" en "Buscar por dominio u organización…"
    Then veo "Sin escaneos para estos filtros"
    When hago clic en "Limpiar filtros"
    Then la búsqueda se limpia y la pestaña vuelve a "Todos"

  Scenario: Primer uso (sin escaneos)
    Given que no tengo ningún escaneo
    When abro "/scans"
    Then veo "Aún no has auditado ningún sitio"
    When hago clic en "Auditar mi primera URL"
    Then la URL es "/scan"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| H1 | `getByRole('heading', { level: 1, name: 'Mis escaneos' })` |
| CTA cabecera | `getByRole('link', { name: 'Auditar URL' })` |
| Búsqueda | `getByPlaceholder('Buscar por dominio u organización…')` |
| Tablist | `getByRole('tablist', { name: 'Filtrar por estado' })` |
| Pestaña estado | `getByRole('tab', { name: /Todos\|En curso\|Completos\|Fallidos/ })` |
| Orden | `getByRole('button', { name: 'Recientes' \| 'Peor grado' })` |
| Fila (link) | `getByRole('link', { name: /grado\|En cola\|En curso\|Falló\|Cancelado/ })` |
| Limpiar filtros | `getByRole('button', { name: 'Limpiar filtros' })` |
| CTA primer uso | `getByRole('link', { name: 'Auditar mi primera URL' })` |

**Notas:** regla de ruteo (`scanHref`): `done|partial → /scans/{id}/report`; el
resto → `/scans/{id}`. Las pestañas llevan un contador mono al lado → usa regex en
el name. "Limpiar filtros" NO resetea el orden. El readout-strip se calcula sobre
la lista completa, no sobre el filtro. Datos por fixture (renderiza offline); no
hay guard de middleware en estas rutas (la visibilidad real la impone el backend).

---

## F5 · Live Pentest Theater (`/scans/[id]`)

```gherkin
@scan @theater
Feature: Live Pentest Theater
  Vista war-room en vivo de un scan: cabecera con host/nivel/estado de conexión,
  dos carriles de agente, feed de hallazgos, gauges parciales y log de telemetría.
  Con fixtures, el stream corre solo hasta terminar.

  @smoke
  Scenario: Ver un scan en vivo hasta su estado terminal
    Given que abro "/scans/scan-salud-running-0007"
    Then veo el host del scan como encabezado
    And la insignia de conexión muestra "conectando…" y luego "en vivo"
    And veo el marcador de grado en construcción "?"
    And veo el carril "OWASP Scanner"
    And veo el carril "Agentic Surface Auditor"
    When el stream llega a estado terminal
    Then la insignia muestra "transmisión finalizada"
    And veo el enlace "Ver reporte completo →"
    When hago clic en "Ver reporte completo →"
    Then la URL coincide con "/scans/.+/report"

  Scenario: Inspeccionar un hallazgo en vivo
    Given que estoy en el theater de un scan en curso
    When hago clic en un hallazgo del feed "Hallazgos en vivo"
    Then se abre el diálogo de detalle del hallazgo
    When hago clic en "Cerrar detalle del hallazgo"
    Then el diálogo se cierra

  Scenario: Cancelar un scan en curso
    Given que abro "/scans/scan-salud-running-0007"
    When hago clic en "Cancelar"
    Then el botón muestra un spinner y se deshabilita
    And eventualmente veo el aviso "Escaneo cancelado."
    And la insignia muestra "transmisión finalizada"
    And el botón "Cancelar" es reemplazado por "Ver reporte completo →"

  Scenario: Scan en cola
    Given que abro "/scans/scan-mitienda-queued-0009"
    Then veo "En cola — el búho está dormido, esperando turno…"

  @negative
  Scenario: Scan inexistente o privado (404)
    Given que el backend responde 404 para el scan
    When abro "/scans/desconocido"
    Then veo "Escaneo no encontrado"
    And veo "Este escaneo no existe o no tienes acceso a él. Los escaneos privados solo son visibles para su propietario."
    When hago clic en "Volver al inicio"
    Then la URL es "/"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Insignia conexión | `getByText(/en vivo\|conectando…\|transmisión finalizada/)` |
| Host (H1) | `getByRole('heading', { level: 1 })` |
| Grado en construcción | `getByRole('img', { name: 'Grado en construcción' })` |
| Cancelar | `getByRole('button', { name: 'Cancelar' })` |
| Ver reporte | `getByRole('link', { name: /Ver reporte completo/ })` |
| Carril OWASP / Agéntico | `locator('[data-slot="agent-lane"][data-lane="owasp"\|"agentic"]')` |
| ToolChip | `locator('[data-slot="tool-chip"][data-tool][data-state]')` |
| Feed hallazgos | `getByRole('heading', { name: 'Hallazgos en vivo' })` |
| Item de hallazgo | `locator('[data-slot="finding-feed-item"]')` |
| Diálogo detalle | `getByRole('dialog')` |
| Cerrar detalle | `getByRole('button', { name: 'Cerrar detalle del hallazgo' })` |
| Telemetría | `getByRole('log', { name: 'Registro de telemetría del escaneo' })` |

**Notas:** insignia → terminal: "transmisión finalizada"; abierto y no terminal:
"en vivo"; si no: "conectando…". El budget timer topa en `<1:30` (90 s). Para 404
real debes mockear el backend; con fixtures el theater **siempre** reproduce (no
404). El feed vacío muestra "Aún sin hallazgos. El búho sigue cazando…".

---

## F6 · Reporte interactivo (`/scans/[id]/report`)

```gherkin
@report @scan
Feature: Reporte de seguridad
  Capa ejecutiva (grado A–F, dos gauges, "Owliver te explica", top riesgos,
  superficie agéntica) + capa técnica (filtros + acordeón de hallazgos con
  evidencia). Acciones: Compartir, Exportar PDF.

  Background:
    Given que abro "/scans/scan-tesoreria-0021/report"
    Then veo el encabezado "Owliver te explica"
    And veo el encabezado "Hallazgos técnicos"

  @smoke
  Scenario: Navegar a la vista en vivo y al histórico desde el reporte
    When hago clic en "ver escaneo en vivo"
    Then la URL coincide con "/scans/.+$"
    When vuelvo atrás
    And hago clic en "Ver histórico del sitio →"
    Then la URL coincide con "/sites/.+"

  Scenario Outline: Filtrar hallazgos por severidad y fuente
    When hago clic en el filtro "<filtro>"
    Then la lista de hallazgos se filtra acordemente

    Examples:
      | filtro   |
      | Crítica  |
      | Alta     |
      | Media    |
      | Baja     |
      | Agéntico |
      | Web      |

  @negative
  Scenario: Filtros sin resultados
    When aplico un filtro de severidad+fuente sin coincidencias
    Then veo "No hay hallazgos con estos filtros."

  Scenario: Expandir un hallazgo técnico
    When hago clic en el encabezado de un hallazgo no crítico
    Then se revelan "Descripción", "Impacto" y "Remediación"

  @share
  Scenario: Compartir genera un enlace público
    When hago clic en "Compartir"
    Then el botón muestra un spinner
    And luego el botón dice "Enlace copiado"
    And veo una línea que termina en "· válido 7 días"

  Scenario: Exportar a PDF abre una pestaña nueva
    Then el enlace "Exportar PDF" tiene como destino "/api/v1/scans/scan-tesoreria-0021/report.pdf"
    And el enlace abre en una pestaña nueva (target=_blank)

  @redaction
  Scenario: El reporte completo muestra la prueba canario
    Then existe un elemento con data-testid "canary"

  @negative
  Scenario: Reporte inexistente o privado (404)
    Given que el backend responde 404 para el reporte
    When abro "/scans/desconocido/report"
    Then veo "No encontramos ese reporte"
    When hago clic en "Volver al leaderboard"
    Then la URL es "/"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| "ver escaneo en vivo" | `getByRole('link', { name: 'ver escaneo en vivo' })` |
| Compartir | `getByRole('button', { name: 'Compartir' })` |
| Confirmación share | `getByText(/· válido 7 días$/)` (o botón `name: 'Enlace copiado'`) |
| Exportar PDF | `getByRole('link', { name: 'Exportar PDF' })` |
| Filtro severidad | `getByRole('button', { name: 'Todas'\|'Crítica'\|'Alta'\|'Media'\|'Baja' })` |
| Filtro fuente | `getByRole('button', { name: 'Todo'\|'Agéntico'\|'Web' })` |
| Encabezados sección | `getByRole('heading', { name: 'Owliver te explica'\|'Principales riesgos'\|'Superficie agéntica detectada'\|'Hallazgos técnicos' })` |
| Canario (sólo reporte completo) | `getByTestId('canary')` |
| Ver histórico | `getByRole('link', { name: 'Ver histórico del sitio →' })` |
| Volver al leaderboard (404) | `getByRole('link', { name: 'Volver al leaderboard' })` |

**Notas:** "Web" y "Agéntico" aparecen como label de gauge, pill de filtro **y**
chip por hallazgo → **acota a `button`** para el filtro. Severidad usa "Todas"
(fem.), fuente usa "Todo" (masc.). El share, offline, acuña token `demo-{id}`.
PDF es un `<a target=_blank>` (proxy `/api/v1/*`), no un BFF; asevera href +
target. `gradeLabel`: A=Seguro, B=Bueno, C=Aceptable, D=Deficiente, E=Malo,
F=Reprobado.

---

## F7 · Reporte público compartido (`/r/[token]`)

```gherkin
@public @report @share @redaction
Feature: Reporte público redactado
  Superficie viral por token (TTL 7 días). Capa ejecutiva completa + capa técnica
  con la evidencia de explotación OCULTA. Regla de seguridad, no de UI.

  Scenario: Ver un reporte público válido con evidencia redactada
    Given un token de reporte válido
    When abro "/r/{token}"
    Then veo el eyebrow "Reporte público · Owliver"
    And veo el encabezado "Owliver te explica"
    And veo el encabezado "Hallazgos técnicos"
    When expando un hallazgo
    Then veo el candado "Evidencia de explotación oculta en el reporte público."
    And NO existe ningún elemento con data-testid "canary"
    And veo la nota "Reporte generado por Owliver — la evidencia de explotación se oculta en los enlaces públicos."

  @negative
  Scenario: Enlace público expirado (renderiza 200 con copy de expiración)
    Given un token expirado/revocado (el backend responde 410)
    When abro "/r/{token}"
    Then veo "Este enlace expiró"
    And veo "Los enlaces compartidos caducan a los 7 días."
    When hago clic en "Ir al inicio →"
    Then la URL es "/"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Eyebrow público | `getByText('Reporte público · Owliver')` |
| Candado redacción | `getByText('oculta en el reporte público')` |
| Nota pie | `getByText('Reporte generado por Owliver — la evidencia de explotación se oculta en los enlaces públicos.')` |
| Expirado (H1) | `getByRole('heading', { name: 'Este enlace expiró' })` |
| CTA expirado | `getByRole('link', { name: 'Ir al inicio →' })` |

**Notas (críticas):** la prueba de redacción más fuerte = `getByTestId('canary')`
**existe** en `/scans/[id]/report` pero **NO** en `/r/[token]`. El expirado es un
**branch React 200**, no un 410 HTTP → asevera por texto. El 404 de `/r` burbujea
al not-found raíz (copy distinta a la del reporte). Offline, `publicReportFixture`
renderiza como válido.

---

## F8 · Histórico del sitio (`/sites/[id]`)

```gherkin
@public @report
Feature: Histórico del sitio
  Resumen del último scan + tendencia de grados + qué cambió + timeline de scans.
  No existe índice /sites; se llega desde el ranking, el reporte o la watchlist.

  Background:
    Given que abro "/sites/site-demo"
    Then veo el grado actual y los gauges Web/Agéntico

  Scenario: Abrir el reporte del último escaneo
    When hago clic en "Ver reporte completo →"
    Then la URL coincide con "/scans/.+/report"

  Scenario: Ver la tendencia de grados
    Then veo el encabezado "Tendencia del grado"
    And veo una línea como "N escaneos registrados."

  Scenario: Abrir un escaneo del historial
    When me desplazo a "Historial de escaneos"
    And hago clic en una fila del timeline
    Then la URL coincide con "/scans/.+/report"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Ver reporte completo | `getByRole('link', { name: /Ver reporte completo/ })` |
| Tendencia (H2) | `getByRole('heading', { name: 'Tendencia del grado' })` |
| Gráfica tendencia | `getByRole('img', { name: 'Tendencia del grado a lo largo del tiempo' })` |
| Historial (H2) | `getByRole('heading', { name: 'Historial de escaneos' })` |
| Fila timeline | `getByRole('heading', { name: 'Historial de escaneos' }).locator('xpath=following::ol[1]/li/a')` |

**Notas:** "Qué cambió desde el escaneo anterior" sólo aparece con ≥2 scans; con un
solo scan no hay delta y la gráfica muestra un único punto. Offline → `siteFixture`.

---

## F9 · Ranking .gob.mx (/watch) — PROTEGIDO

```gherkin
@protected @ranking
Feature: Ranking de sitios .gob.mx
  El ranking worst-first vive en /watch y está GATEADO (requiere sesión + tenant).
  No hay ranking público hoy.

  @negative @auth
  Scenario: Anónimo no puede ver el ranking
    Given que no tengo sesión
    When abro "/watch"
    Then soy redirigido a "/login"

  @smoke
  Scenario: Usuario autenticado ve y filtra el ranking
    Given que tengo una sesión válida con tenant
    When abro "/watch"
    Then veo el encabezado "La seguridad, medida como evidencia."
    And veo la región "Ranking de seguridad de sitios" con filas worst-first
    When hago clic en el filtro "F"
    Then la lista se vuelve a consultar filtrada por grado
    When hago clic en "Peor agéntico"
    Then la lista se filtra por peor puntaje agéntico
    When hago clic en "Cargar más"
    Then se carga la siguiente página

  Scenario: Abrir el detalle de un sitio desde una fila
    Given que tengo una sesión válida con tenant
    And que estoy en "/watch"
    When hago clic en la primera fila del ranking
    Then la URL coincide con "/sites/.+"

  Scenario Outline: CTAs del ranking
    Given que tengo una sesión válida con tenant
    And que estoy en "/watch"
    When hago clic en "<cta>"
    Then la URL es "<destino>"

    Examples:
      | cta                  | destino   |
      | Audita cualquier URL →| /scan    |
      | Ir a mi watchlist    | /watcher  |

  @negative
  Scenario: Ranking vacío con filtro
    Given que tengo una sesión válida con tenant
    And que ningún sitio coincide con el filtro activo
    Then veo "Ningún sitio coincide con ese filtro"
    When hago clic en "Ver todos"
    Then los filtros se limpian
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| H1 | `getByRole('heading', { level: 1, name: 'La seguridad, medida como evidencia.' })` |
| Región ranking | `getByRole('region', { name: 'Ranking de seguridad de sitios' })` |
| Filtro grado | `getByRole('button', { name: 'F', exact: true })` |
| Filtro "Peor web" / "Peor agéntico" | `getByRole('button', { name: 'Peor web'\|'Peor agéntico' })` |
| Fila ranking | `getByRole('region', { name: 'Ranking de seguridad de sitios' }).getByRole('listitem').first().getByRole('link')` |
| Cargar más | `getByRole('button', { name: 'Cargar más' })` |
| Ver todos (vacío) | `getByRole('button', { name: 'Ver todos' })` |

**Notas:** DISCREPANCIA con `flows.md`: el ranking **no** está en `/`. Comentarios
viejos en el código dan a entender que el ranking vive en "/" — el correcto es el del
middleware: el ranking se movió a `/watch` y está gateado. Para E2E siembra sesión
+ tenant antes de `/watch`. Filtros recargan vía `useRanking` (no re-ordenan en
cliente).

---

## F10 · Watchlist y monitoreo (`/watcher`) — PROTEGIDO

```gherkin
@protected @watchlist
Feature: Watchlist y monitoreo continuo
  /watcher es la superficie canónica de monitoreo: agregar dominios, alternar
  monitoreo por fila, re-escanear, quitar, y preferencias de alerta. /watchlist
  redirige aquí.

  Background:
    Given que tengo una sesión válida con tenant
    And que abro "/watcher"
    Then veo el título "Mi watchlist"
    And la pestaña "Sitios" está activa

  Scenario: /watchlist redirige a /watcher
    When abro "/watchlist"
    Then la URL es "/watcher"

  @smoke
  Scenario: Agregar un dominio a la watchlist
    When escribo "ejemplo.com.mx" en "Agregar dominio"
    And hago clic en "Agregar"
    Then el dominio se agrega a la lista
    And el campo se limpia

  @negative
  Scenario Outline: Validación al agregar dominio
    When escribo "<entrada>" en "Agregar dominio"
    And hago clic en "Agregar"
    Then veo el error "<mensaje>"

    Examples:
      | entrada   | mensaje                                                       |
      |           | Ingresa una URL o dominio.                                    |
      | localhost | Ingresa un dominio público válido (no IPs privadas ni localhost). |

  Scenario: Alternar monitoreo de una fila
    Given que hay al menos una fila en la watchlist
    When alterno el switch "Monitoreo de {host}"
    Then se envía la actualización de monitoreo de esa fila

  Scenario Outline: Acciones de fila de watchlist
    Given que hay al menos una fila en la watchlist
    When hago clic en "<accion>" de la fila
    Then la URL coincide con "<destino>"

    Examples:
      | accion       | destino        |
      | Re-escanear  | /scan\?url=.+  |
      | (grado/título)| /sites/.+     |

  Scenario: Quitar un sitio de la watchlist
    Given que hay al menos una fila en la watchlist
    When hago clic en "Quitar {host} de la watchlist"
    Then la fila se elimina de la lista

  @smoke
  Scenario: Configurar preferencias de alerta
    When hago clic en la pestaña "Config"
    And alterno el switch "Alertas por correo"
    And escribo un webhook en "Webhook de Slack (opcional)"
    And hago clic en "Guardar"
    Then veo la confirmación "Guardado"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Título | `getByRole('heading', { level: 1 })` (texto "Mi watchlist") |
| Pestañas | `getByRole('tab', { name: 'Sitios'\|'Config' })` |
| Agregar dominio (input) | `getByLabel('Agregar dominio')` |
| Switch monitorear (form) | `getByRole('switch')` |
| Agregar (submit) | `getByRole('button', { name: 'Agregar' })` |
| Error/alerta | `getByRole('alert')` |
| Switch por fila | `getByRole('switch', { name: 'Monitoreo de {host}' })` |
| Re-escanear | `getByRole('link', { name: 'Re-escanear' })` |
| Link grado/título de fila | `getByRole('link', { name: /Ver / })` / `getByRole('link', { name: '{departmentName||host}' })` |
| Quitar | `getByRole('button', { name: 'Quitar {host} de la watchlist' })` |
| Alertas por correo | `getByRole('switch', { name: 'Alertas por correo' })` |
| Webhook Slack | `getByLabel('Webhook de Slack (opcional)')` |
| Guardar | `getByRole('button', { name: 'Guardar' })` |

**Notas:** la clave de mutación es el **id de fila** (`row.id`), nunca `siteId`
(que sólo se usa para navegar a `/sites/{siteId}`). Los GET caen a fixture
offline, pero **POST/PATCH/DELETE/PUT reenvían el error real** y **necesitan sesión
real**: planifica las pruebas de escritura contra un backend vivo o mockea el BFF.
Las mismas alert prefs se editan también en `/settings/notifications`. El rename
del título sólo persiste en `localStorage` (`owliver:watcher:name`).

---

## F11 · Autenticación y sesión

```gherkin
@auth
Feature: Autenticación y sesión
  Existen DOS logins reales (email+contraseña y Google OAuth). Registro es STUB.
  Reset de contraseña e invitaciones son reales.

  @smoke
  Scenario: Login con email y contraseña
    Given que no tengo sesión
    And que abro "/login"
    Then veo el encabezado "Entra a Owliver"
    When escribo mi correo en "Correo electrónico"
    And escribo mi contraseña en "Contraseña"
    And hago clic en "Iniciar sesión"
    Then soy redirigido a "/watcher"

  @negative
  Scenario Outline: Errores de login con credenciales
    Given que abro "/login"
    When intento iniciar sesión con "<caso>"
    Then veo la alerta "<copy>"

    Examples:
      | caso                 | copy                                                |
      | campos vacíos        | Ingresa tu correo y contraseña.                     |
      | credenciales malas   | Correo o contraseña incorrectos. Inténtalo de nuevo.|

  Scenario: Iniciar login con Google
    Given que abro "/login"
    When hago clic en "Entrar con Google"
    Then el navegador va a "/api/auth/google/start"

  Scenario: Callback de Google exitoso
    Given que regreso a "/login/callback?code=valid-code"
    Then veo "Verificando tu sesión…"
    And luego "Listo, redirigiendo…"
    And soy redirigido al destino (por defecto "/watcher")

  @negative
  Scenario Outline: Errores de OAuth en la pantalla de login
    When abro "/login?error=<code>"
    Then veo la alerta "No pudimos iniciar tu sesión"

    Examples:
      | code     |
      | oauth    |
      | config   |
      | exchange |

  @stub
  Scenario: Registro (STUB — sin backend)
    Given que abro "/register"
    When relleno nombre, correo, contraseña y confirmación válidos
    And hago clic en "Crear cuenta"
    Then NO ocurre navegación ni llamada de red
    # Sólo se pueden aseverar los mensajes de validación, no el éxito.

  @negative @stub
  Scenario Outline: Validación del registro
    Given que abro "/register"
    When envío el formulario con "<caso>"
    Then veo "<mensaje>"

    Examples:
      | caso                  | mensaje                                       |
      | nombre vacío          | El nombre es requerido                        |
      | correo inválido       | Ingresa un correo electrónico válido          |
      | contraseña corta      | La contraseña debe tener al menos 6 caracteres|
      | contraseñas distintas | Las contraseñas no coinciden                  |

  Scenario: El registro enlaza a iniciar sesión hacia la landing
    Given que abro "/register"
    When hago clic en "Iniciar sesión"
    Then la URL es "/"

  Scenario: Solicitar restablecer contraseña
    Given que abro "/reset-password"
    When escribo mi correo en "Correo electrónico"
    And hago clic en "Enviar enlace de recuperación"
    Then veo un mensaje que incluye "está registrado, recibirás un enlace"

  Scenario: Confirmar nueva contraseña con token
    Given que abro "/reset-password/un-token"
    When escribo una nueva "Contraseña" y la "Confirmar contraseña" (≥8, iguales)
    And hago clic en "Restablecer contraseña"
    Then veo "Contraseña actualizada"
    When hago clic en "Iniciar sesión"
    Then la URL es "/"

  @negative
  Scenario: Token de reset inválido o expirado
    Given que el backend responde InvalidOrExpiredToken
    When confirmo una nueva contraseña en "/reset-password/expirado"
    Then veo "Este enlace ya no es válido o expiró. Solicita uno nuevo."

  Scenario: Aceptar una invitación
    Given una invitación válida en "/invitations/un-token"
    Then veo "Te invitaron a <organización>"
    When escribo "Nombre" (y contraseña si se requiere)
    And hago clic en "Aceptar invitación"
    Then soy redirigido a "/dashboard"

  Scenario Outline: Estados de invitación
    When abro "/invitations/<token>"
    Then veo "<copy>"

    Examples:
      | token            | copy                            |
      | ya-aceptada      | Esta invitación ya fue aceptada |
      | caducada         | Esta invitación caducó          |
      | inexistente      | Enlace no válido                |

  Scenario: Cerrar sesión
    Given que tengo una sesión válida
    When abro el menú de usuario
    And hago clic en "Cerrar sesión"
    Then soy redirigido a "/login"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Login H1 | `getByRole('heading', { name: 'Entra a Owliver' })` |
| Correo | `getByLabel('Correo electrónico')` |
| Contraseña | `getByLabel('Contraseña')` |
| Iniciar sesión | `getByRole('button', { name: 'Iniciar sesión' })` |
| Entrar con Google | `getByRole('link', { name: 'Entrar con Google' })` |
| Alerta login | `getByRole('alert')` |
| Callback status | `getByText('Verificando tu sesión…')` / `getByText('Listo, redirigiendo…')` |
| Registro: Crear cuenta | `getByRole('button', { name: 'Crear cuenta' })` |
| Reset: enviar enlace | `getByRole('button', { name: 'Enviar enlace de recuperación' })` |
| Reset confirm: submit | `getByRole('button', { name: 'Restablecer contraseña' })` |
| Reset confirm: éxito | `getByRole('heading', { name: 'Contraseña actualizada' })` |
| Invitación: aceptar | `getByRole('button', { name: 'Aceptar invitación' })` (o `'Unirme al tenant'`) |
| Menú usuario / Cerrar sesión | `getByRole('menuitem', { name: 'Cerrar sesión' })` |

**Notas:** inputs con `id`+`htmlFor` estables → `getByLabel` funciona. Copy vía
next-intl (es/en) — fija el locale o asevera por role/estructura si te preocupa la
flakiness. El éxito del login pasa `accessToken: ""` al store, así que
`isAuthenticated()` de cliente es brevemente `false` hasta que un layout protegido
refresca; **no** uses el store de cliente para aseverar sesión, usa el comportamiento.

---

## F12 · Gating de rutas y redirecciones de sesión

```gherkin
@auth @protected
Feature: Gating de rutas (middleware + layout protegido)
  El acceso se decide en dos capas: el middleware (cookie ___RT5___) y el layout
  (protected) server-side (refreshServerSession → tenant).

  Scenario Outline: Anónimo en ruta protegida es enviado a login
    Given que no tengo sesión
    When abro "<ruta>"
    Then soy redirigido a "/login"

    Examples:
      | ruta       |
      | /watch     |
      | /watcher   |
      | /dashboard |
      | /members   |

  Scenario Outline: Usuario logueado en auth-entry es enviado al dashboard
    Given que tengo una sesión válida con tenant
    When abro "<ruta>"
    Then soy redirigido a "/dashboard"

    Examples:
      | ruta            |
      | /login          |
      | /register       |
      | /reset-password |

  Scenario: Sesión sin tenant es enviada a crear organización
    Given que tengo sesión pero sin tenant
    When abro "/dashboard"
    Then soy redirigido a "/unassigned"

  Scenario Outline: Superficies públicas siguen accesibles con sesión
    Given que tengo una sesión válida con tenant
    When abro "<ruta>"
    Then permanezco en "<ruta>" (sin rebote)

    Examples:
      | ruta   |
      | /      |
      | /scan  |
```

**Notas:** `PUBLIC_EXACT_ROUTES = ['/', '/register', '/reset-password', '/login',
'/scan']`; `PUBLIC_PREFIX_ROUTES = ['/invitations/', '/reset-password/', '/login/',
'/scans/', '/sites/', '/r/']`. DISCREPANCIA: el middleware manda auth-entry logueado
a `/dashboard`, pero el login exitoso va a `/watcher` — ambas existen. Guard de
refresh-loop: `___RA5___ ≥ 3` limpia cookies y deja pasar.

---

## F13 · Administración del tenant (boilerplate SaaS)

```gherkin
@protected @admin
Feature: Administración del tenant
  Páginas envueltas por el layout (protected) + PermissionGuard cliente. Sin
  permiso → redirige a /forbidden. Journeys core de Owliver están en F10; esto
  es CRUD de fundación.

  Background:
    Given que tengo una sesión válida con tenant

  @smoke
  Scenario: Llegar al dashboard y a miembros
    When abro "/dashboard"
    Then veo un encabezado que incluye "Hola de nuevo,"
    When hago clic en "Ver miembros"
    Then la URL es "/members"

  Scenario: Invitar a un miembro (requiere permiso)
    Given que tengo el permiso "tenant_users.create"
    And que abro "/members"
    When hago clic en "Invitar"
    Then se abre el diálogo "Invitar usuario"
    When escribo un correo en "Email *" y hago clic en "Siguiente"
    And elijo un rol y hago clic en "Siguiente"
    And hago clic en "Enviar invitación"
    Then la invitación aparece como pendiente

  @negative
  Scenario: Sin permiso, una página protegida redirige a /forbidden
    Given que NO tengo el permiso "tenant_settings.update"
    When abro "/settings"
    Then soy redirigido a "/forbidden"
    And veo "No tienes permiso para ver esta página"
    When hago clic en "Volver al inicio"
    Then la URL es "/dashboard"

  Scenario Outline: Acceso por permiso a páginas de administración
    Given que tengo el permiso "<permiso>"
    When abro "<ruta>"
    Then veo el encabezado "<encabezado>"

    Examples:
      | ruta        | permiso                 | encabezado    |
      | /roles      | tenant_roles.view       | Roles         |
      | /api-keys   | tenant_settings.update  | API Keys      |
      | /members    | tenant_users.view       | Usuarios      |

  Scenario: Notificaciones es accesible sin guard de permiso
    When abro "/settings/notifications"
    Then veo el encabezado "Notificaciones"

  Scenario: Crear la primera organización (sin tenant)
    Given que tengo sesión pero sin tenant
    When abro "/unassigned"
    Then veo "Crea tu organización"
    When escribo el nombre y hago clic en "Crear organización"
    Then soy enviado fuera de "/unassigned"
```

**Selectores (Playwright)**

| Elemento | Selector |
|---|---|
| Dashboard welcome | `getByRole('heading', { name: /Hola de nuevo/ })` |
| Ver miembros | `getByRole('link', { name: /Ver miembros/ })` |
| Invitar | `getByRole('button', { name: 'Invitar' })` |
| Diálogo invitar | `getByRole('dialog')` (título "Invitar usuario") |
| Email invitación | `getByLabel('Email *')` |
| Siguiente / Enviar | `getByRole('button', { name: 'Siguiente'\|'Enviar invitación' })` |
| Crear Rol | `getByRole('button', { name: 'Crear Rol' })` |
| Nueva clave (API) | `getByRole('button', { name: 'Nueva clave' })` |
| Forbidden H1 | `getByRole('heading', { name: 'No tienes permiso para ver esta página' })` |
| Forbidden "Volver al inicio" | `getByRole('link', { name: 'Volver al inicio' })` |
| Unassigned H1 | `getByRole('heading', { name: 'Crea tu organización' })` |
| Crear organización | `getByRole('button', { name: 'Crear organización' })` |

**Notas:** `PermissionGuard` es **cliente**: mientras carga renderiza `null` y, si
falta permiso, hace `router.replace('/forbidden')` en `useEffect` (la página monta
brevemente). Mapa de permisos: `/dashboard→dashboard.view`,
`/members→tenant_users.view`, `/roles→tenant_roles.view`,
`/settings`/`/api-keys→tenant_settings.update`, `/settings/notifications` y
`/profile` **sin guard**. Botones de acción tienen gates finos
(`tenant_users.create`, `tenant_roles.create`, …) y se **deshabilitan** (no se
ocultan).

---

## Apéndice A · Mapeos de etiquetas para aserciones

**Grado → etiqueta (`gradeLabel`):** A=Seguro · B=Bueno · C=Aceptable ·
D=Deficiente · E=Malo · F=Reprobado.

**Severidad → etiqueta (`severityLabel`):** critical=Crítica · high=Alta ·
medium=Media · low=Baja · info=Informativa.

**Estados de scan:** `queued` → `running` → `done | partial | cancelled | error`.
Cobertura parcial capa el grado a **C**.

## Apéndice B · Endpoints BFF que disparan los flujos

| Acción (flujo) | BFF | Backend |
|---|---|---|
| Crear scan (F3) | `POST /api/owliver/scans` | `POST /v1/scans` |
| Estado del scan (F5) | `GET /api/owliver/scans/[id]` | `GET /v1/scans/{id}` |
| Stream SSE (F5) | `GET /api/owliver/scans/[id]/stream` | `GET /v1/scans/{id}/stream` |
| Cancelar (F5) | `POST /api/owliver/scans/[id]/cancel` | `POST /v1/scans/{id}/cancel` |
| Compartir (F6) | `POST /api/owliver/scans/[id]/share` | `POST /v1/scans/{id}/share` |
| Exportar PDF (F6) | `GET /api/v1/scans/{id}/report.pdf` (proxy) | backend PDF |
| Reporte público (F7) | `GET /api/r/[token]` | `GET /v1/r/{token}` |
| Sitio (F8) | `GET /api/owliver/sites/[id]` | `GET /v1/sites/{id}` |
| Ranking (F9) | `GET /api/owliver/ranking?country=mx` | `GET /v1/ranking` |
| Watchlist (F10) | `GET·POST /api/owliver/watchlist`, `PATCH·DELETE /api/owliver/watchlist/[id]` | `/v1/watchlist` |
| Alert prefs (F10/F13) | `GET·PUT /api/owliver/me/alerts` | `/v1/me/alerts` |
| Login (F11) | `POST /api/auth/login` | `POST /v1/auth/login` |
| Google start/login (F11) | `GET /api/auth/google/start`, `POST /api/auth/google-login` | `POST /v1/auth/google-login` |
| Logout / Refresh (F11/F12) | `POST /api/auth/logout`, `POST /api/auth/refresh` | `/v1/auth/*` |
| Reset (F11) | `POST /api/auth/reset-password`(+`/confirm`) | `/v1/auth/reset-password*` |
| Aceptar invitación (F11) | `POST /api/auth/invitations/[token]/accept` | `/v1/invitations/{token}/accept` |
| Crear tenant (F13) | `POST /api/tenants` | `/v1/tenants` |

---

> **Mantenimiento:** este spec refleja el código a la fecha del frontmatter.
> Si cambian rutas/copys, re-extrae con el mapeo por dominios y actualiza las
> tablas de selectores (no hay `data-testid`, así que el copy es load-bearing).
