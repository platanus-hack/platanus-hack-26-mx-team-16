# Prompt para Claude (diseño de UI) — Owliver 🦉

> Copia todo lo que está debajo de la línea y pégalo en Claude (modo diseño /
> artifacts). Es un brief autocontenido: describe la app, la dirección visual,
> cada pantalla, los flujos y los momentos "wow". El copy va en **español (es-MX)**
> a propósito — úsalo literal, no inventes texto de relleno.

---

Eres un **diseñador de producto senior** especializado en herramientas de
seguridad y dashboards de datos. Diseña la **interfaz web completa de Owliver**:
una app de pentesting automático orquestado por agentes de IA. Entrega pantallas
de alta fidelidad, responsive (desktop-first, con su versión móvil), listas para
implementar en **Next.js + Tailwind + shadcn/ui**.

## 1. Qué es Owliver

**Owliver 🦉 es el búho que vigila la seguridad de los sitios web.** El usuario
ingresa una URL + un nivel de ataque, un equipo de agentes de IA ejecuta un
pentest automático y se genera un reporte **ultra fácil de entender pero
técnicamente valioso**, con un **grado A–F** estilo Mozilla Observatory.

El diferenciador único: además del OWASP clásico (web), Owliver **audita la
superficie agéntica** — los chatbots, cajas de prompt y widgets de IA embebidos
en los sitios — buscando *prompt injection* y *jailbreaks*. Casi nadie mide eso
hoy.

Los resultados alimentan un **ranking público de sitios del Estado mexicano
(`.gob.mx`)** — un "Hall of Shame" cívico — y **watchlists privadas** para
monitoreo continuo.

- **Usuarios:** ciudadanos curiosos, periodistas, equipos de seguridad, devs.
- **Personalidad de marca:** **afilada, confiable, cercana.** North star: *"La
  mesa de inspección"* (the inspection bench) — rigor técnico presentado con
  claridad.
- **Anti-referencias (evítalas):** plantillas SaaS genéricas, el look "app de IA"
  trendy y morado, el desorden de software enterprise legacy.
- **Lema de cierre:** *"Owliver vigila la seguridad del Estado y de tu IA — lo que
  nadie más está midiendo."*

## 2. Dirección visual — "claro de día, SOC de noche"

Dos modos que **conviven** (no es un toggle del usuario):

**A) App shell — claro, institucional, confiable (default).**
La mayor parte de la app (leaderboard, formulario, reporte, login) vive aquí.
Cool-gray + teal, limpio, casi plano (anillos hairline + sombras whisper), con un
acento **ámbar/oro = "los ojos del búho"** para CTAs y acentos vivos.

```
Primary (teal, marca/confianza): oklch(0.59 0.095 180.54)
Texto (ink):                     oklch(0.222 0.029 253.225)
Fondo app (surface):             oklch(0.984 0.002 252.121)
Card:                            oklch(1 0 0)
Acento (ámbar, ojos del búho):   oklch(0.78 0.15 75)
```

**B) Live-view / "theater" — oscuro, "war room" / sala de operaciones (SOC).**
SOLO la pantalla de escaneo en vivo entra en este modo: near-black azulado,
telemetría, monoespaciada, scanlines sutiles, neón **funcional** (no decorativo).

```
Fondo SOC (near-black):          oklch(0.16 0.02 250)
Líneas/scanlines:                oklch(0.24 0.02 250)
Cian (actividad en curso):       oklch(0.80 0.13 195)
Ámbar (herramienta corriendo):   oklch(0.80 0.14 75)
Rojo (finding crítico, pulse):   oklch(0.64 0.22 25)
```

**Escala de grados A–F** — única fuente de color para chips, gauges y filas:

```
A (≥90) verde       oklch(0.72 0.16 150)   — seguro
B (≥80) verde-lima  oklch(0.75 0.15 130)
C (≥70) ámbar       oklch(0.80 0.14 90)
D (≥60) naranja     oklch(0.72 0.16 55)
E (≥40) naranja-rojo oklch(0.66 0.19 35)
F (<40) rojo        oklch(0.58 0.22 25)    — "hall of shame"
```

