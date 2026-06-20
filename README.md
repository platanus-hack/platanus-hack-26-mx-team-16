# Doxiq

Plataforma inteligente de extraccion de datos y analisis de reglas de negocio a partir de documentos. Soporta multiples industrias y procesos configurables dinamicamente.

## Stack Tecnologico

| Capa | Tecnologia |
|------|-----------|
| Frontend | Next.js 15 + React 19 + TypeScript + Tailwind CSS v4 + shadcn |
| Backend | FastAPI + Python 3.12 + SQLAlchemy (async) + PostgreSQL |
| OCR | Gemini 2.5 Flash / AWS Textract / GCP Vision |
| LLM | Gemini 2.5 Flash / OpenAI gpt-4o-mini |
| Analisis | Gemini 2.5 Flash via Agno Agent (output estructurado) |
| Storage | S3 (AWS) |
| Knowledge Base | pgvector + Gemini Embedding API (similitud coseno) |
| Workers | Temporal Framework |
| Auth | JWT + Google OAuth |

## Arquitectura

```
doxiq/
  backend/          # FastAPI + Clean Architecture (DDD)
  frontend/         # Next.js App (shadcn + Base UI)
  docs/             # Documentacion del proyecto
```

### Backend — Clean Architecture

Cada modulo sigue la estructura:

```
src/<module>/
  domain/           # Entidades, repositorios (ABC), excepciones
  application/      # Use cases, commands
  infrastructure/   # Repositorios SQL, servicios externos
  presentation/     # Endpoints, routers, presenters, schemas
```

**Modulos:** auth, users, profile, tenants, workflows, industries, file_storage, extraction, knowledge_base, integrations, common

## Funcionalidades

### Extraccion de Documentos
- OCR multi-proveedor (Gemini, AWS Textract, GCP Vision) con scoring de confianza
- Extraccion de tablas Markdown para campos de tipo array
- Estructuracion LLM de texto OCR a JSON basado en schemas dinamicos
- Procesamiento asincrono con polling de estado
- Knowledge Base (RAG) para inyectar contexto de documentos de referencia
- Cancelacion de jobs en progreso

### Analisis de Reglas de Negocio
- Evaluacion de reglas configurables contra datos extraidos
- Variables de template (`{{today}}`, `{{current_year}}`)
- Referencias a campos (`@DOC_TYPE.field`)
- Contexto KB por regla para validaciones contextuales
- Streaming SSE para resultados en tiempo real

### Multi-tenancy
- Tenants con roles y permisos configurables
- Workflows por tenant
- Bootstrap de roles por defecto

## Desarrollo

### Requisitos
- Python 3.12+
- Node.js 18+
- Docker + Docker Compose

### Backend

```bash
# Con Docker (recomendado)
just dev-backend

# O directamente
cd backend && docker compose up
```

Backend disponible en `http://localhost:8200`

### Frontend

```bash
just dev-frontend

# O directamente
cd frontend && npm install && npm run dev
```

Frontend disponible en `http://localhost:3000`

### Comandos utiles (justfile)

```bash
just                    # Listar todos los comandos
just dev-all            # Iniciar backend + frontend
just dev-backend        # Solo backend (Docker)
just dev-frontend       # Solo frontend
just migrate-backend    # Correr migraciones
just stop-all           # Parar todos los contenedores
```

### Variables de Entorno (backend/.env)

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `CORS_ORIGINS` | Origenes permitidos CORS |
| `GEMINI_API_KEY` | API key para Gemini (OCR + LLM) |
| `OPENAI_API_KEY` | API key para OpenAI |
| `AWS_ACCESS_KEY_ID` | AWS credentials (S3 + Textract) |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_S3_BUCKET_NAME` | Bucket S3 para archivos |
| `JWT_SECRET_KEY` | Secret para tokens JWT |

## Documentacion

| Documento | Contenido |
|-----------|----------|
| [CHEATSHEET.md](CHEATSHEET.md) | Referencia ultra compacta para pedir uso de MCPs y skills en prompts |
| [docs/backend/endpoints.md](docs/backend/endpoints.md) | Referencia completa de los 69 endpoints REST |
| [docs/backend-migration.md](docs/backend-migration.md) | Plan de migracion desde legacy |
| [docs/legacy_backend/](docs/legacy_backend/) | Documentacion historica del backend anterior |
