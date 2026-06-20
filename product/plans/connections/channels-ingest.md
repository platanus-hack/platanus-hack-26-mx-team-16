---
feature: connections
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
moved_from: .recon/
---

# E6 Recon — Canales nativos de ingesta provider-agnóstico (email entrante + WhatsApp Business)

**Alcance**: plan `product/plans/re-architecture/re-architecture.md:180` (fase `ingest` E6: sources nativos de email y WhatsApp Business), `:445` (fila E6) y `:376-399` (§6.1 Caso 4 multicanal). Base: `product/specs/source-webhooks/_archive/spec.md` y `product/specs/connections/spec.md`. Decisiones de Vic ya tomadas: canales **provider-agnósticos** (adapters por proveedor) y extractor `asr` vía Gemini (recon aparte).

---

## 1. Lo que EXISTE hoy (módulo connections + ingest E4/E5)

### 1.1 Enums y capacidades

`backend/src/common/domain/enums/connections.py`:
- `ConnectionProvider` (línea 4): `WEBHOOK`, `SLACK`, `EMAIL` ("inbound + outbound mail", línea 9), `WHATSAPP` ("inbound + outbound (phase 2)", línea 10), `DRIVE`, `HTTP`.
- `ConnectionCapability` (línea 15): `RECEIVE` / `SEND` / `LOOKUP`.
- `PROVIDER_CAPABILITIES` (línea 37): `EMAIL: {RECEIVE, SEND}` (línea 40), `WHATSAPP: {RECEIVE, SEND}` (línea 41) — los canales E6 ya están declarados como orígenes válidos.

`backend/src/common/domain/enums/sources.py`: `SourceAuthMode` = `API_KEY ("api_key")` | `HMAC ("hmac")`.

### 1.2 Modelos de dominio

- `ConnectionAccount` — `backend/src/connections/domain/models/connection_account.py:20`: `uuid, tenant_id, provider, display_name, capabilities: list[ConnectionCapability], status, config: dict` (metadata no sensible: "webhook url, slack channel, from-address, scopes…", línea 27), `secret: str | None` ("Persisted but NEVER presented", línea 29). CRUD JWT completo en `presentation/endpoints/connection_account.py` montado en `/v1/connections` (`presentation/router.py:35-48`).
- `WorkflowSource` — `backend/src/connections/domain/models/workflow_source.py:21`: `provider` (default `WEBHOOK`), **`account_id: UUID | None`** (línea 26 — "NULL for WEBHOOK (inline); set for OAuth providers" → la columna para enganchar un `ConnectionAccount` EMAIL/WHATSAPP **ya existe y está sin usar**), `route_token` (única, `src_…`), `auth_mode`, `secret` (hash de `dxk_` o `whsec_`), `config: dict`, `enabled`.
- ORM `workflow_sources` — `backend/src/common/database/models/workflow_source.py:16`; `UniqueConstraint("route_token", ...)` línea 18; migración `backend/src/common/database/versions/20260609.062319_ac2f000bb27b_add_workflow_sources.py`.

### 1.3 Auth de source

`backend/src/connections/domain/services/source_auth.py`:
- `compute_source_signature(secret: str, timestamp: int, body: str) -> str` (línea 21) — estilo Svix: `v1,<base64(HMAC_SHA256(key, "<ts>.<body>"))>`.
- `verify_source_auth(source, *, api_key=None, signature=None, timestamp=None, body=None, now=None, max_skew_seconds=300) -> bool` (línea 28).
- **Nota E6**: Meta firma con `X-Hub-Signature-256: sha256=<hex HMAC-SHA256(app_secret, raw_body)>` (hex, sin timestamp) y Mailgun con `HMAC(signing_key, timestamp+token)` (hex) — ninguno encaja en el formato Svix; hacen falta verificadores por proveedor.

### 1.4 El endpoint de ingesta `/v1/ingest/{token}` (E4/E5)

