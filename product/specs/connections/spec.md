---
feature: connections
type: spec
status: partial
coverage: 50
audited: 2026-06-16
---

# Especificación: Conexiones (reemplazo de "Integrations")

> Estado: Borrador para handoff a desarrollo
> Autor: brainstorming con el equipo (vía `/brainstorm`)
> Contexto del producto: **Doxiq** — plataforma de extracción de documentos y
> análisis de reglas de negocio (OCR + LLM). Backend FastAPI (Clean Arch + DDD,
> async SQLAlchemy, Temporal, background jobs). Frontend Next.js 15 / React 19 /
> Tailwind v4 / shadcn + Base UI.

---

## 1. Resumen y objetivo

Renombrar y rediseñar la actual sección **"Integrations"** (hoy un único item en
el grupo *Settings* del sidebar del workflow, que sólo configura un webhook) por
un concepto más amplio y humano: **"Conexiones" (EN: Connections)**.

"Conexiones" agrupa **dos mitades** simétricas:

- **Orígenes** (EN: *Origins*) — las fuentes **desde donde se reciben archivos**
  para procesarlos (email, WhatsApp, Drive, …).
- **Destinos** (EN: *Destinations*) — los lugares **a donde se envían los
  resultados** (Slack, WhatsApp, email, webhooks, …).

La feature reemplaza al item "Integrations" del workflow para **ambos tipos** de
workflow (STANDARD y ANALYSIS).

### Decisiones tomadas (resumen ejecutivo)

| # | Decisión | Valor elegido |
|---|----------|---------------|
| 1 | Término paraguas | **Conexiones / Connections** |
| 2 | Sub-etiquetas de las dos mitades | **Orígenes / Destinos** (EN: Origins / Destinations) |
| 3 | Estructura en el sidebar del workflow | **Grupo "Conexiones"** colapsable con dos sub-items navegables (Orígenes, Destinos), cada uno su propia página |
| 4 | Alcance de credenciales | **Cuentas a nivel organización + selección por-workflow** (todas las credenciales viven en la org; el workflow elige cuál usar y con qué parámetros) |
| 5 | Superficie de gestión org | **Nueva sección dedicada "Conexiones"** en el grupo *Plataforma*; no se tocan los items existentes "Integraciones" ni "Fuentes de datos" |
| 6 | Modelo de cuenta | **Cuenta con capacidades** (recibir / enviar / ambos); un solo registro por cuenta |
| 7 | Enrutamiento de entrada | **Identificador dedicado por workflow** (camino feliz) **+ reglas opcionales** (fase 2) |
| 8 | Disparo de salida | **Basado en eventos + envío manual** on-demand desde la UI |
| 9 | Contenido de salida | **Plantilla con tokens** para mensajería (`@doctype.campo`, `{{variable}}`, `#kb`); **JSON estructurado** para webhooks |
| 10 | Alcance MVP (fase 1) | **Orígenes: Email. Destinos: Webhook, Slack, Email.** (WhatsApp y Drive → fase 2) |
| 11 | Permisos | **Permiso dedicado `manage_connections`** para cuentas org; config por-workflow sigue al rol *admin* del workflow |
| 12 | Confiabilidad/observabilidad | **Completo**: reintentos con backoff, estado por entrega, historial navegable, "probar conexión" + estado de salud por cuenta |

---

## 2. Modelo conceptual

Dos capas:

### 2.1 Capa organización — "Conexiones" (registro de cuentas)

Un registro de **cuentas conectadas** reutilizables por todos los workflows del
tenant. Conectar una cuenta es donde viven las **credenciales sensibles**
(OAuth tokens, secretos SMTP, app tokens de Slack). Cada cuenta declara:

- **Proveedor / tipo de conector** (email, slack, webhook, whatsapp, drive…).
- **Capacidades**: `can_receive` (puede ser Origen), `can_send` (puede ser
  Destino), o ambas. Ej.: Email → ambas; Slack → solo enviar; Webhook → solo
  enviar; Drive → recibir (y enviar en fase 2).
- **Estado de salud**: `connected | error | expired | revoked`.
- **Credenciales** (cifradas, nunca expuestas crudas al frontend).

### 2.2 Capa workflow — Orígenes / Destinos (selección + parámetros)

Cada workflow **referencia** cuentas org y las parametriza para su uso concreto.
No vuelve a pedir credenciales: sólo selecciona una cuenta existente (filtrada
por capacidad) y define parámetros específicos del workflow.

