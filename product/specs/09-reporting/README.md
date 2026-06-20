---
feature: reporting
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §11 (§11.1–§11.3); spec-gaps.md §5 (§5.3)
---

# Owliver — Reporte "Owliver te explica" + export + reporte público

> El reporte es el núcleo del producto y el clímax del pitch: un reporte interactivo in-app de **dos capas** —una capa ejecutiva en lenguaje llano redactada por Opus (grado A–F, doble gauge 🛡️/🤖, párrafo "Owliver te explica", top-3 riesgos, inventario de superficie agéntica) y una capa técnica en acordeón por finding (evidencia, impacto, remediación, referencias)— con **export a PDF** y un **link público compartible** (`/r/[token]`) que renderiza la capa ejecutiva completa y los findings técnicos **con los exploits redactados**: muestra tipo, categoría, severidad, impacto y remediación, pero nunca el payload crudo de explotación contra el sitio del usuario. Este documento especifica el **contenido y el contrato** del reporte; la superficie de renderizado (rutas, shell, sistema visual) vive en [13-frontend](../13-frontend/README.md).

## 1. Alcance y límites de ownership

Este subspec es dueño del **producto reporte**: qué muestra cada capa, cómo se redacta el párrafo "Owliver te explica", los componentes UI concretos que lo materializan, la entrega y el export a PDF, y la **redacción de exploits** del reporte público `/r/[token]`.

Lo que NO se duplica aquí (resumen de una línea + cross-ref):

- **Ruta `/r/[token]`, shell público y sistema visual del reporte** → la superficie de renderizado (route-groups, layout, design system, breakpoints) vive en [13-frontend](../13-frontend/README.md); este documento define el contenido/contrato que esa superficie pinta.
- **Semántica de los gauges y del grado A–F** (cómo se calculan los dos sub-scores y el grado, el cap a C por cobertura parcial) → ver [07-scoring](../07-scoring/README.md). Aquí solo se especifica cómo se *renderizan*.
- **Contrato del endpoint `POST /scans/{id}/share` y `GET /r/[token]`** (forma del request/response, status codes a nivel HTTP) → ver [12-api](../12-api/README.md). Aquí se especifica la semántica del token y la redacción del payload, no la forma del endpoint.
- **Inventario de superficie agéntica y el "star finding" agéntico** (cómo se detecta, `agentic_status`) → ver [03-agentic-surface](../03-agentic-surface/README.md); aquí solo cómo se presenta en el reporte.
- **Tendencia histórica** (`dedupe_key`, `first_seen`/`last_seen`, comparación entre escaneos) → la mecánica de dedupe a nivel site vive en [06-data-model](../06-data-model/README.md) y [08-ranking-watchlists](../08-ranking-watchlists/README.md); aquí solo su presentación.

## 2. Estructura del reporte: dos capas

El reporte es un **reporte interactivo in-app** organizado en **dos capas**. La capa 1 es lo primero que ve cualquier audiencia (técnica o no); la capa 2 es el detalle accionable para quien remedia.

### 2.1 Capa 1 — Ejecutiva (lenguaje llano, generada por Opus)

La capa ejecutiva está pensada para que un funcionario o dueño de sitio sin background de seguridad entienda en 30 segundos qué tan mal está y por qué importa. Contiene:

- **Grado grande A–F** renderizado arriba, en grande, más los **dos sub-scores** mostrados como gauges semicirculares: 🛡️ Web y 🤖 Agéntico.
- **Párrafo "Owliver te explica"** — redactado por Opus (ver [05-agent-team](../05-agent-team/README.md)): explica en lenguaje llano qué encontramos y por qué importa, **sin jerga**.
- **Top 3 riesgos priorizados** con su **impacto de negocio** (qué pasaría si se explota, en términos que entiende quien decide).
- **Inventario de superficie agéntica detectada** — qué chatbots / widgets de IA tiene el sitio (ver [03-agentic-surface](../03-agentic-surface/README.md)).
- **Badges de estado cuando aplique:**
  - **"IA detectada, sin auditar"** cuando `agentic_status = detected_not_tested` — el sitio tiene superficie agéntica que no pudo probarse (ver [07-scoring](../07-scoring/README.md)).
  - **"cobertura parcial"** cuando el grado quedó capado en **C** por cobertura insuficiente del escaneo (ver [07-scoring](../07-scoring/README.md)).

### 2.2 Capa 2 — Técnica (acordeón por finding)

La capa técnica es un **acordeón**: un panel colapsable por finding. Cada finding expone:

- **severidad**, **categoría OWASP/LLM**, `evidence` (payload + req/resp + screenshot), `impact`, `remediation` paso a paso, `references` (CWE/OWASP) y `confidence`.
- **Filtros** por severidad / source / categoría.
- **Tendencia histórica** (si hay escaneos previos): cómo cambió el grado y qué findings son **nuevos/resueltos**, vía `dedupe_key` + `first_seen`/`last_seen` a nivel site (mecánica en [06-data-model](../06-data-model/README.md) y [08-ranking-watchlists](../08-ranking-watchlists/README.md)).

### 2.3 El "star finding" agéntico con evidencia de canario