- Ruta: `ingest_router` prefix `/ingest` (`backend/src/connections/presentation/router.py:27-33`) montado bajo `/v1` (`backend/config/router.py:56`). **Público, sin JWT** — la credencial es el `auth_mode` del Source.
- Handler: `async def ingest_via_source(token, file: UploadFile, session, temporal_client, api_key = Security(_ingest_key_header), case_id = Form(alias="caseId"), case_name = Form(alias="caseName"))` — `backend/src/connections/presentation/endpoints/ingest.py:61`. Flujo: `find_by_route_token` → `verify_source_auth` → `ResolveIngestCase` (antes de subir) → `UploadFileUseCase` → document_set con `processing_job_id = f"SRC#{source.route_token}_FILE#{uploaded.uuid.hex[:12]}"` (línea 103, unique en `workflow_document_set.py:16`) → `IngestViaSource` → 202 `{job_id, document_set_id, case: {id,name}|null}` (spec §5.7).
- `IngestViaSource` — `backend/src/workflows/application/sources/ingest.py:59`: resuelve pipeline por `source.config.get("pipeline_slug", DEFAULT_PIPELINE_SLUG)` (línea 99), carga doctypes del workflow, despacha `PipelineInterpreterWorkflow` con `scope="document"` si hay caso (línea 122).
- `ResolveIngestCase` — mismo archivo línea 150: `caseId` (debe existir → 400 `ingest.CaseNotFound`) | `caseName` find-or-create vía `FindOrCreateCaseM2M` (`caseName ≡ external_ref`, único por workflow, retry de `IntegrityError`); solo workflows ANALYSIS; `case.created` solo en creación real; `EnsureCaseRunStarted` idempotente. **Esta pieza es reutilizable tal cual desde los canales** — el canal solo tiene que computar `case_name`.

### 1.5 Gestión de Sources y frontend

- `create_source` — `backend/src/connections/presentation/endpoints/workflow_source.py:50`: **hardcodea `provider=ConnectionProvider.WEBHOOK`** (línea 72); acuña `route_token` (`src_`), `dxk_` (hash) o `whsec_`, revela credencial una sola vez. `list_sources` línea 83. No hay update/delete/disable de sources.
- Repo: `SQLWorkflowSourceRepository` (`infrastructure/repositories/sql_workflow_source.py`) — `find_by_route_token` (línea 19), `find_by_id` (25), `list_by_workflow` (36), `create` (48). **No hay** `find_by_provider_and_address` ni similar.
- Frontend: `frontend/src/presentation/workflows/connections/workflow-origins-view.tsx` (260 líneas) — alta de source webhook con selector `api_key`/`hmac` (líneas 189-190); el comentario de la línea 61 ya promete tiles "Email / WhatsApp / Drive" como coming-soon (spec source_webhooks §9, `spec.md:785`). Hooks en `frontend/src/application/hooks/queries/sources.ts` (94 líneas).

### 1.6 Adapters scaffold (F12) — **modelo equivocado para E6**

- `EmailSourceAdapter.poll(source) -> list[dict]` → `NotImplementedError` (`backend/src/connections/infrastructure/adapters/email.py:12`).
- `WhatsappSourceAdapter.poll(source)` ídem (`adapters/whatsapp.py:12`).
- Registry: `ADAPTER_SOURCES[EMAIL/WHATSAPP]` (`adapters/registry.py:26-31`); base `SourceAdapter` en `domain/adapters/base.py`.
- Son **polling**; los canales E6 son **push por webhook** (el proveedor llama al backend). Los scaffolds deben mutar de `poll()` a `parse(payload) -> ChannelMessage`.

### 1.7 Infra disponible para email/WhatsApp

- **Mailpit en compose dev**: `backend/docker-compose.yml:121-128` — `axllent/mailpit`, SMTP en `1027:1025`, UI/API HTTP en `8027:8025`, `MP_SMTP_AUTH_ACCEPT_ANY=true`. Hoy solo recibe el **saliente** (`SmtpEmailService` con `aiosmtplib` — `backend/src/messaging/infrastructure/services/smtp_email.py:17`; settings `SMTP_*` en `common/settings.py:81-86`).
  - **Sí sirve como receptor de prueba inbound**: Mailpit soporta `MP_WEBHOOK_URL` (POST JSON al recibir un mensaje, con ID; los adjuntos se bajan por su API HTTP `GET /api/v1/message/{ID}`). Eso da un "proveedor" dev local → adapter `mailpit` espejo del patrón VLM dev de E3: `swaks/smtplib → mailpit:1027 → webhook al backend → adapter baja el MIME por la API`.
