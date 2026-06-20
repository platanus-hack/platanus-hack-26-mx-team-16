---
feature: re-architecture
type: plan
status: implemented
coverage: 90
audited: 2026-06-16
---

# Decisiones de arquitectura — Doxiq · pipelines configurables

Registro de decisiones tomadas en la revisión cruzada + walkthrough (una a una).
Acompaña a `architecture/pipelines.html` (propuesta), `architecture/detalle-tecnico.html` (detalle),
`cases/fondos-credito-garantia.html` (garantías) y `cases/circulares.html` (circulares).

Leyenda de estado: ✅ cerrada · ⚠️ default provisional (requiere confirmación del cliente).

---

## A · Decisiones arquitectónicas (las decide ingeniería)

| # | Decisión | Resolución | Estado |
|---|---|---|---|
| A1 | ¿Dónde vive la definición del pipeline? | En **DB** (fuente de verdad en runtime) como `Pipeline`/`PipelineVersion`; **cargada y versionada por fixtures JSON** (mecanismo existente `command.py` load/dump + `backend/fixtures/`). El run **sella `pipeline_id` + `version`** al arrancar; versiones **inmutables append-only** (una edición = versión nueva). | ✅ |
| A2 | ¿Cómo invoca una regla una Tool externa? | **Ambos**: fase `enrich` para el pre-fetch general (default, cubre los 3 casos) **y** un token `@tool.x(args)` para lookups dirigidos desde una regla. Los dos pasan por el **mismo conector determinista con caché** (la Tool nunca se llama como HTTP crudo desde el LLM). Arrancar con `enrich`; el token se suma cuando un caso lo pida. | ✅ |
| A3 | ¿Dónde viven las credenciales de una Tool de lookup? | Reusar **`ConnectionAccount` + capability `LOOKUP`** (nueva). El secreto vive una vez por tenant (rotación/allowlist/auditoría centralizadas, coherente con `SEND`/webhooks); la `ToolDefinition` guarda lo no-secreto (input/output schema, transport) y referencia `connection_account_id`. | ✅ |
| A4 | ¿El `input_hash` de síntesis varía por contenido del documento? | **Sí, por pipeline.** Regla de oro: **todo lo que entra al prompt de síntesis entra al hash**. Farmacia queda lean (salida = verdicts); circulares mete los documentos a la síntesis y al hash. Se **versiona la clave de caché** para invalidar lo viejo. (Corrige la exclusión actual de `mapped_extraction`.) | ✅ |
| A5 | ¿Versionado de esquema + eval harness? | **Plataforma de eval completa** (datasets gestionados, métricas, comparación de versiones, UI de revisión) como **workstream propio** (no bloquea M0–M6). El versionado de esquema ya viene gratis con pipelines/doctypes inmutables. | ✅ |
| A6 | ¿Cómo se calcula la confianza por campo? | **Por capas**: (1) legibilidad bbox (ya existe), (2) confianza semántica vía auto-eval del LLM y/o consenso (`analysis_consensus_samples` ya existe), (3) **cross-check contra referencia** (formulario / API de jueces / reglas de formato) — la señal más fuerte. El `confidence_gate` combina; la plataforma de eval (A5) calibra umbrales. | ✅ |
| A7 | ¿Captura de correcciones (active learning)? | **Diferida a la plataforma de eval (A5)**: las correcciones humanas `(field, ocr_guess, human_value, confidence)` por tenant son datasets de eval — se capturan en ese workstream, sin entidad nueva en M0–M6. | ✅ |

**Ya resueltas en la revisión cruzada (sin walkthrough):**
- **DAG vs lineal** → *parcial*: secuencia lineal + predicado condicional `when:` por fase alcanza para los 3 casos (circulares lo prueba); DAG con paralelismo diferido.
- **Webhooks desde cualquier pipeline** → *sí*: desacoplar el dispatcher para que ANALYSIS/cobertura también emita. (Los nombres por-pipeline `coverage.completed`/`resolution.completed`/`circular.completed` quedaron **superados por W1**: colapsan en `analysis_run.completed`, con el `output_schema` de cada caso como payload.)
- **`HumanTask.audience`** → agregado a la entidad unificada (lo exige la doble revisión de circulares).

---

## B · Decisiones de negocio / contrato (revisadas; algunas a confirmar con el cliente)