El finding agéntico es el diferenciador del producto y el clímax del pitch: cuando un chatbot o widget de IA del sitio fue exitosamente inyectado/jailbreakeado, el finding se destaca y su `evidence` incluye la **prueba con canario** — la evidencia de que el modelo del sitio ejecutó la instrucción inyectada (p. ej. devolvió el canario plantado). La mecánica de detección y el formato del canario son ownership de [03-agentic-surface](../03-agentic-surface/README.md); en el reporte se presenta como un finding técnico de la capa 2 con tratamiento visual destacado, y su payload de explotación queda **redactado** en el reporte público (ver §5).

## 3. Componentes UI concretos

El reporte es núcleo (ver spec.md §15) y clímax del pitch, así que los componentes base **no son opcionales**. La provisión/instalación de estos componentes en el frontend es ownership de [13-frontend](../13-frontend/README.md); aquí se fija el contrato de qué renderiza cada uno.

- **Accordion** (`npx shadcn add accordion`): un panel colapsable por finding en la Capa 2; **header** = chip de severidad + categoría + título; **body** = evidencia, impacto, remediación, referencias. (El repo trae `collapsible` pero no `accordion`; hay que instalarlo.)
- **Gauge** semicircular para los dos sub-scores: `chart.tsx` con `RadialBarChart` de recharts (`^3.6.0`, ya presente), `endAngle=180`, `Label` central con el **score numérico + grado**. Uno 🛡️ Web y uno 🤖 Agéntico.
- **Toasts** (`sonner`): feedback de acciones — compartir generado, PDF listo, errores 403/410. (El repo no trae `sonner`; hay que añadirlo.)
- El **grado global** se renderiza grande arriba; las filas de finding usan el **chip de grado/severidad** con color A–F del design system (ver [13-frontend](../13-frontend/README.md) para los tokens de color A–F).

## 4. Entrega y export

**Entrega:** página in-app (el núcleo) + **export PDF** + **link público compartible** (`/r/[token]`, respaldado por la tabla `public_reports`).

- **Export PDF:** vía **Playwright print-to-PDF** o **WeasyPrint**.
- **Screenshots de `evidence`:** se sirven desde la **ruta estática de FastAPI** (`/data/scans/{scan_id}/{n}.png`); el **PDF los embebe desde esa misma ruta**.

### 4.1 M3 — PDF/share es recortable; Plan B del demo

El export PDF y el share son **recortables** bajo presión de tiempo (hito M3). Si se recortan, el **Plan B del demo debe cubrir su ausencia mostrando la página de reporte in-app con la redacción ya aplicada**: el reporte in-app y su comportamiento de redacción (la lógica que oculta exploits) son la pieza imprescindible; el demo se hace sobre la página in-app sin depender del PDF ni del link compartible. La redacción de exploits (§5) **no es recortable** aunque su vehículo (el link público) sí lo sea, porque define cómo se comporta el reporte cuando se comparte.

## 5. Reporte público `/r/[token]` — redacción de exploits

`/r/[token]` es un **server component sin login** que renderiza:

1. la **capa ejecutiva completa** (grado, gauges, párrafo "Owliver te explica", top-3 riesgos, inventario agéntico, badges), y
2. los **findings técnicos con sus payloads de explotación redactados/ocultos por defecto**.

Se muestra **tipo, categoría, severidad, `impact` y `remediation`**, pero **no el exploit crudo**: ni el payload de prompt-injection, ni el request de sqlmap, ni el system-prompt filtrado. **El link compartible nunca debe filtrar exploits reales contra el sitio del usuario.** Esta es una regla de seguridad del producto, no una preferencia de UI: un enlace público que filtre el payload exacto convierte el reporte en un manual de ataque contra el propio sitio del usuario.

La frontera de redacción aplica a la capa técnica del reporte público:

- **Se muestra:** tipo de finding, categoría OWASP/LLM, severidad, `impact`, `remediation`, `references`, `confidence`.
- **Se oculta/redacta:** el contenido crudo de `evidence` que constituye un exploit reproducible — payload de prompt-injection, request de sqlmap, system-prompt filtrado, y en general el req/resp y payload que permitirían reejecutar el ataque. El reporte **autenticado** in-app (no público) sí muestra `evidence` completa a su dueño.

### 5.1 Manejo del token

La forma del endpoint vive en [12-api](../12-api/README.md); la semántica del token es:

- **Token inexistente** → **404**.
- **Token con `expires_at < now()` o `revoked_at` no nulo** → **410 Gone** con copy **"Este enlace expiró"**.
- **Token válido** → reporte redactado (capa ejecutiva completa + capa técnica con exploits redactados).

### 5.2 Generación y ciclo de vida del token

- El token se genera con `secrets.token_urlsafe(32)`.
- **TTL default 7 días**, settable en `POST /scans/{id}/share`.
- `revoked_at NULL` por defecto, para permitir **revocación** posterior.
- Índice **UNIQUE** sobre `public_reports(token)`.

Los errores 403/410 que surjan al consumir un link (expirado/revocado) se reportan al usuario vía **toast** (`sonner`), igual que el feedback de "compartir generado" y "PDF listo" (§3).
