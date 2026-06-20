# Codex Project Rules - Doxiq

## Project Overview
Doxiq (by Llamitai) is a document extraction and business rule analysis platform. It uses OCR + LLM to extract structured data from documents and evaluate configurable business rules against the extracted data.

## Repository Structure
```
doxiq/
  backend/        # FastAPI API (Python 3.12, async SQLAlchemy, PostgreSQL)
  frontend/       # Next.js App (TypeScript, Tailwind CSS v4, shadcn + Base UI)
  docs/           # Project documentation
  justfile        # Development commands
```

## Backend Architecture
Clean Architecture with DDD. Each module follows: `domain/ → application/ → infrastructure/ → presentation/`

**Modules:** auth, users, profile, tenants, workflows, industries, file_storage, extraction, knowledge_base, integrations, common, messaging

### Key Patterns
- **Use cases** are dataclasses implementing `UseCase` with an `execute()` method
- **Repositories** are abstract classes in `domain/`, implemented as SQL repos in `infrastructure/`
- **Presenters** convert domain entities to API response dicts
- **Routers** use `add_api_route()` to register endpoints
- **Exceptions** extend `DomainError` with code, message, and status_code
- **Database** uses async SQLAlchemy with Alembic migrations
- **Background tasks** use FastAPI BackgroundTasks (extraction pipeline)
- **Temporal** used for document processing workflows (`src/workflows/`)

## Frontend Architecture
- Next.js 15 + React 19 + TypeScript
- Tailwind CSS v4 (oklch colors, `@theme inline`)
- shadcn + Base UI components
- Clean Architecture: `domain/ → application/ → infrastructure/ → presentation/`
- `src/app/` — Next.js App Router pages
- `src/presentation/` — UI components and views
- `src/application/` — stores (zustand), hooks, lib
- `src/domain/` — entities, repositories, responses
- `src/infrastructure/` — mock repositories (API integration pending)

### MANDATORY: Client → Backend must go through a Next.js BFF route
Any code that runs in the browser (`"use client"` components, hooks, event handlers) **must never** `fetch` the backend directly via `Settings.apiBaseUrl` / `process.env.NEXT_PUBLIC_BACKEND_API_HOST`.

The pattern is:
1. **Client component** → `fetch("/api/<feature>/...", ...)` (same-origin, relative path)
2. **BFF route** at `src/app/api/<feature>/.../route.ts` (server-side handler) reads server-only env vars and forwards via `serverHttp`
3. The BFF is also where you set/read HttpOnly cookies, inject `X-Api-Key`, and translate error payloads

## Design System
Governed by two root files maintained via the `/impeccable` skill:
- **`PRODUCT.md`** (strategic): register, users, purpose, brand personality, anti-references, design principles
- **`DESIGN.md`** (visual): tokens, typography, components, Do's/Don'ts

Quick reference:
- **Register:** `product` (authenticated app UI; no marketing surface)
- **Personality:** sharp, trustworthy, approachable. North Star: *"The Inspection Bench."*
- **Visual system:** teal primary `oklch(0.59 0.095 180.54)` on cool-gray neutrals, Figtree + Geist Mono, 0.75rem base radius, near-flat (hairline rings + whisper shadows)
- **Anti-references:** generic SaaS templates, the trendy AI-app look, legacy enterprise clutter

## Development Commands
```bash
# Development
just dev-backend              # Start backend with Docker
just dev-frontend             # Start frontend dev server
just migrate-backend          # Run DB migrations
just migrate-backend-new "name"  # Create new migration

# Docker
just stop-all                 # Stop all containers
just build-prod               # Build production images
```

## Style Guidelines
- Backend: Python, snake_case, type hints, async/await
- Frontend: TypeScript, camelCase, functional components
- API responses use camelCase (presenters convert from snake_case)
- Commit messages in English (Conventional Commits)

## Skills Available
Loaded from `.codex/skills/`:
- brainstorming, clean-fastapi-ddd, design-system-patterns, docker-hardening
- fastapi, fastmcp-server, find-skills, frontend-design, impeccable
- pytest-coverage, python-testing, sse-endpoints, vercel-react-best-practices