- **Parse MIME**: no hay lib externa ni hace falta — stdlib `email` (`BytesParser(policy=policy.default)`, `.iter_attachments()`) cubre raw MIME (SES/mailpit); `python-multipart>=0.0.9` ya está en `backend/pyproject.toml:28` para los proveedores que postean `multipart/form-data` (Mailgun/SendGrid). `httpx>=0.28.1` (línea 17) para bajar media de Meta/mailpit. `pydantic[email]` (línea 26) valida direcciones.
- **Subida**: `UploadFileUseCase` (`backend/src/storage/application/use_cases/upload_file.py:21`) exige un `UploadFile` de FastAPI y valida `settings.ALLOWED_UPLOAD_MIMES` = solo `pdf/jpeg/jpg/png` (`common/settings.py:148-153`) y `MAX_UPLOAD_SIZE` 100MB (línea 143). Los canales traen bytes ya en memoria → falta camino bytes-first y ampliar el allowlist (audio para notas de voz: `audio/ogg` (opus), `audio/mpeg`, `audio/mp4`, `audio/amr`; opcional `text/plain|text/html` si el cuerpo del correo se ingesta como archivo).
- **Texto sin adjunto**: ya existe la vía de documentos virtuales — `submit_case_data` (`backend/src/workflows/presentation/endpoints/m2m_cases.py:218`, `/v1/cases/.../data`) + `virtual_creator.py`; el plan la cita como alternativa para transcripts (`re-architecture.md:389-390`).
- Settings: `GEMINI_API_KEY` ya existe (`settings.py:99`). **No existe** ningún setting de WhatsApp/Meta ni de dominio de buzones.

### 1.8 Specs base

- `product/specs/source-webhooks/_archive/spec.md`: §5.3-5.6 modos (multipart/URL/base64/presign), §5.7 envelope 202, **§5.9 Idempotencia** (`spec.md:615`): patrón **delivery-first** — `INSERT` en `source_webhook_deliveries` con `UNIQUE(source_webhook_id, idempotency_key)` ANTES de efectos secundarios; replay devuelve `response_snapshot`. **Esa tabla NO está implementada** (no hay modelo en `src/common/database/models/`); la implementación E4 optó por `workflow_sources` sin deliveries. Es el diseño exacto a resucitar para dedup de mensajes.
- `product/specs/connections/spec.md` §5.3 (líneas 229-235): Email origen MVP = "alias dedicado (auto-generado, copiable)" + lista blanca de remitentes opcional; pregunta abierta línea 422: proveedor inbound (SendGrid Inbound Parse, Mailgun Routes, SMTP propio) — **la decisión provider-agnóstico de Vic la resuelve: todos, vía adapters**.

### 1.9 Dedup hoy

- `document_sets.processing_job_id` es unique pero incluye `file_id` (uuid4 nuevo por subida) → **cero dedup a nivel mensaje**: el mismo correo reenviado por el proveedor (retries de SES/Mailgun son la norma) crea sets duplicados.
- Patrón existente reutilizable: `case_events.dedupe_key` unique (`backend/src/common/database/models/case_event.py:41`).

---

## 2. Shapes de proveedor (para el diseño del contrato)

| Proveedor | Transporte | Identidad de ruteo | Dedup id | Adjuntos | Auth |
|---|---|---|---|---|---|
| SES (+SNS) | JSON SNS; raw MIME en S3 o base64 | `receipt.recipients[]` | `mail.messageId` + `Message-ID` RFC5322 | dentro del raw MIME → stdlib `email` | firma SNS (cert) o secreto en URL |
| Mailgun Routes | `multipart/form-data` | campo `recipient` | `Message-Id` | `attachment-count` + `attachment-N` (files) | `signature`=HMAC(signing_key, `timestamp`+`token`), hex |
| Postmark | JSON | `ToFull[].Email` / `OriginalRecipient` | `MessageID` + `Headers[Message-ID]` | `Attachments[].Content` base64 | Basic auth / token en URL |
| Mailpit (dev) | JSON (`MP_WEBHOOK_URL`) | `To[]` | `ID` / `MessageID` | via API `GET /api/v1/message/{ID}` | ninguna (red local) |
| WhatsApp Cloud API (Meta) | JSON `entry[].changes[].value` | `value.metadata.phone_number_id` | `messages[].id` (**wamid**) | `media_id` → `GET graph.facebook.com/v2x.x/{media_id}` (Bearer) → URL efímera (~5 min) → download con mismo Bearer | GET `hub.mode/hub.verify_token/hub.challenge` (echo) + POST `X-Hub-Signature-256: sha256=<hex>` sobre raw body |

WhatsApp `messages[].type`: `text` (`text.body`), `image|document|audio|video` (`{type}.id`, `mime_type`, `sha256`, `document.filename`, `audio.voice: true` para notas de voz — `audio/ogg; codecs=opus`), `context.id` (wamid citado, útil para hilo→caso).

---

## 3. Delta E6 — cambios concretos

### 3.1 Contrato provider-agnóstico (nuevo, dominio)

`backend/src/connections/domain/models/channel_message.py` (nuevo):