- **Origen del workflow** = (cuenta org con `can_receive`) + **identificador
  dedicado** que enruta lo entrante a ESTE workflow (ver §5) + estado
  `enabled/disabled`.
- **Destino del workflow** = (cuenta org con `can_send`) + **suscripción a
  eventos** + **plantilla de contenido** (o config de payload para webhook) +
  estado `enabled/disabled`.

Un mismo origen/destino puede tener varios bindings (varios workflows usan la
misma cuenta org de email, cada uno con su alias/canal).

---

## 3. Arquitectura de información y navegación

### 3.1 Sidebar del workflow (`/workflows/[wf_slug]/…`, grupo *Settings*)

El item plano **"Integrations"** se reemplaza por un **grupo colapsable
"Conexiones"** con dos sub-items:

```
Settings
 ├─ Document Types
 ├─ Knowledge
 ├─ (Analysis Rules)      ← solo ANALYSIS
 ├─ (Synthesis)           ← solo ANALYSIS
 ├─ Conexiones            ← grupo colapsable (NUEVO, reemplaza "Integrations")
 │   ├─ Orígenes
 │   └─ Destinos
 └─ Permissions
```

- Aplica a **ambos** tipos de workflow (STANDARD y ANALYSIS).
- Técnicamente el sidebar actual (`src/presentation/workflows/shared/workflow-sidebar.tsx`)
  es una **lista plana**; hay que añadir soporte de **grupo colapsable con
  sub-items** usando los componentes shadcn `Collapsible` + `SidebarMenuSub` /
  `SidebarMenuSubItem` / `SidebarMenuSubButton`. El grupo se expande
  automáticamente cuando la ruta activa cae dentro de `connections/*`.

**Rutas nuevas** (App Router):

- `src/app/(protected)/workflows/[wf_slug]/connections/sources/page.tsx` → Orígenes
- `src/app/(protected)/workflows/[wf_slug]/connections/destinations/page.tsx` → Destinos
- (Opcional) `connections/page.tsx` → redirect a `connections/sources`.
- Cada página sigue el patrón establecido tras el último refactor: `WorkflowAppShell`
  + `PageContent` + `PageContent.Header(icon, title, subtitle, actions)` + `PageContent.Body`.
- **Migración**: la ruta actual `…/integrations` y `WebhookConfigForm` se
  **absorben** en Destinos (el webhook pasa a ser un tipo de Destino). Mantener
  `…/integrations` como redirect a `…/connections/destinations` para no romper
  enlaces/bookmarks.

### 3.2 Sidebar de plataforma (grupo *Plataforma*)

