---
feature: connections
type: plan
status: implemented
coverage: 90
audited: 2026-06-16
---

# Plan: Conexiones de entrada y salida (Sources & Destinations)

> Estado: **borrador para decisión**. Las secciones marcadas con 🟡 son
> decisiones abiertas (ver §9). El resto refleja la recomendación.
> Specs relacionadas: `product/specs/connections/spec.md`, `product/specs/source-webhooks/_archive/spec.md`,
> `product/specs/source-webhooks/standard-webhooks.md`.

## 1. Objetivo

Modelar y construir el sistema de **conexiones de un workflow**: por dónde
**entran** archivos al workflow (sources) y a dónde **sale** el resultado del
procesamiento (destinations). Implementar **HTTP webhooks primero** (source +
destination), dejando los demás providers como TODO con el modelo ya preparado.

## 2. Requisitos (del usuario)

### Entradas (sources) — recibir archivos para mandarlos a un workflow
- **Webhook** — estilo n8n, pero protegido por **API key o secreto**.
- **Drive** — una carpeta; cada archivo subido llega a un workflow. La config
  de la conexión debe persistir.
- **Email** — un alias de correo; cada correo entrante carga su **body +
  attachments** en el workflow.
- **WhatsApp** — un número configurado vía [kapso.com](https://kapso.com); los
  incumbentes envían archivos a ese número y se cargan en el workflow.
- **Slack** — ❌ NO se soporta como entrada.

### Salidas (destinations) — enviar el resultado del procesamiento
La forma del payload depende del **tipo de workflow**:
- **STANDARD** → datos de la extracción: `WorkflowDocumentSet` vía presenter,
  con el JSON extraído por documento (`workflow_documents`).
- **ANALYSIS** → el **esquema configurado en el output** del workflow.

Integraciones de salida (en orden de prioridad):
1. **HTTP** — uno o más destination webhooks, cada uno con su `secret`, estilo
   Stripe (firma + reintentos).
2. **Drive** — depositar los outputs como archivos JSON en un Drive configurado.
3. **Slack** — notificar (a) cuando alguien carga un documento en un workflow
   (requiere un evento de ingesta que **aún no existe** en el catálogo §5) y
   (b) cuando termina el procesamiento (`document.extracted` para STANDARD /
   `analysis_run.completed` para ANALYSIS).

## 3. Insight de modelado: por qué `ConnectionAccount` (y por qué NO para webhook)

La pregunta de fondo era: *¿usar un registro org-level (`ConnectionAccount`) o
config per-workflow estilo n8n (`WebhookDestination`)?*

La respuesta sale de la **naturaleza de la credencial** de cada provider:

| Provider | Dirección | ¿Credencial reutilizable a nivel org? | Modelo |
|---|---|---|---|
| Webhook | source + dest | **No** — source: token+api_key/hmac que generamos; dest: URL+secret del cliente | **Inline** (per-workflow) |
| Drive | source + dest | **Sí** — token OAuth caro y reusable; carpeta por-binding | `ConnectionAccount` + binding |
| Email | source | **Sí** — mailbox/dominio org; alias por-binding | `ConnectionAccount` + binding |
| WhatsApp | source | **Sí** — API key de kapso + número, org-level | `ConnectionAccount` + binding |
| Slack | dest | **Sí** — token OAuth del workspace, org-level | `ConnectionAccount` + binding |

**Esto es exactamente cómo funciona n8n**: tiene *Credentials* (reutilizables,
encriptadas, compartidas entre workflows = `ConnectionAccount`) y *parámetros del
nodo* (per-workflow = el binding). Su nodo *Webhook* es inline porque un webhook
no tiene credencial reutilizable.

→ **Modelo híbrido**: el webhook va inline (`account_id = NULL`); Drive / Email /
WhatsApp / Slack referencian un `ConnectionAccount`. No re-pedimos credenciales
por workflow, y rotar un token OAuth en un solo lugar arregla todos los workflows.

### 3.1 Relación con las specs existentes (este plan las supersede)

- **`product/specs/connections/spec.md §4.4`** planeaba migrar el webhook actual a una
  `ConnectionAccount` tipo `webhook` (org) + `WorkflowDestinationBinding`. **Lo
  invertimos** (D2): el webhook queda **per-workflow inline** (`account_id = NULL`)
  porque no aporta credencial org reutilizable. `ConnectionAccount` se reserva
  para Drive/Email/WhatsApp/Slack. → Actualizar/marcar esa sección como superseded.
- **Nombres de tablas**: los `WorkflowSourceBinding` / `WorkflowDestinationBinding`
  de la spec connections y la `source_webhooks` de la spec source_webhooks se
  unifican aquí como **`workflow_sources`** y **`workflow_destinations`**:
  - `workflow_destinations` ≡ la actual `webhook_destinations` **generalizada**
    (rename in-place, ver D4).
  - `workflow_sources` ≡ la `source_webhooks` diseñada, **generalizada** a más
    providers.

## 4. Modelo de datos (DECIDIDO — D1: dos tablas)

Tres capas. **D1 zanjado**: una tabla por dirección (`workflow_sources` /
`workflow_destinations`), cada una con `provider` + `config` jsonb +
`account_id` nullable. Webhook va inline (`account_id = NULL`); los providers
OAuth referencian un `ConnectionAccount`.

### Capa 1 — `connection_accounts` (org) — YA EXISTE
`backend/src/common/database/models/connection_account.py` · CRUD ya implementado
en el módulo `connections`. **Sin consumidores hoy.**
- `provider`: `WEBHOOK* | DRIVE | EMAIL | WHATSAPP | SLACK`
- `capabilities`: `[RECEIVE, SEND]`
- `status`: `CONNECTED | ERROR | EXPIRED | REVOKED` (salud de la credencial)
- `config` jsonb (metadata no sensible: workspace, scopes, número…)
- `secret` String(512) (token OAuth / api key del provider; **nunca** se serializa)
- Scope: `tenant_id` (org)
- (*) WEBHOOK existe hoy en el enum `ConnectionProvider`
  (`common/domain/enums/connections.py`) con capability `SEND`, pero por D2 **no
  usa esta capa** (va inline, `account_id = NULL`). Candidato a eliminarse del enum.

### Capa 2 — Bindings per-workflow

**`workflow_sources`** (entrada) — generaliza la `source_webhooks` diseñada en spec:
- `workflow_id`, `tenant_id`
- `provider`: `WEBHOOK | DRIVE | EMAIL | WHATSAPP`
- `account_id`: FK→`connection_accounts` **nullable** (NULL para WEBHOOK)
- `config` jsonb — identidad de entrada según provider:
  - WEBHOOK: `{ token (público ruteable, prefijo src_), auth_mode,
    api_key (dxk_, hasheable), hmac_secret (whsec_) }` — ver auth §6 y prefijos §7
    (D3: API key **y** HMAC soportados)
  - DRIVE: `{ folder_id }` · EMAIL: `{ alias }` · WHATSAPP: `{ number }`
- `enabled`
- Índice único sobre la identidad ruteable (token / alias / number / folder)
  para resolver `inbound → workflow` (ver **D7**: promover la identidad ruteable
  a columna dedicada en vez de indexar dentro de `config` jsonb).

**`workflow_destinations`** (salida) — generaliza la `webhook_destinations` actual:
- `workflow_id`, `tenant_id`
- `provider`: `WEBHOOK | DRIVE | SLACK`
- `account_id`: FK→`connection_accounts` **nullable** (NULL para WEBHOOK)
- `subscribed_events`: jsonb (catálogo §5; default derivado del tipo de workflow, ver **D8**)
- `config` jsonb — destino + payload según provider:
  - WEBHOOK: `{ url, secret, api_version }`
  - DRIVE: `{ folder_id }` · SLACK: `{ channel }`
- `enabled`

### Capa 3 — `workflow_events` (log de entrega) — YA EXISTE
`destination_id` pasa a apuntar a `workflow_destinations` (renombrada). Log
genérico de intentos de entrega (status, response, retries) para todo provider.

## 5. Catálogo de eventos y payloads

Orientado por el tipo de workflow:

| Tipo | Eventos | Payload |
|---|---|---|
| STANDARD | `document.extracted`, `document.failed` (por documento) | `WorkflowDocumentSet` presenter + JSON de cada `workflow_document` |
| ANALYSIS | `analysis_run.completed` (resumen, **sin** eventos por-doc) | Esquema configurado en el output del workflow |

> Decisión ya zanjada (memoria `project_analysis_webhooks`): ANALYSIS emite solo
> el resumen `analysis_run.completed`, no eventos por documento.

> **Estado del catálogo** (`common/domain/enums/webhooks.py`, `WebhookEventType`):
> hoy solo existen `document.extracted` y `document.failed`. **`analysis_run.completed`
> aún NO está en el enum** — se agrega en la Fase 3 junto con el builder ANALYSIS.

> **Hueco conocido — evento de ingesta:** todos los eventos del catálogo son
> *post-procesamiento*. El requisito de Slack §2(a) (notificar **al cargar** un
> documento) no tiene evento aquí; queda fuera de alcance hasta definir un
> `document.received` (o similar) cuando se implemente el adapter Slack (Fase 5).

El **payload lo construye el dispatcher según el tipo de workflow**, no según la
config del destination — el destination solo elige a qué eventos se suscribe.

## 6. Alcance de la primera entrega

**SÍ ahora (HTTP webhooks):**
- **Source webhook**: endpoint público `/v1/ingest/{token}` que resuelve
  `token → workflow_source → workflow`, descarga archivos a S3 y dispara el
  pipeline Temporal existente. Solo `provider=WEBHOOK` activo. **Auth (D3): se
  soportan ambos** — `X-Api-Key: dxk_…` (verificar contra hash) **y** firma HMAC
  del body con `hmac_secret` + timestamp anti-replay. Cada source declara su
  `auth_mode` (`api_key | hmac | both`); default `api_key`.
- **Destination webhook**: ya casi existe (`webhook_destinations` +
  `dispatch_webhooks.py` + `deliver_webhook`). Generalizar la tabla (agregar
  `provider`, `account_id` nullable) manteniendo activo solo el path WEBHOOK.

**TODO (modelo preparado, sin adapter):** DRIVE / EMAIL / WHATSAPP (source) y
DRIVE / SLACK (dest). El enum + `config` jsonb + `account_id` ya los soportan;
falta cada adapter de ingesta/entrega y el flujo OAuth/kapso.

## 7. Reuso de infraestructura existente
- **SSRF / validación de URL**: `common/application/helpers/webhooks/url_validation.py`
  (entrega destination; y source si en el futuro descarga archivos por URL).
- **Firma + POST + retry/backoff**: `common/application/helpers/webhooks/{signing,delivery}.py`.
- **Pipeline de ingesta**: S3 + workflows Temporal existentes (source).
- **Secreto revelable + rotación** (patrón repetido: `webhook_destination.secret`
  y `tenant.webhook_signature_key` ya existen; `workflow_sources.api_key` +
  `hmac_secret` son nuevos): extraer a un value-object/mixin compartido —
  generar con prefijo, `String(512)`, `reveal`/`regenerate`, presenter `hasX`.
  Hoy el generador `whsec_` vive en `signing.py` (`generate_webhook_secret`,
  `SECRET_PREFIX = "whsec_"`) pero `tenant` lo **inlinea aparte** — el VO unifica eso.
  **Esquema de prefijos:** `whsec_` = secreto de firma HMAC (firma saliente del
  destination **y** verificación entrante del source HMAC) · `dxk_` = API key del
  source (a implementar, hoy solo en spec) · `src_` = token público ruteable del
  source. Primer paso de bajo riesgo; lo reusan ambos lados.

## 8. Fases de implementación

0. **Groundwork** — VO "secreto revelable + rotación" compartido.
1. **Generalizar `workflow_destinations`** — migración in-place de
   `webhook_destinations` (+`provider` default WEBHOOK, +`account_id` nullable),
   rename de tabla; redirigir `dispatch_webhooks` y `workflow_events.destination_id`.
   Comportamiento WEBHOOK idéntico al actual.
2. **`workflow_sources` + ingest webhook** — tabla, repo, CRUD per-workflow,
   endpoint `/v1/ingest/{token}`, auth, descarga→S3, disparo del pipeline.
3. **Payload por tipo** — agregar `analysis_run.completed` a `WebhookEventType`
   (`common/domain/enums/webhooks.py`); builder STANDARD (eventos por-doc, presenter
   `WorkflowDocumentSet` + JSON de cada `workflow_document`) vs ANALYSIS (resumen
   `analysis_run.completed`, esquema configurado en el output). Aplica a HTTP webhook
   (ambos tipos de workflow entran en la primera entrega).
4. **Wire `ConnectionAccount` → bindings** — `account_id` resoluble; UI de
   selección de cuenta por-workflow (sin re-pedir credenciales).
5. **TODO providers** — adapters Drive/Email/WhatsApp/Slack, uno por uno.

## 9. Decisiones

Resueltas:
- **D1 ✅ Dos tablas** — `workflow_sources` / `workflow_destinations`, cada una con
  `provider` + `config` jsonb + `account_id` nullable.
- **D2 ✅ Destination webhook per-workflow inline** — url+secret en la fila del
  destination, `account_id = NULL`. (Org-reutilizable estilo Stripe descartado.)
- **D3 ✅ Source auth: API key y HMAC** — ambos soportados, `auth_mode` por source.

Abiertas (no bloquean el arranque):
- **D4 — migración de `webhook_destinations`**: recomendado **in-place**
  (ALTER `+provider` default WEBHOOK, `+account_id` nullable, rename →
  `workflow_destinations`) en vez de tabla nueva + migración de datos.
- **D5 — módulo de los bindings**: `connections` (junto a accounts) vs `workflows`.
  Recomendado: `connections`.
- **D6 (detalle) — default de `auth_mode`** para nuevos source webhooks
  (`api_key` propuesto) y si la UI permite exigir HMAC obligatorio por source.
- **D7 — identidad ruteable como columna, no jsonb**: el `token` (src_) del source
  hoy vive en `config` jsonb (§4), pero `/v1/ingest/{token}` necesita resolver
  `token → workflow` con un índice único. Recomendado **promover el token a una
  columna dedicada** (única, scope global para rutear sin contexto de tenant) en
  vez de un índice de expresión sobre jsonb. Aplica análogamente a alias/number/folder.
- **D8 — `subscribed_events` default por tipo de workflow**: el default actual de
  `webhook_destinations` (`["document.extracted","document.failed"]`) es inválido
  para un workflow ANALYSIS (necesita `analysis_run.completed`). El default debe
  derivarse del tipo de workflow al crear el destination.