```python
class ChannelAttachment(BaseModel):
    filename: str
    content_type: str
    content: bytes | None = None      # inline (multipart/base64/MIME)
    fetch_ref: str | None = None      # media_id Meta / message ID mailpit — lo baja el adapter

class ChannelMessage(BaseModel):
    provider: ConnectionProvider                  # EMAIL | WHATSAPP
    provider_message_id: str                      # Message-ID | wamid  → clave de dedup
    route_hint: str                               # rcpt (email) | phone_number_id (wa)
    sender: str                                   # from | wa_id
    subject: str | None = None                    # email only
    text_body: str | None = None                  # body-plain | text.body
    attachments: list[ChannelAttachment]
    thread_ref: str | None = None                 # In-Reply-To/References | context.id
    received_at: datetime
```

`backend/src/connections/domain/adapters/channel.py` (nuevo): `class ChannelAdapter(ABC)` con `verify(source, request_ctx) -> bool` (firma del proveedor), `parse(payload, files) -> list[ChannelMessage]`, `fetch_attachment(account, ref) -> tuple[bytes, str]`. Reemplaza el modelo `poll()` de los scaffolds F12 (`adapters/email.py`, `adapters/whatsapp.py` se reescriben; `registry.py` pasa a registrar adapters por `(provider, vendor)`).

Adapters infra (nuevos): `adapters/email_ses.py`, `email_mailgun.py`, `email_postmark.py`, `email_mailpit.py` (dev — espejo del patrón "VLM dev" de E3), `whatsapp_meta.py` (vendor inicial; Twilio/360dialog enchufan después por el mismo contrato).

### 3.2 Endpoints públicos (nuevos, sin JWT, junto a `ingest_router`)

En `backend/src/connections/presentation/endpoints/channels.py` + `router.py`:
- `POST /v1/channels/email/{token}` — resuelve Source por `route_token` (reusa `find_by_route_token`), `source.config["vendor"]` elige adapter, `adapter.verify` → `adapter.parse` → pipeline común (§3.5).
- `GET /v1/channels/whatsapp/{token}` — handshake Meta: si `hub.verify_token == source.config["verify_token"]` responde `hub.challenge` plano (200, text/plain).
- `POST /v1/channels/whatsapp/{token}` — verifica `X-Hub-Signature-256` (hex HMAC del **raw body** con `app_secret` del `ConnectionAccount`; verificador nuevo junto a `source_auth.py`, NO el formato Svix), parse, **responde 200 inmediato** y procesa en background (Meta reintenta si >necesita; descarga de media va después del ACK).

### 3.3 Source/Account: provider real + ruteo buzón/número → workflow

- `create_source` (`workflow_source.py:50`): aceptar `provider: ConnectionProvider` (hoy hardcoded WEBHOOK en línea 72) + `account_id` opcional + validación de `PROVIDER_CAPABILITIES`/config por provider.
  - **EMAIL**: genera alias `in+{route_token}@{settings.CHANNELS_EMAIL_DOMAIN}` y lo guarda en `config["address"]` — el `route_token` viaja en el local-part (plus-addressing), así el ruteo dirección→Source NO necesita columna nueva: el adapter extrae el token del `rcpt` y cae en `find_by_route_token`. Para proveedores que no preservan el rcpt completo, fallback: nuevo `find_by_provider_and_address` (índice sobre columna nueva `address` o config indexado). `config["allowed_senders"]` (lista blanca, spec connections §5.3).
  - **WHATSAPP**: `account_id` → `ConnectionAccount(provider=WHATSAPP)` con `secret`=access token y `config={phone_number_id, app_secret, verify_token}`; `source.config["phone_number_id"]` espejo para validar que el `value.metadata.phone_number_id` del webhook coincide (el callback URL por-token ya rutea; el check evita cruces si un mismo app Meta sirve varios números).
- `auth_mode` no aplica a canales (la firma del proveedor es la credencial) → permitir `secret=None` para sources de canal o nuevo `SourceAuthMode.PROVIDER`.

### 3.4 Dedup + deliveries (nueva tabla, diseño ya zanjado en spec §5.9)

Tabla `channel_deliveries` (o resucitar `source_webhook_deliveries`, `product/specs/source-webhooks/_archive/spec.md:615`): `uuid, source_id FK, provider_message_id, status (RECEIVED|PROCESSED|FAILED|SKIPPED), payload_snapshot, document_set_ids, case_id, created_at` con **`UNIQUE(source_id, provider_message_id)`** — insert delivery-first ANTES de subir nada; conflicto ⇒ 200 replay (email) / 200 silencioso (Meta exige 200 siempre). `provider_message_id` = `Message-ID` normalizado (email) | `wamid` (WhatsApp). Esto también da la pestaña "Receptions" del spec §9.4 gratis.

