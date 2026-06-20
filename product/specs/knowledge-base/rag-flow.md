---
feature: knowledge-base
type: spec
status: pending
coverage: 5
audited: 2026-06-16
backlog: true
---

# Spec: Integración de RagFlow self-hosted en la gestión de Knowledge Bases (`rag-flow`)

Estado: **exploración / propuesta — pendiente decisión de adopción y PoC** (§8, §10)

---

## 1. Objetivo

Evaluar si incorporar [**RagFlow**](https://ragflow.io/) ([infiniflow/ragflow](https://github.com/infiniflow/ragflow), Apache-2.0) **self-hosted** como motor de RAG y de comprensión documental nos ayuda a:

1. **Mejorar la extracción de texto** de documentos (sobre todo escaneados, con tablas y layout complejo) vía su pipeline de comprensión profunda **DeepDoc** (OCR + reconocimiento de layout + TSR).
2. **Mejorar la calidad de las `validation_rules` y `analysis_rules`** dándoles recuperación semántica real (híbrida + reranking + citas con grounding) sobre la Knowledge Base, en lugar del retrieve naïve que tenemos hoy — y, sobre todo, **cerrar el gap actual** por el cual el contenido de KB **nunca llega al prompt de evaluación de reglas** (§4, 🔴).

Este spec documenta qué existe hoy en el codebase (§2), qué es RagFlow (§3), las limitaciones que arrastramos (§4), un diseño de integración por capas (§5), ventajas (§6), trade-offs/riesgos (§7), un plan de adopción por fases (§8) y los archivos a tocar (§9).

Es un spec **de evaluación**: no cierra diseño de implementación. La meta es decidir **si** y **cómo** entra RagFlow.

---

## 2. Contexto del codebase actual (qué EXISTE)

### 2.1 Knowledge Base actual (pgvector + Gemini)

El módulo `src/knowledge_base/` ya implementa un RAG propio, mínimo, en Clean Architecture.

**Modelo de dominio**

| Entidad | Archivo | Campos clave |
|---|---|---|
| `KBDocument` | `src/common/domain/models/knowledge_base/kb_document.py` | `slug`, `extracted_text`, `status` (`VECTORIZING`→`READY`/`FAILED`), `chunk_count`, `workflow_id` (scope workflow) **o** `NULL` (scope tenant) |
| `KBEmbedding` | `src/common/domain/models/knowledge_base/kb_embedding.py` | `kb_document_id`, `chunk_index`, `chunk_text`, `embedding: list[float]` |
| ORM embedding | `src/common/database/models/knowledge_base/kb_embedding.py` | columna `embedding: Vector(768)` (pgvector) |

**Ingesta** (`src/knowledge_base/application/use_cases/vectorize_kb_document.py`):

1. `TextExtractor` (`src/knowledge_base/infrastructure/services/text_extractor.py`): PDF vía `pdfplumber`, Excel vía `openpyxl`→Markdown, imágenes vía `pytesseract` (opcional, falla suave), texto plano UTF-8.
2. **Chunking naïve** (`vectorize_kb_document.py:23-34`): ventana deslizante de caracteres, `CHUNK_SIZE = 1_500`, `CHUNK_OVERLAP = 200`. Sin límites semánticos (frase/párrafo), sin manejo especial de tablas/código.
3. **Embeddings** (`src/knowledge_base/infrastructure/services/embedder.py`): **Google Gemini `gemini-embedding-001`, 768 dimensiones** (`GEMINI_API_KEY`), en paralelo (ThreadPool, 10 workers).
4. Persistencia batch en `kb_embeddings` (pgvector).

**Recuperación** (`src/knowledge_base/application/use_cases/retrieve_kb_context.py` → `RetrieveKBContext`):

```python
# search_similar: src/knowledge_base/infrastructure/repositories/sql_kb_embedding_repository.py:47-67
stmt = (
    select(KBEmbeddingORM)
    .where(KBEmbeddingORM.tenant_id == tenant_id, KBEmbeddingORM.embedding.isnot(None))
    .order_by(KBEmbeddingORM.embedding.cosine_distance(query_embedding))  # solo coseno
    .limit(top_k)  # default 5, máx 20
)
```

- Métrica única: **distancia coseno** pgvector. **Sin BM25/full-text, sin reranking, sin metadata filtering** más allá de `tenant_id` + lista de `kb_document_ids`.
- Endpoints: `POST /knowledge-base/search`, `POST /knowledge-base/suggest-rules` (`src/knowledge_base/presentation/router.py`).
- Servicio de resolución de slugs: `KBDocumentResolver` (`src/knowledge_base/domain/services/kb_resolver.py`) → `resolve_slugs` (`sql_kb_document_repository.py:133-153`), prefiere KB de workflow sobre KB de tenant.

### 2.2 Reglas: `validation_rules` y `analysis_rules`

Las reglas son un sistema **plugin por `kind`** (`VALIDATION`, `DERIVATION`, …) — `src/workflows/domain/rules/kind_protocol.py`.

- **Definición**: `WorkflowRule` (`src/common/domain/models/processing/workflow_rule.py`) con `kind`, `prompt` (lenguaje natural con tokens), `config` (p. ej. `severity: BLOCKER|MAJOR|MINOR|INFO`), `scope`, `knowledge_refs: list[UUID]`.
- **Sintaxis de tokens** en el prompt (`src/workflows/infrastructure/services/rules/kinds/_shared/refs.py`):
  - `@slug.path` → datos del case (campos extraídos), p. ej. `@cedula.numero`, `@invoice.items[2].total`.
  - `#kb_slug` / `#{kb_slug}` → **referencia a Knowledge Base**.
  - `{{system_var}}` → variables de runtime (`{{today}}`, `{{case.name}}`…).
- **Compilación** (`validation/kind.py:119-171`): se extraen los `#kb_slug` (`parse_kb_refs`), se **validan/resuelven a UUIDs** vía `KBDocumentResolver.resolve()` y se guardan como `knowledge_refs` en el artifact. La regla en LN se descompone (LLM parser, `validation/llm_parser.py`) en un árbol booleano + `sub_checks` (`FORMAT_CHECK`, `RANGE_CHECK`, `DATE_CHECK`, `CHECKSUM_CHECK`, `CROSS_REF_CHECK`, `AGGREGATE_CHECK`, `LLM_CHECK`).
- **Evaluación** (`src/workflows/application/workflow_rules/evaluation/evaluator.py`): construye `EvalInputs(documents, document_refs, knowledge_context, tokens)` y llama `kind.evaluate()`. Emite `Citation` (`src/common/domain/models/processing/citation.py`) y `VerdictSignal`.

### 2.3 Pipeline de extracción (Temporal + Lambdas vnext-tools)

`DocumentSetProcessingWorkflow` → `run_extraction_pipeline()` (`src/workflows/presentation/workflows/pipeline.py`):

1. **extract_text** (OCR) — Lambda `vnext-tools-extract_text-{STAGE}` (`src/workflows/domain/constants.py`).
2. **classify_pages** — Lambda `vnext-tools-classify_pages`.
3. **persist_classified_documents** — activity.
4. **extract_fields** (LLM, schema = `DocumentType.fields` JSONB Draft-7) — Lambda `vnext-tools-extract_fields`.
5. **validate_extraction** — Lambda `vnext-tools-validate_extraction`.
6. **mark_document_status** — finaliza y persiste.

OCR propio (`src/workflows/infrastructure/services/ocr/ocr_service.py`): proveedores **GCP Vision / AWS Textract / Gemini** (`gemini-2.0-flash-001`); PDFs vía `pdf2image`. Agentes LLM vía **Agno** (`src/workflows/infrastructure/agents/builder.py`, matriz OpenAI/Gemini/Anthropic).

### 2.4 Infraestructura self-hosted actual

`backend/docker-compose.yml`: `api` (8200), `temporal-worker`, **`postgres` (`pgvector/pgvector:pg17`, 5434)**, **`redis:7`**, `temporal` (7233/8233), **`minio` (9000/9001)**, `mailpit`, `admin` (Directus). Red `shared-network` en dev/prod; secretos vía **Infisical**. Config por env en `src/common/settings.py` (`GEMINI/OPENAI/ANTHROPIC/OPENROUTER_API_KEY`, `AWS_S3_ENDPOINT_URL`, etc.).

> Nota: ya operamos **Postgres, Redis y MinIO** self-hosted — relevante para el footprint de RagFlow (§7).

---

## 3. Qué es RagFlow (self-hosted)

Motor RAG open-source (Apache-2.0) orientado a "comprensión profunda de documentos" + capacidades de agente. Lo relevante para nosotros:

### 3.1 DeepDoc — comprensión documental (clave para extracción)
- **OCR + reconocimiento de layout** (10 componentes: Text, Title, Figure, Figure caption, **Table**, Table caption, Header, Footer, Reference, Equation) + **TSR (Table Structure Recognition)**.
- Pensado para PDFs/imágenes/escaneos/multi-columna donde un OCR plano pierde estructura. Acelerable por **GPU** (`DEVICE=gpu`).

### 3.2 Chunking por plantilla
- "Chunk methods": `general`, `qa`, `table`, `paper`, `book`, `laws`, `manual`, `presentation`, `resume`, `picture`, `one`, `knowledge_graph`, `tag`. Explicable y visualizable, con intervención humana sobre los chunks.

### 3.3 Recuperación híbrida + reranking + GraphRAG
- **Vector + full-text (BM25) + tensor (late-interaction)** con **fused re-ranking**. GraphRAG opcional (`use_kg`).
- **Citas con grounding** (posiciones/highlight por chunk) → menos alucinación.

### 3.4 APIs de integración
- **HTTP API** (`/api/v1/...`) + **Python SDK** (`sdk/python`) + servidor **MCP**.
- Endpoint estrella para nosotros — **`POST /api/v1/retrieval`**:
  - Request: `question`, `dataset_ids[]`, `document_ids[]`, `top_k`, `similarity_threshold`, `vector_similarity_weight`, `rerank_id`, `keyword` (BM25 on/off), `highlight`, `metadata_condition`, `use_kg`, `cross_languages`.
  - Response `chunks[]`: `content`, `document_id`, `document_keyword`, `highlight`, `positions`, `kb_id`, `important_keywords`, `similarity` (fusionada), `term_similarity` (BM25), `vector_similarity`.
- Datasets: `chunk_method`, `embedding_model`, `parser_config` (`graphrag`, `llm_id`), `language`. Subida: `POST /api/v1/datasets/{id}/documents` (`local`/`web`/`empty`) + parse. Chunks manuales con `important_keywords`, `questions`, `tag_kwd`, `image_base64`.
- **Embeddings y LLM configurables** (incluye modelos locales vía Ollama) → podemos mantener Gemini o mover a local.

### 3.5 Requisitos de self-hosting
- Docker Compose. Mínimos: **CPU ≥ 4, RAM ≥ 16 GB, Disco ≥ 50 GB**, Docker ≥ 24, Compose ≥ v2.26.1.
- Dependencias propias: **MySQL + MinIO + Redis + Elasticsearch** (motor por defecto) **o Infinity** (`DOC_ENGINE`). Imagen *slim* (~2 GB, sin modelos de embedding embebidos) desde v0.22.0.

---

## 4. Lo que FALTA / limitaciones actuales (el caso a favor)

1. **🔴 El contenido de KB nunca llega a la evaluación de reglas.** En compilación `#kb_slug` se resuelve a UUIDs (`knowledge_refs`), pero en evaluación `knowledge_context` se pasa **vacío** (`[]`) — `src/workflows/presentation/workflows/activities/analysis_run_activities.py` + `evaluation/evaluator.py:48,74`. Es decir: hoy una regla **no puede** validar/analizar contra el texto real de la KB. **Este es el gap principal** y el mayor argumento para mejorar la capa de retrieval.
2. **🟡 Retrieval pobre aunque se cablee.** Si conectáramos el `knowledge_context`, hoy sería: coseno puro, sin BM25/híbrido, sin reranking, chunking de 1500 chars sin semántica, y a nivel **documento completo** (`resolve_slugs` trae el `KBDocument`, no los chunks relevantes a la aserción). Baja precisión para reglas regulatorias/normativas.
3. **🟡 Extracción sin layout.** El OCR produce texto plano con marcadores `--- Page N ---`; **sin estructura de tablas → campos**, sin preprocesado de escaneos, sin bounding boxes. `extract_fields` recibe texto plano, lo que degrada exactitud en facturas/formularios/tablas (la extracción de tablas Gemini existe pero **no está integrada** al pipeline).
4. **🟡 Sin grounding fino.** Nuestras `Citation` apuntan a campos del documento del case, pero no a *spans* de la KB que justifican un veredicto.

---

## 5. Diseño propuesto: integración por capas

Principio: **RagFlow entra detrás de nuestras interfaces de dominio existentes**, sin reescribir el sistema de reglas. Se introduce un proveedor de RAG conmutable por config (`RAG_PROVIDER = pgvector | ragflow`), igual que ya hacemos con proveedores LLM por env.

```
                         ┌──────────────────────────────────────────┐
   #kb_slug (compile)    │  Doxiq backend (FastAPI / Temporal)       │
        │                │                                          │
        ▼                │   KBDocumentResolver   WorkflowRuleEval   │
  knowledge_refs ───────▶│        │                     │           │
                         │        ▼                     ▼           │
                         │   RagKBProvider (interface)              │
                         │      ├─ PgvectorProvider (actual)        │
                         │      └─ RagflowProvider (NUEVO) ─────────┼──▶ RagFlow self-hosted
                         └──────────────────────────────────────────┘     POST /api/v1/retrieval
                                                                           POST /api/v1/datasets/...
```

### 5.1 Opción A — RAG para reglas (recomendada como primer paso, bajo riesgo)

**Mapeo de datos:** cada `KBDocument` se replica en un **dataset RagFlow** (estrategia de tenancy: 1 dataset por workflow, o por tenant con `metadata_condition` para aislar). Guardamos `ragflow_dataset_id` / `ragflow_document_id` junto al `KBDocument`.

**Ingesta (dual-write):** en `KBDocumentVectorizer`, además (o en lugar) del pipeline pgvector, subir el archivo a RagFlow (`POST /datasets/{id}/documents` + parse) eligiendo `chunk_method` según el tipo (p. ej. `laws`/`manual`/`table`).

**Recuperación (cierra el 🔴 gap §4.1):** en la actividad de evaluación, poblar `knowledge_context` llamando a `POST /api/v1/retrieval` con:
- `question` = la aserción/campo a verificar (o el `prompt` del sub_check),
- `dataset_ids` = derivados de `knowledge_refs` de la regla,
- `top_k`, `similarity_threshold`, `rerank_id`, `vector_similarity_weight`, `use_kg`.

Mapear `chunks[].content` + `positions` → `knowledge_context` y `chunks` → nuestras `Citation` (grounding real de la KB). Esto sube precisión de `LLM_CHECK`, `CROSS_REF_CHECK` y de las `analysis_rules` que razonan contra normativa.

**Esfuerzo:** medio. Toca KB ingest + un nuevo cliente + cablear `knowledge_context`. **No** toca el pipeline de Temporal de extracción.

### 5.2 Opción B — DeepDoc para extracción (mayor impacto, mayor cambio)

Usar **DeepDoc** como parser de documentos complejos (tablas/escaneos), alimentando texto + tablas estructuradas a `extract_fields`. Dos vías:
- (B1) Insertar un paso/rama en el pipeline (`vnext-tools`/`pipeline.py`) que, para mimes/casos "difíciles", llame a RagFlow para obtener el parse estructurado antes de `extract_fields`.
- (B2) Self-hostear sólo **DeepDoc** como microservicio de parsing (sin el resto de RagFlow), si únicamente queremos el OCR/TSR.

**Esfuerzo:** alto (cambia el contrato del pipeline y la generación de prompts de extracción).

### 5.3 Opción C — Plataforma completa
RagFlow como capa única de comprensión documental **y** RAG (A + B). Máximo valor, máximo footprint y acoplamiento.

### 5.4 Recomendación
Empezar por **Opción A** detrás de feature flag: resuelve el gap 🔴 que ya nos duele y es reversible. Evaluar **B** con métricas reales de exactitud de extracción antes de comprometer el pipeline.

---

## 6. Ventajas de usar RagFlow

| # | Ventaja | Impacto en Doxiq |
|---|---|---|
| 1 | Retrieval **híbrido + reranking** | Reglas que de verdad "ven" la KB con alta precisión (vs coseno top-k) |
| 2 | **DeepDoc** (layout + TSR) | Mejor texto/tablas → más exactitud en `extract_fields`, sobre todo escaneos/facturas |
| 3 | **Citas con grounding** | Pobla `Citation` con spans de KB → menos alucinación en `LLM_CHECK`/análisis |
| 4 | **Chunking por plantilla** + GraphRAG | Mejor calidad de chunk para normativa/leyes; cross-referencias |
| 5 | Embeddings/LLM **configurables** (incl. locales) | Podemos seguir con Gemini o ir a Ollama; menos lock-in |
| 6 | **Self-hosted, Apache-2.0** | Datos en nuestra infra; encaja con postura Infisical/self-host actual |
| 7 | Menos código propio que mantener | Delegamos chunking/embeddings/rerank/parse a un motor maduro |

---

## 7. Trade-offs y riesgos

- **🔴 Footprint pesado.** RagFlow quiere **su propio MySQL + Elasticsearch (o Infinity) + MinIO + Redis** y **≥16 GB RAM**. Aunque ya corremos Postgres/Redis/MinIO, RagFlow no los reutiliza de forma trivial (sobre todo ES/MySQL). Es un stack adicional considerable.
- **🟡 Doble fuente de verdad.** El contenido de KB viviría en pgvector **y** en RagFlow → consistencia, backfill y borrado en cascada coordinado.
- **🟡 Latencia/disponibilidad.** El retrieval pasa a ser una llamada de red dentro de una activity de Temporal → timeouts/reintentos/circuit-breaker.
- **🟡 Multi-tenancy.** Aislar tenants/workflows ⇒ mapear a datasets + API keys + `metadata_condition`. Riesgo de fuga entre tenants si se modela mal.
- **🟡 Operación.** Upgrades de RagFlow, modelos de embedding (la imagen slim no los trae), GPU opcional para DeepDoc, observabilidad.
- **🟢 Licencia.** Apache-2.0 self-host: sin coste de su pricing cloud.
- **Alternativa más barata:** si sólo queremos cerrar el gap 🔴 y reranking, podríamos primero **mejorar pgvector** (BM25 con `tsvector` + un reranker) sin sumar todo el stack RagFlow. RagFlow gana claramente cuando además queremos **DeepDoc** (extracción) y GraphRAG.

---

## 8. Plan de adopción por fases

| Fase | Objetivo | Entregable |
|---|---|---|
| **0 — PoC** | Levantar RagFlow vía su docker-compose junto al stack; ingerir 5–10 docs de KB reales; comparar calidad de retrieval vs pgvector | Reporte de precisión/recall + decisión go/no-go |
| **1 — RAG para reglas** | Implementar `RagflowProvider` y **cablear `knowledge_context`** en evaluación (cierra §4.1) detrás de flag | `RAG_PROVIDER=ragflow` en staging; reglas con citas de KB |
| **2 — Dual-write ingest** | Replicar ingesta de KB a RagFlow + backfill de KB existente | Job de migración + borrado en cascada coordinado |
| **3 — DeepDoc (extracción)** | Evaluar B1/B2 en docs difíciles con métricas de exactitud | Comparativa extract_fields con/ sin DeepDoc |
| **4 — Consolidación** | Decidir si deprecar la ruta pgvector o mantener híbrido | ADR final |

---

## 9. Detalles de implementación (archivos a tocar)

- **Config** — `src/common/settings.py`: `RAG_PROVIDER` (`pgvector`|`ragflow`), `RAGFLOW_BASE_URL`, `RAGFLOW_API_KEY`, `RAGFLOW_DEFAULT_CHUNK_METHOD`, `RAGFLOW_RERANK_ID`. Secretos vía Infisical.
- **Cliente nuevo** — `src/knowledge_base/infrastructure/services/ragflow_client.py`: wrapper de `/api/v1/datasets`, `/documents`, `/retrieval` (httpx async, reintentos, timeout).
- **Proveedor de retrieval** — nueva implementación de la interfaz que hoy cubre `RetrieveKBContext`/`search_similar`, p. ej. `RagflowRetriever` paralelo a `SQLKBEmbeddingRepository.search_similar` (`sql_kb_embedding_repository.py:47-67`).
- **Ingesta** — `src/knowledge_base/application/use_cases/vectorize_kb_document.py`: dual-write a RagFlow; persistir `ragflow_dataset_id`/`ragflow_document_id` (migración Alembic sobre `kb_documents`).
- **Cerrar el gap de evaluación** — `src/workflows/presentation/workflows/activities/analysis_run_activities.py` + `src/workflows/application/workflow_rules/evaluation/evaluator.py`: poblar `knowledge_context` desde RagFlow usando `knowledge_refs` y mapear `chunks[]`→`Citation` (`src/common/domain/models/processing/citation.py`).
- **(Opción B)** — `src/workflows/presentation/workflows/pipeline.py` + Lambdas `vnext-tools/`: rama de parsing DeepDoc para mimes/casos difíciles antes de `extract_fields`.
- **Infra** — añadir el stack RagFlow (compose propio) a `backend/docker-compose*.yml` / red `shared-network`; documentar en `specs/devops/`.

---

## 10. Decisiones abiertas

1. **¿Alcance?** Sólo RAG para reglas (A) vs también DeepDoc para extracción (B/C). 🔴 bloquea el dimensionamiento de infra.
2. **¿Reemplazar o coexistir con pgvector?** ¿RagFlow es la única fuente o dual-write con pgvector como fallback?
3. **¿Tenancy en RagFlow?** ¿1 dataset por workflow, por tenant, o por `(tenant, workflow)`? ¿API key por tenant?
4. **¿Motor doc?** Elasticsearch (default, +RAM) vs Infinity (más liviano; sin soporte oficial en Linux/arm64).
5. **¿Embeddings?** Mantener Gemini `gemini-embedding-001` (768) en RagFlow para consistencia, o adoptar el modelo/rerank de RagFlow (implica re-embeddear).
6. **¿GPU?** DeepDoc en CPU vs GPU según volumen.
7. **Alternativa mínima:** ¿primero BM25+reranker sobre pgvector (sin stack RagFlow) y reservar RagFlow para cuando DeepDoc/GraphRAG sean prioridad?

---

> Próximo paso sugerido: **Fase 0 (PoC)** acotado a Opción A, midiendo precisión de retrieval vs pgvector sobre KB real, antes de comprometer el footprint de infraestructura del §7.