Añadir un **nuevo item "Conexiones"** (`/connections`) en el grupo *Plataforma*,
junto a Panel / Flujos / Integraciones / Conocimiento / Fuentes de datos. **No**
se modifican ni eliminan "Integraciones" ni "Fuentes de datos" existentes
(decisión #5). Esta página es el registro org de cuentas conectadas (§2.1).

- Ruta: `src/app/(protected)/connections/page.tsx`.
- Sólo visible/accionable para usuarios con el permiso `manage_connections` (§9).

---

## 4. Modelo de datos (propuesta)

> Backend: módulo DDD nuevo sugerido `connections` (separado del `integrations`
> existente, según decisión #5). Async SQLAlchemy + Alembic. Respeta el patrón
> dominio → aplicación → infraestructura → presentación.

### 4.1 `ConnectionAccount` (org / tenant level)

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUID | PK |
| `tenant_id` | UUID | FK tenant |
| `provider` | enum | `email` \| `slack` \| `webhook` \| `whatsapp` \| `drive` … |
| `display_name` | str | nombre legible que pone el admin |
| `capabilities` | set/enum | `{receive, send}` (derivadas del provider, validadas) |
| `status` | enum | `connected \| error \| expired \| revoked` |
| `credentials` | jsonb cifrado | tokens/secretos; **nunca** sale al cliente |
| `metadata` | jsonb | datos no sensibles (workspace, email base, scopes) |
| `last_health_check_at` | datetime | |
| `created_at/updated_at` | datetime | |

### 4.2 `WorkflowSourceBinding` (origen por-workflow)

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUID | PK |
| `workflow_id` | UUID | FK |
| `account_id` | UUID | FK `ConnectionAccount` (capability `receive`) |
| `enabled` | bool | |
| `routing_identifier` | str | alias email / id de carpeta Drive / keyword WhatsApp (ver §5) |
| `routing_rules` | jsonb \| null | **fase 2**: condiciones avanzadas |
| `params` | jsonb | parámetros específicos del conector |
| `created_at/updated_at` | datetime | |

### 4.3 `WorkflowDestinationBinding` (destino por-workflow)

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUID | PK |
| `workflow_id` | UUID | FK |
| `account_id` | UUID | FK `ConnectionAccount` (capability `send`) |
| `enabled` | bool | |
| `subscribed_events` | str[] | catálogo §6.1 |
| `content` | jsonb | plantilla (mensajería) o config de payload (webhook) §6.3 |
| `params` | jsonb | canal Slack, "to" de email, headers/secret de webhook… |
| `created_at/updated_at` | datetime | |

### 4.4 `DeliveryRecord` (observabilidad de salida)

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUID | PK |
| `destination_binding_id` | UUID | FK |
| `workflow_id` / `case_id` / `run_id` | UUID | contexto |
| `event` | str | evento disparador |
| `status` | enum | `pending \| sent \| failed \| retrying` |
| `attempts` | int | |
| `last_error` | str \| null | |
| `payload_snapshot` | jsonb | lo enviado (o resumen) |
| `triggered_by` | enum | `event \| manual` |
| `created_at / delivered_at` | datetime | |

> **Migración del webhook actual**: los campos `webhookUrl / webhookEnabled /
> webhookEvents` del workflow (frontend `domain/entities/workflow.ts` + backend
> enum `common/domain/enums/webhooks.py`) se migran a una `ConnectionAccount`
> tipo `webhook` (a nivel org) + un `WorkflowDestinationBinding`. Escribir
> migración de datos para no perder webhooks configurados.

---

## 5. Orígenes (entrada)

### 5.1 Enrutamiento (decisión #7: dedicado + reglas)

**Fase 1 — identificador dedicado (determinístico):**

- **Email**: cada workflow recibe un **alias dedicado** de ingreso, p. ej.
  `wf-<slug>@inbound.doxiq.app` (o sub-addressing `inbound+<token>@…`). Todo correo
  a ese alias entra a ESTE workflow. El sistema crea un **caso** por mensaje (o
  agrupa por hilo/asunto — ver §10 abierto) y adjunta los archivos del correo.
- **Drive (fase 2)**: subcarpeta dedicada que el workflow observa.
- **WhatsApp (fase 2)**: keyword o número/short-code dedicado.

**Fase 2 — reglas de enrutamiento:** condiciones opcionales (remitente, asunto,
etiqueta, carpeta) encima del identificador para casos avanzados. Documentado,
no implementado en MVP.

### 5.2 Comportamiento de entrada

- Al llegar un archivo válido por un Origen `enabled`, se crea/alimenta un **caso**
  (ANALYSIS) o se lanza el **pipeline de extracción** (STANDARD), reutilizando la
  infraestructura existente (Temporal para document processing; el upload pasa por
  `file_storage`).
- Validación de tipos de archivo soportados (reusar la lista ya usada en
  Knowledge/extracción).
- Errores de ingestión visibles en el estado del Origen y/o logs.

### 5.3 Conector MVP — Email (Origen)

- Requiere infra de **inbound email** (servicio que recibe y hace webhook al
  backend; p. ej. proveedor SMTP/inbound-parse). Definir proveedor en
  implementación.
- Config por-workflow: alias dedicado (auto-generado, copiable), opción de
  filtrar por remitentes permitidos (lista blanca) — opcional.

---

## 6. Destinos (salida)

### 6.1 Catálogo de eventos (decisión #8)

Los destinos se **suscriben a eventos** del workflow. Catálogo inicial
(type-aware):

**STANDARD** (sin Synthesis):
- `document.processed` — un documento terminó de extraerse (payload: output
  estructurado del doc).
- `document.failed`.

**ANALYSIS**:
- `case.completed`.
- `analysis_run.completed` — (ya existe en el sistema) resumen del run.
- `synthesis.ready` — narrativa + output estructurado de Synthesis listos.
- `analysis_run.failed`.

> El catálogo debe ser extensible. Cada evento define el **payload disponible**
> (qué tokens/campos puede referenciar la plantilla del destino).

### 6.2 Envío manual (decisión #8)

Desde la UI del caso/run (o desde la página de Destinos), botón **"Enviar a…"**
que dispara una entrega on-demand a un destino elegido, reutilizando su
plantilla. Queda registrado en `DeliveryRecord` con `triggered_by = manual`.

### 6.3 Contenido (decisión #9)

- **Mensajería (Slack / Email / WhatsApp)**: **plantilla configurable** por
  destino. Reutiliza el **sistema de tokens del repo**:
  - `@slug.path` → datos del caso/documento extraídos.
  - `{{variable}}` → variables de sistema (`{{now}}`, etc.).
  - `#kb_slug` → conocimiento.
  - Campos del **output de Synthesis** (según el JSON Schema declarado).
  - Reusar el editor de tokens / `MarkdownRichEditor` + `TokenChipPalette` ya
    usados en `SynthesisConfigView`.
  - Email: plantilla de **asunto** + **cuerpo** (markdown→HTML). Slack/WhatsApp:
    **mensaje** (texto/markdown; Slack puede usar bloques en fase 2).
- **Webhook**: **payload JSON estructurado** (envelope estándar: `event`,
  `workflow`, `case/run`, `data` con el output). Config: URL, secreto de firma
  (HMAC), headers custom. (Migrar `WebhookConfigForm` actual aquí.)

### 6.4 Conectores MVP

| Conector | Dirección | Cuenta org requiere | Config por-workflow |
|----------|-----------|---------------------|---------------------|
| **Webhook** | Destino | URL + secret (puede vivir como "cuenta" org reutilizable o ad-hoc) | eventos, headers, payload |
| **Slack** | Destino | OAuth app (workspace) | canal(es), plantilla mensaje, eventos |
| **Email** | Destino | cuenta de envío (SMTP/API) | "to/cc", asunto+cuerpo plantilla, eventos |
| **Email** | Origen | cuenta inbound | alias dedicado, lista blanca opcional |

---

## 7. Confiabilidad y observabilidad (decisión #12 — Completo)

- **Reintentos con backoff exponencial** para entregas fallidas (usar la infra de
  background jobs del backend; cada entrega es un job idempotente).
- **Estado por entrega** (`DeliveryRecord`): `pending / retrying / sent / failed`.
- **Historial navegable** de entregas por workflow (y por destino), con detalle
  de error y payload snapshot. UI: tabla/lista filtrable.
- **"Probar conexión"** por cuenta org (envía un ping/mensaje de prueba) y por
  destino del workflow.
- **Estado de salud** por `ConnectionAccount` (`connected/error/expired/revoked`)
  con chequeo periódico y refresco de tokens OAuth; banner/badge en la UI cuando
  una cuenta requiere reautenticación.

---

## 8. UI/UX

- Seguir `PRODUCT.md` / `DESIGN.md` (teal primary, Figtree + Geist Mono, near-flat,
  "The Inspection Bench").
- **Patrón obligatorio BFF** (ver `CLAUDE.md`): todo fetch del cliente va a una
  ruta `/api/...` de Next.js (BFF) que reenvía con `serverHttp` / proxy; **nunca**
  fetch directo al backend desde el cliente. Las credenciales OAuth y secretos se
  manejan server-side.
- **Página Orígenes (workflow)**: header con acción "Añadir origen" → selector de
  cuentas org con capacidad `receive`; lista de orígenes configurados con su alias
  dedicado (copiable), estado enabled, estado de ingestión.
- **Página Destinos (workflow)**: header con acción "Añadir destino" → selector de
  cuentas org con capacidad `send`; por destino: eventos suscritos, editor de
  plantilla/payload, toggle enabled, "probar", y acceso al historial de entregas.
- **Página Conexiones (org)**: lista de cuentas conectadas con su tipo,
  capacidades, estado de salud; flujo "Conectar cuenta" (OAuth para Slack/Drive;
  formularios para email/webhook); editar/revocar. Gated por `manage_connections`.
- **Estados vacíos** claros (reusar `EmptyState`).

---

## 9. Permisos (decisión #11)

- **Nuevo permiso `manage_connections`** (asignable por rol, a nivel org/tenant):
  habilita ver y gestionar la sección org **Conexiones** (conectar/editar/revocar
  cuentas, ver credenciales-metadata, probar conexión). Independiente del rol de
  workflow.
- **Config por-workflow** (Orígenes/Destinos: seleccionar cuenta, plantillas,
  eventos, enable/disable): permitida al rol **admin del workflow** (sistema de
  permisos de workflow ya existente: admin/member/viewer). Los miembros sin admin
  ven en sólo-lectura.
- En ningún caso el frontend recibe credenciales crudas.

---

## 10. Alcance: Fase 1 (MVP) vs Fase 2

**Fase 1 (MVP):**
- Sección org **Conexiones** + permiso `manage_connections`.
- Grupo **Conexiones** (Orígenes/Destinos) en el sidebar del workflow (ambos tipos).
- **Orígenes**: Email (alias dedicado).
- **Destinos**: Webhook (migrado), Slack (OAuth), Email.
- Disparo por eventos + envío manual.
- Plantillas con tokens (mensajería) + payload JSON (webhook).
- Confiabilidad completa: reintentos, estados, historial, salud, probar conexión.
- Migración de webhooks existentes.

**Fase 2 (documentado, no implementado):**
- Orígenes: **WhatsApp**, **Drive**.
- Destinos: **WhatsApp**.
- **Reglas de enrutamiento** avanzadas en Orígenes.
- Adjuntos en Destinos (PDF del caso, JSON del output, documentos originales).
- Bloques enriquecidos de Slack.

---

## 11. Consideraciones de implementación (backend)

- Módulo DDD nuevo `connections` (`domain/ → application/ → infrastructure/ →
  presentation/`). Use cases como dataclasses con `execute()`; repos abstractos
  en `domain/`, SQL en `infrastructure/`; presenters snake→camel; endpoints vía
  `add_api_route()`; excepciones extienden `DomainError`.
- **Ingestión (Orígenes)**: endpoint(s) que reciben del proveedor inbound
  (email parse webhook) → crean caso/lanzan pipeline (Temporal/extraction).
- **Entrega (Destinos)**: emisor de eventos del workflow → encola jobs de entrega
  (background jobs con reintentos) → adaptadores por proveedor (webhook/slack/email).
- **Cifrado** de credenciales en reposo. Refresh de tokens OAuth.
- Reusar `messaging` / `file_storage` / `extraction` / Temporal existentes.

---

## 12. i18n (EN / ES)

| Clave (sugerida) | EN | ES |
|------|----|----|
| `Connections.title` | Connections | Conexiones |
| `Connections.sources` | Origins | Orígenes |
| `Connections.destinations` | Destinations | Destinos |
| `Connections.addSource` | Add origin | Añadir origen |
| `Connections.addDestination` | Add destination | Añadir destino |
| `Connections.testConnection` | Test connection | Probar conexión |
| `Connections.deliveryHistory` | Delivery history | Historial de entregas |
| `Connections.health.connected` | Connected | Conectada |
| `Connections.health.expired` | Reauth required | Requiere reautenticación |

> El sidebar hoy usa labels hardcodeados; al introducir grupos puede migrarse a
> i18n o mantener hardcode consistente con el resto (decidir en implementación).

---

## 13. Criterios de aceptación (MVP)

1. El item "Integrations" del sidebar del workflow ya no existe; en su lugar hay
   un grupo colapsable **Conexiones** con **Orígenes** y **Destinos**, en STANDARD
   y ANALYSIS. `…/integrations` redirige a `…/connections/destinations`.
2. Existe una sección org **Conexiones** (`/connections`) visible sólo con
   `manage_connections`, donde se conectan cuentas (Webhook, Slack OAuth, Email).
3. Una cuenta org con capacidad `receive` puede seleccionarse como **Origen** de
   un workflow y obtiene un **alias dedicado** que enruta correos a ese workflow,
   creando casos/lanzando extracción.
4. Una cuenta org con capacidad `send` puede seleccionarse como **Destino**,
   suscribirse a eventos y definir su contenido (plantilla con tokens o payload
   JSON). Al ocurrir el evento, se entrega; también puede dispararse manualmente.
5. Las entregas reintentan con backoff; su estado e historial son visibles; se
   puede "probar conexión"; la salud de cada cuenta se refleja en la UI.
6. Los webhooks previamente configurados siguen funcionando tras la migración.
7. Ningún flujo del cliente hace fetch directo al backend ni recibe credenciales
   crudas (patrón BFF respetado).

---

## 14. Preguntas abiertas / decisiones diferidas

- **Email Origen**: ¿un caso por mensaje, o agrupar por hilo/asunto? ¿Proveedor de
  inbound email (SMTP, SendGrid Inbound Parse, Mailgun Routes, propio)?
- **Webhook como "cuenta org"**: ¿se modela como cuenta reutilizable o se permite
  también ad-hoc por-workflow? (Spec asume cuenta reutilizable, con posibilidad
  ad-hoc.)
- **Slack**: ¿una cuenta = un workspace; múltiples canales por destino?
- **Retención** del historial de entregas y de `payload_snapshot` (privacidad/coste).
- ¿Migrar los labels del sidebar a i18n en este trabajo o mantener hardcode?