### 3.5 Pipeline común canal → caso → documentos (reuso E4)

Por cada `ChannelMessage`: (1) delivery-first dedup; (2) `case_name` según `source.config["case_strategy"]`; (3) `ResolveIngestCase(...)` tal cual (`sources/ingest.py:150`); (4) por adjunto: bytes → S3 (ver §3.6) → `IngestViaSource`-equivalente (extraer de `IngestViaSource.execute` un camino que no re-verifique auth, p. ej. flag `pre_authenticated=True` o use case `IngestChannelFile`) con `job_id = f"SRC#{token}_MSG#{hash(provider_message_id)}_A{n}"`; (5) `text_body` sin adjuntos → documento virtual (`virtual_creator.py` / camino de `submit_case_data`, `m2m_cases.py:218`) o archivo `.txt`.

Estrategias `case_strategy` (default por canal, **decisión pendiente para Vic**): `"per_message"` (Caso 4: un caso por pedido — anónimo o `external_ref=provider_message_id`), `"sender"` (email `from` / `wa_id` como `external_ref` — agrupador tipo Caso 1), `"subject"` (subject normalizado sin `Re:/Fwd:`), `"thread"` (`thread_ref`: `References`/`context.id` → mismo caso que el mensaje citado, requiere lookup en `channel_deliveries.case_id`).

### 3.6 Subida bytes-first + MIMEs

- `UploadBytesUseCase` (o helper que envuelva bytes en `starlette.datastructures.UploadFile(BytesIO)` para reusar `UploadFileUseCase`, `upload_file.py:21`).
- Ampliar `ALLOWED_UPLOAD_MIMES` (`settings.py:148`): `audio/ogg`, `audio/mpeg`, `audio/mp4`, `audio/amr`, `audio/wav` (insumo del extractor `asr`), y decidir `text/plain`/`text/html` para cuerpos.

### 3.7 Settings nuevos (`common/settings.py`)

`CHANNELS_EMAIL_DOMAIN: str | None` (dominio de alias), `MAILPIT_API_URL: str | None` (dev, `http://mailpit:8025`), opcional `META_GRAPH_API_VERSION: str = "v20.0"`. Compose dev: añadir `MP_WEBHOOK_URL=http://api:8200/v1/channels/email/<token-dev>` al servicio mailpit (`backend/docker-compose.yml:121`) para el E2E del Caso 4.

### 3.8 Frontend

`workflow-origins-view.tsx`: tiles Email/WhatsApp dejan de ser coming-soon → form por provider (Email: muestra alias copiable + vendor + allowed_senders + case_strategy; WhatsApp: selector de `ConnectionAccount`, muestra callback URL `/v1/channels/whatsapp/{token}` + verify_token copiables); `sources.ts`: `createSource` acepta `provider` y config. Settings de org: alta de `ConnectionAccount` WHATSAPP (ya existe el CRUD backend).

### 3.9 Tests/E2E

Unit: adapters (fixtures de payloads SES/Mailgun/Postmark/Meta), verificador `X-Hub-Signature-256`, dedup race (doble POST mismo wamid). E2E Caso 4 dev: `smtplib → mailpit:1027 → MP_WEBHOOK_URL → /v1/channels/email/{token}` y POST simulado de Meta con media servida por un stub.

---

## 4. Riesgos / decisiones abiertas

1. **`case_strategy` default por canal** — no zanjado en plan/spec; preguntar a Vic (per_message vs sender vs thread).
2. Meta media URL expira ~5 min y exige ACK 200 rápido → descarga en background task post-ACK; si el download falla, delivery queda `FAILED` reintentable.
3. `IngestViaSource` re-verifica auth dentro del use case (`sources/ingest.py:89`) — los canales llegan pre-autenticados por firma del proveedor; hay que abrir un camino sin `verify_source_auth` sin debilitar el endpoint API existente.
4. Un solo app Meta multi-número/multi-tenant: el ruteo por `{token}` en la URL lo cubre (un callback por Source), pero Meta solo permite **un** callback URL por app → o un app por tenant, o un endpoint global `/v1/channels/whatsapp` que rutee por `phone_number_id` (requiere `find_by_provider_and_external_id`). Decisión de despliegue pendiente.
5. `ALLOWED_UPLOAD_MIMES` ampliado afecta también al upload UI — validar por contexto si no se quiere abrir audio en el uploader web.