- **Tipografía:** **Figtree** para UI; **Geist Mono** para telemetría, payloads,
  evidencia y **todos los scores/grados** (lectura tipo "instrumento de medición").
- **Mascota 🦉:** el búho es un **indicador de actividad**, no clipart. Tres
  estados: dormido (idle), vigilando/girando la cabeza (running), alerta —ojos
  ámbar encendidos— (encontró algo).
- **Motion:** los grados hacen *count-up*; los gauges animan de 0 al valor; los
  findings entran con *fade + slide* corto; los findings críticos **laten** una
  vez en rojo. Respeta `prefers-reduced-motion`.
- **Radio** base ~12px. Iconografía con foco visible, contraste AA en ambos modos.

## 3. Pantallas a diseñar

Diseña estas pantallas. Para cada una respeta el layout, los componentes, los
estados y el copy indicado.

### 3.1 — Hall of Shame · Leaderboard (`/`) 🔴 — PORTADA

El gancho viral. "El Estado bajo la lupa": ranking de sitios `.gob.mx`, **peores
primero**, poblado desde el segundo cero.

- **Hero provocador:** titular grande **"¿Qué tan segura es la IA del gobierno?"**,
  subcopy con un contador ("**128 sitios auditados · 41 reprobados (grado F)**").
  Micro-copy de defensa legal, discreto: *"Datos 100% pasivos y públicos —
  equivalente a Mozilla Observatory / SSL Labs. No intrusivo."*
- **CTA primario** (ámbar): **"Audita cualquier URL →"**.
- **Tabla/cards de ranking**, cada fila:
  - Posición + **grado grande A–F** (monoespaciado, color de escala).
  - Nombre de la dependencia + hostname (ej. *Servicio de Administración
    Tributaria · sat.gob.mx*).
  - **Doble medidor** lado a lado: **🛡️ Web** vs **🤖 Agéntico** — el contraste es
    el diferenciador. Incluye una fila estrella tipo **SAT: "C web / F agéntico"**.
  - Badges cuando aplique: **"IA detectada, sin auditar"** (cuando hay chatbot
    pero no se probó) y **"cobertura parcial"**.
  - Valor de penalización cruda + tendencia (▲ ▼ vs el escaneo previo).
- **Filtros:** por grado, por peor dimensión (web/agéntico), por país (MX).
- **Estados:** skeleton de filas al cargar; las filas en **F** dominan la pantalla
  (rojo). Al cargar, los grados hacen count-up y las F laten una vez.

### 3.2 — Formulario de escaneo + gate de atestación (`/scan` o modal)

Entrada universal: URL + nivel. Es el **control legal** convertido en UI.

- **Input de URL** grande, con validación, que muestra el `host` detectado.
- **Selector de nivel** = 3 cards:
  - **Básico** — *pasivo, no intrusivo, anónimo, sin permisos.* (default)
  - **Intermedio** — *activo suave, rate-limited.*
  - **Avanzado** — *explotación, requiere autorización.*
  Cada card explica en lenguaje llano qué hace.