| # | Decisión | Resolución | Estado |
|---|---|---|---|
| B1 | Caché del formulario de póliza | **Sin caché** — fetch en vivo cada caso. Se **persiste la respuesta por-caso** como snapshot de auditoría/reproducibilidad (no como caché reusable). Requiere un **path degraded** claro si el web service del cliente cae. *(Revierte la recomendación de caché agresiva de §6.3 del doc.)* | ✅ |
| B2 | Identidad del fármaco | **Normalizar a canónico** usando una **KB de fármacos provista por el cliente** (vía el mecanismo `#kb` / Tool). De paso ejercita el fix de inyección de KB (`knowledge_context`). | ⚠️ |
| B3 | Contrato A/B/C de farmacia | **Avanzar** con los shapes asumidos del doc; **validar con el cliente** antes de congelar. No bloquea M0–M4. | ⚠️ |
| B4 | UIs de revisión (circulares) | **Doxiq hospeda ambas** (analista Doxiq + analista banco); `audience`/RBAC separa qué ve cada uno (el banco entra con login/rol a Doxiq). `assignee_mode=internal_queue` en las dos. | ✅ |
| B5 | Split de oficios (TIFF) | **LLM por contenido + un Lambda dedicado de detección de sellos** iniciales de cada oficio, para mejorar el corte. (Extensión específica de circulares al `classify_pages`.) | ✅ |
| B6 | Escala de listas | **Validación por lotes** (fan-out acotado) + **límite blando configurable** de personas/oficio (advierte/particiona, no rechaza). | ✅ |
| B7 | BD de jueces | **Doxiq construye y mantiene un API de jueces**; la Tool `lookup_judge` consulta ese **API interno** (nuestra la responsabilidad de mantenerlo al día). | ✅ |
| B8 | Tipos de oficio | **Un doctype `oficio` + campo `tipo`** (congelar / descongelar / info); las reglas y el output ramifican por `tipo`. | ✅ |
| B9 | Ingesta de circulares | El **banco sube cada TIFF por API M2M**; lote diario automático (SFTP/scheduler) como **fase 2** si el volumen lo pide. | ✅ |
| B10 | Garantías — completitud | **NO hay barrera dura.** Se procesa al llegar **≥1 documento**; no es obligatorio tener todos los tipos; pueden llegar **varios del mismo tipo**. Las reglas cross-document usan **`on_empty=SKIPPED`** (ya en el enum) → solo disparan cuando sus inputs están presentes; el verdict se **re-evalúa** al llegar más documentos. ⇒ garantías **no usa `await_documents`** como gate (queda como capacidad para casos que sí necesiten barrera). | ✅ |

**Checklist de validación con el cliente (cierra B2 y B3):**
- **B2 · Identidad de fármaco** — ¿qué codificación maneja su sistema (código local propio, ATC, NDC, RxNorm)? ¿Puede entregar su catálogo/formulario como KB (CSV o API) y con qué cadencia de actualización?
- **B3 · Contrato A/B/C** — confirmar shapes reales: payload de A (`document.extracted`), request/response de B (`POST /case`), formato de `policyId`/`pharmacy_id`, y el lazo de clarificación (re-entrada por B tras la pregunta por WhatsApp).

---

## C · Conexiones: entrada y salida configurable (plan `archive/webhooks.md` integrado)

> El plan paralelo `plans/archive/webhooks.md` queda integrado a la arquitectura. Detalle visual en `architecture/conexiones.html`. La entrada (Sources) alimenta `ingest`; la salida (Destinations) consume `finalize`.

| # | Decisión | Resolución | Estado |
|---|---|---|---|
| W1 | Eventos/payload bajo pipelines | **Catálogo chico** (`document.extracted`/`document.failed` + `analysis_run.completed`); el payload de resultado = el `output_schema` del pipeline, no un evento por caso. Los nombres `coverage`/`circular`/`resolution.completed` colapsan en `analysis_run.completed`. | ✅ |
| W2 | Entrada de archivos | **Toda ingesta de archivos = Source** (`workflow_sources`); el upload HTTP es el source webhook. La entrada de **datos estructurados** (farmacia B `POST /case`, callbacks de HumanTask) queda como API aparte. | ✅ |
| W3 | Batch diario (circulares) | El banco sube cada TIFF por el source HTTP ahora; el **lote diario** automático se agrega como un **source más** (Drive/SFTP) en fase 2 — el modelo ya lo admite. | ✅ |
| D1 | Estructura de tablas | **2 tablas**: `workflow_sources` / `workflow_destinations`, cada una con `provider` + `config` jsonb + `account_id` nullable. | ✅ |
| D2 | Webhook ¿org o inline? | **inline** (`account_id=NULL`); `ConnectionAccount` solo para OAuth. Supersede `product/specs/connections/spec.md §4.4`. | ✅ |
| D3 | Auth del source | **API key y HMAC**, `auth_mode` por source. | ✅ |
| D4 | Migración `webhook_destinations` | **in-place** (ALTER +provider +account_id, rename → `workflow_destinations`). | ✅ |
| D5 | Módulo de los bindings | **`connections`** (junto a `connection_accounts`). | ✅ |
| D6 | Default de `auth_mode` | **api_key**. | ✅ |
| D7 | Identidad ruteable | **columna dedicada única** (`route_token`), no en `config` jsonb. | ✅ |
| D8 | Default de `subscribed_events` | **deriva del output** del pipeline (resuelto por W1). | ✅ |

**`ConnectionAccount` queda con 3 capabilities:** `RECEIVE` (Sources OAuth) · `SEND` (Destinations OAuth) · `LOOKUP` (Tools).

---

## Impacto en los documentos (cambios a aplicar)

- **B10 → `cases/fondos-credito-garantia.html`**: reemplazar el "completeness gate / esperar los 3 tipos" por **procesamiento incremental + `on_empty=SKIPPED`** (re-evalúa al llegar más; multi-doc del mismo tipo). *Cambio de diseño material.*
- **B1 → `architecture/pipelines.html` §6.3**: suavizar la recomendación de caché agresiva → fetch en vivo + snapshot de auditoría por-caso + path degraded.
- **B2 → farmacia**: la normalización de fármaco usa KB del cliente (`#kb`).
- **B5 → `cases/circulares.html`**: nota del Lambda de detección de sellos en el split.
- **B7 → `cases/circulares.html`**: la Tool `lookup_judge` apunta a un **API de jueces propio de Doxiq** (no al web service del cliente).
- **B8 → `cases/circulares.html`**: `oficio` con campo `tipo` (ya consistente).
- **A1–A6 → `architecture/pipelines.html` §11**: marcar las decisiones como resueltas con su respuesta.
- **A7 + checklist B2/B3 → `architecture/pipelines.html` §11 y `cases/recetas-medicas.html` §08**: estados sincronizados con este registro (2026-06-09).
