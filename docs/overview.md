# Doxiq — Visión General

Doxiq (de Llamitai) es una plataforma de **extracción documental + análisis de reglas de negocio**. Lee imágenes / PDFs, extrae información estructurada con OCR + LLM, y opcionalmente evalúa reglas configurables sobre los datos extraídos.

## ¿Para qué sirve?

1. **Procesar documentos**: OCR multi-proveedor (Gemini, AWS Textract, GCP Vision) → texto → estructuración LLM a JSON según un schema dinámico (`DocumentType` + campos definidos).
2. **Validar y analizar**: ejecutar reglas de negocio contra los datos extraídos, con soporte de variables de plantilla (`{{today}}`, `{{current_year}}`), referencias a campos (`@DOC_TYPE.field`) y contexto desde Knowledge Base (RAG con pgvector).
3. **Multi-tenant**: cada tenant configura sus workflows, document types y reglas de forma aislada.

## Stack

- **Backend**: FastAPI (Python 3.12), SQLAlchemy async, PostgreSQL + pgvector, Alembic, Temporal (orquestación de procesamiento), arquitectura limpia (`domain/ → application/ → infrastructure/ → presentation/`).
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind v4, shadcn + Base UI, zustand.
- **Infraestructura**: Docker Compose, Redis, S3 / storage local.

## Tipos de Workflow

Definidos en `src/workflows` — el campo `workflow_type` controla la bifurcación:

| Tipo       | Caso        | DocumentSet asociado a | Soporta Analysis Run |
|------------|-------------|------------------------|----------------------|
| `STANDARD` | No usa cases| `workflow_id` directo  | No                   |
| `ANALYSIS` | Requiere case| `workflow_case_id`    | Sí                   |

La validación está en `application/document_sets/dispatcher.py` y `application/analysis_runs/starter.py` (lanza `WorkflowTypeMismatchError` si se mezcla).

## Flujo de uso (confirmado)

### Configuración común (ambos tipos)

1. **Crear workflow** (`POST /workflows`) eligiendo `workflow_type`.
2. **Configurar document types soportados**: cada uno con campos tipados, validaciones y opcionalmente sugerencia automática vía LLM (`suggest_document_type_fields`).
3. **(Solo ANALYSIS) Configurar analysis rules**: reglas se parsean a "checks" ejecutables con un parser LLM (`parser_runner`, `parsed_checks_clearer`, `reparse_rule`). Se pueden reordenar y observar vía SSE.

### A. Workflow ANALYSIS

1. Entrar al detalle → tab **Cases**.
2. Crear un **Case** (`workflow_case`).
3. Subir documento al case → se crea un **DocumentSet** atado al `workflow_case_id` y se dispara la pipeline Temporal `DocumentSetProcessingWorkflow` (OCR → clasificación → extracción → validación → persistencia).
4. Ejecutar **Analysis Run** (`POST /analysis-runs`) sobre el case → genera un `analysis_run` con `analysis_rule_results` por cada regla. Resultados en streaming SSE (`stream_analysis_run_events`).

### B. Workflow STANDARD

1. Entrar al detalle → tab **Documents**.
2. Cargar archivo → se crea un **DocumentSet** atado directamente al workflow (sin case) y se dispara la misma pipeline de procesamiento.

## Pipeline de procesamiento (Temporal)

`src/workflows/presentation/workflows/document_set_processing.py` orquesta:

1. `text_reader` — OCR del archivo (provider configurable).
2. `persist_classified_documents` — clasificar y enlazar a `DocumentType`.
3. `extraction_normalizer` / `extraction_validator` — estructuración LLM y validación contra el schema.
4. `update_document_set_status` / `mark_document_status` — actualización de estado.
5. Re-extracción soportada vía `document_set_re_extraction.py` y `re_extract_case_document_sets`.

Eventos del set se exponen por SSE (`stream_document_set_events`) para refresco en tiempo real del frontend.

## Módulos backend

`auth`, `users`, `profile`, `tenants`, `workflows` (núcleo), `industries`, `file_storage`, `extraction`, `knowledge_base` (RAG con pgvector), `integrations`, `messaging`, `common`.

## Rutas principales del frontend

`src/app/(protected)/workflows/[wf_slug]/`:

- `/workflow` — config general
- `/document-types` y `/document-types/[id]` — tipos y campos
- `/analysis-rules` — reglas (solo ANALYSIS)
- `/cases` y `/cases/[caseId]` — cases (solo ANALYSIS)
- `/documents` y `/documents/[id]` — carga directa (STANDARD)
- `/integrations`, `/permissions`

## Comandos útiles

```bash
just dev-all              # backend + frontend
just dev-backend          # API + Postgres + Redis + Temporal (Docker)
just dev-backend-worker   # worker Temporal local
just dev-frontend         # Next dev server
just migrate-backend      # alembic upgrade
just migrate-backend-new "name"
just test-backend [path]
just start-workflow ...   # disparar DocumentProcessingWorkflow manualmente
```

Puertos: backend `:8200`, frontend `:8080`.

## Documentación complementaria

- `docs/backend/processing-workflow.md` — detalle de la pipeline
- `docs/backend/endpoints.md`, `docs/backend/postman_collection.json` — API
- `docs/cases/processing-document.md` — flujo de cases
- `docs/erd-diagram.md` — modelo de datos
- `docs/frontend/flows.md` — flujos UI