- **Gate de atestación** (aparece SOLO si el nivel es activo):
  - Advertencia prominente: ***"Vas a lanzar pruebas intrusivas contra {host};
    hacerlo sin autorización es ilegal."***
  - **Checkbox obligatorio:** *"Declaro tener autorización para auditar este
    dominio."* + aceptar términos. Sin marcarlo, el botón queda deshabilitado.
  - Si el host es `.gob.mx`: **advertencia reforzada en rojo** ("Sitio del Estado:
    el escaneo activo automático está prohibido; solo se permite pasivo"). Para
    gov + activo, error inline: *"Los sitios gob.mx solo admiten escaneo pasivo."*
- **Estados:** validación inline; botón en loading; error de validación claro.
- **Flujo:** al enviar → redirige a la pantalla de escaneo en vivo (3.3).

### 3.3 — ★ Live Pentest Theater (`/scans/[id]`) 🌑 — EL CENTERPIECE

**El momento cinematográfico.** Aquí Owliver deja de ser un formulario y se
convierte en un búho cazando en vivo. **Modo SOC oscuro.** Es la pantalla que más
debe impresionar.

- **Header:** host objetivo + nivel + **grado en construcción** (placeholder) +
  **barra de progreso 0–100** con fase legible ("Detectando tecnologías…",
  "Sondeando chatbot…") + **timer** (tranquiliza: "< 90s").
- **Dos carriles de agente lado a lado**, cada uno con su 🦉:
  - **🛡️ OWASP Scanner** — fila de **chips de herramientas** (nuclei, zap, testssl,
    nikto, sqlmap…) que **se encienden** (ámbar, pulsando) mientras corren y **se
    apagan** (verde = ok, rojo = falló/timeout).
  - **🤖 Agentic Surface Auditor** — fases: *detección → inventario → sondas.*
    Muestra el chatbot detectado (vendor + modelo inferido) y cada probe lanzado.
- **Feed de findings en vivo** (columna central/derecha): cada finding **cae** con
  fade+slide — chip de severidad + categoría (OWASP A01–A10 / LLM01–LLM10) +
  título. Los **críticos laten en rojo**.
- **Telemetría inferior:** los dos scores parciales (🛡️/🤖) subiendo/bajando en
  vivo + un **log monoespaciado estilo terminal**, scrolleable.
- **Botón Cancelar** (mata el escaneo). **Cierre:** cuando termina, botón grande
  **"Ver reporte completo →"**.
- **Estados:** en cola (🦉 dormido), corriendo (theater activo), cobertura parcial
  (banner), error (muestra detalle), cancelado. **Al recargar la página, el
  progreso se repinta completo** (no queda vacío) — diséñalo asumiendo replay.
- **Sensación objetivo:** tensión, "estoy viendo a la IA atacar". Chips
  encendiéndose + findings cayendo + el rojo del crítico.

### 3.4 — Reporte "Owliver te explica" (`/scans/[id]/report`) — EL PAYOFF

Vuelve al **modo claro** (lectura/confianza). Reporte interactivo de **dos capas**.

- **Capa 1 — Ejecutiva:**
  - **Grado grande A–F** arriba (count-up) + **dos gauges semicirculares**:
    **🛡️ Web** y **🤖 Agéntico**, con el score numérico + grado al centro.
  - Párrafo **"Owliver te explica"** — qué encontramos y por qué importa, sin
    jerga, tono cercano.
  - **Top 3 riesgos** priorizados con su **impacto de negocio**.
  - **Inventario de superficie agéntica:** qué chatbots/IA tiene el sitio (vendor,
    modelo inferido o "modelo no expuesto").
  - Badges: "IA detectada, sin auditar" / "cobertura parcial".
- **Capa 2 — Técnica (acordeón, un panel por finding):**
  - Header del panel = chip de severidad + categoría OWASP/LLM + título.
  - Cuerpo = **evidencia** (payload + request/response + screenshot), **impacto**,
    **remediación** paso a paso, **referencias** (CWE/OWASP), nivel de confianza.
  - **El finding agéntico estrella:** *system-prompt leak* del chatbot con su
    **canary** (token secreto filtrado) en un **bloque monoespaciado destacado** —
    evidencia incontestable. Resáltalo visualmente.
  - **Filtros** por severidad / dimensión / categoría.
  - **Tendencia histórica** si hay escaneos previos (cómo cambió el grado, qué
    findings son nuevos/resueltos).
- **Acciones:** **Exportar PDF** · **Compartir** (genera un link público).

### 3.5 — Reporte público compartido (`/r/[token]`)

Link sin login, **seguro para difundir** (el gancho viral del Hall of Shame).

- Renderiza la **capa ejecutiva completa** + los findings técnicos **con los
  exploits redactados/ocultos** (muestra tipo, severidad, impacto, remediación;
  **nunca** el payload crudo). Diseña el estado "exploit redactado" (candado +
  *"Oculto en el reporte público"*).
- **Estados:** link inexistente → 404; link expirado/revocado → pantalla **"Este
  enlace expiró"**.
- Banner para compartir en redes (ver Report Card, 3.9).

### 3.6 — Histórico del sitio (`/sites/[id]`)

Vista por dominio: encabezado (host, badge gov, grado actual), **línea de tiempo**
de escaneos (grado por fecha), **gráfico de tendencia** del grado, enlace al
reporte de cada escaneo.

### 3.7 — Magic-link · Auth (4 pantallas)

Flujo de login sin contraseña, minimalista, en modo claro:
1. **Pedir email** — input + botón "Enviar enlace".
2. **"Revisa tu correo"** — confirmación, con reenvío + cooldown visible.
3. **Verificando** — landing del callback (estados: verificando / ok / token
   inválido o expirado).
4. **Sesión iniciada** — éxito, redirige a la watchlist o al destino pendiente.

### 3.8 — Watchlist + monitoreo (`/watchlist`, requiere sesión)

Lista de dominios vigilados: cada uno con grado actual + tendencia + **toggle de
monitoreo** (re-escaneo periódico). Botón "Agregar dominio". Acceso a correr
escaneo activo. Ajustes de alertas (email / Slack). Estado vacío: *"Agrega tu
primer dominio para vigilarlo."*

### 3.9 — (Opcional) Report Card compartible

Imagen tipo **"boletín de calificaciones"** generada para compartir: grado grande
A–F + medidores 🛡️/🤖 + nombre de la dependencia + marca Owliver. Es lo que
aparece al pegar un link de `/r/[token]` en redes. Diséñala con la **F roja** bien
visible — es el hook viral #1.

## 4. Flujos clave a representar

1. **Auditar una URL (camino feliz):** `/` → CTA "Audita una URL" → formulario
   (nivel básico, sin gate) → escaneo en vivo (theater) → "Ver reporte" →
   reporte → "Compartir" → link público.
2. **Escaneo activo con atestación:** formulario → elige "Avanzado" → aparece el
   gate (advertencia + checkbox) → (si no hay sesión) magic-link → de vuelta al
   escaneo.
3. **Ver el ataque en vivo + recargar:** theater corriendo → el usuario recarga →
   el progreso se repinta completo desde el inicio (replay) → termina → reporte.
4. **Explorar el Hall of Shame:** `/` → filtra por grado F → entra a una fila
   (SAT) → ve su reporte público → comparte la Report Card.
5. **Vigilancia:** login → watchlist → agrega dominio → activa monitoreo.

## 5. Momentos "wow" (dónde concentrar el esfuerzo)

1. **El Live Pentest Theater** (3.3) — la pantalla insignia. Debe sentirse como
   una sala de operaciones real: herramientas encendiéndose, findings cayendo,
   tensión creciente, el búho trabajando.
2. **El reveal del reporte** (3.4) — los dos gauges animando + el grado grande +
   el finding agéntico estrella con su canary como prueba irrefutable.
3. **El Hall of Shame** (3.1) — un muro de grados donde el rojo domina; "el Estado
   reprobado", ordenado de peor a mejor, listo para compartir.

## 6. Entregables

- Pantallas de alta fidelidad para las secciones 3.1–3.8 (3.9 opcional), en
  **desktop** y una variante **móvil** de las 3 principales (Hall of Shame,
  Theater, Reporte).
- Un **mini design system** visible: tokens de color (claro + SOC + escala A–F),
  tipografía, y los componentes reutilizables: GradeBadge (A–F), SeverityChip,
  Gauge semicircular, ToolChip (encendido/apagado), AgentLane, FindingFeedItem,
  AttestationGate, OwlMascot (3 estados), barra de progreso de escaneo.
- Estados de cada pantalla: loading (skeletons, no spinners), vacío, error
  (404/410/422), cobertura parcial.

Copy en **español (es-MX)**, tono afilado-confiable-cercano. Usa los textos
literales de este brief; no rellenes con lorem ipsum.
