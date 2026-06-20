# AGENTS.md

## Project Overview

Doxiq (by Llamitai) is a minimal multi-tenant SaaS starter boilerplate: authentication, users, tenants, roles/permissions and invitations, plus a generic asynchronous background-job mechanism (SAQ).

## Design Context

Frontend design work is governed by two root files maintained via the `/impeccable` skill:

- **`PRODUCT.md`** (strategic): register, users, purpose, brand personality, anti-references, design principles.
- **`DESIGN.md`** (visual): tokens, typography, components, Do's/Don'ts — Stitch DESIGN.md format, with a machine-readable mirror + drop-in component snippets in `.impeccable/design.json`.

Quick reference:
- **Register:** `product` (authenticated app UI; no marketing surface).
- **Personality:** sharp, trustworthy, approachable. North Star: *"The Inspection Bench."*
- **Visual system:** teal primary `oklch(0.59 0.095 180.54)` on cool-gray neutrals, Figtree + Geist Mono, 0.75rem base radius, near-flat (hairline rings + whisper shadows). Live tokens in `frontend/src/app/globals.css`.
- **Anti-references:** generic SaaS templates, the trendy AI-app look, legacy enterprise clutter.

Before building or restyling UI, read `PRODUCT.md` and `DESIGN.md` first.

## Documentación de decisiones y módulos

Las **decisiones de arquitectura** se registran como ADRs con el plugin
`adr-writer` (marketplace `Codex-toolkit`). La **documentación de
módulos / codebase** se genera con `codebase-documenter`.

Decisiones históricas previas a la migración viven junto a su feature en
`product/features/<feature>/plan.md`. Consúltalas antes de re-litigar
algo ya zanjado; las decisiones **nuevas** van como ADRs vía `adr-writer`.

## Repository Structure

```
doxiq/
  backend/        # FastAPI API (Python 3.12, async SQLAlchemy, PostgreSQL)
  frontend/       # Next.js App (TypeScript, Tailwind CSS v4, shadcn + Base UI)
  product/        # Specs y planes del proyecto
  justfile        # Development commands
```

## Backend Architecture

Clean Architecture with DDD. Each module follows: `domain/ → application/ → infrastructure/ → presentation/`

**Modules:** auth, users, profile, tenants, common, messaging, assets, admin

### Key Patterns
- **Use cases** are dataclasses implementing `UseCase` with an `execute()` method
- **Repositories** are abstract classes in `domain/`, implemented as SQL repos in `infrastructure/`
- **Presenters** convert domain entities to API response dicts
- **Routers** use `add_api_route()` to register endpoints
- **Exceptions** extend `DomainError` with code, message, and status_code
- **Database** uses async SQLAlchemy with Alembic migrations
- **Background tasks** use a generic SAQ (Redis-backed) async-job queue

### Common Commands

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

### Backend Entry Points
- API: `backend/config/main.py` → port 8200
- Worker: SAQ worker via `backend/config/tasks.py`
- CLI: `backend/command.py` (fixtures load/dump)

### Database
- PostgreSQL
- Migrations: `backend/src/common/database/versions/`
- Seeds: `backend/scripts/seed_test_user.py`

## Frontend

- Next.js 15 + React 19 + TypeScript
- Tailwind CSS v4 (oklch colors, `@theme inline`)
- shadcn + Base UI components
- Clean Architecture: `domain/ → application/ → infrastructure/ → presentation/`
- `src/app/` — Next.js App Router pages
- `src/presentation/` — UI components and views
- `src/application/` — stores (zustand), hooks, lib
- `src/domain/` — entities, repositories, responses
- `src/infrastructure/` — HTTP-backed repositories (`infrastructure/repositories/http-*`)

### MANDATORY: Client → Backend must go through a Next.js BFF route

Any code that runs in the browser (`"use client"` components, hooks,
event handlers) **must never** `fetch` the backend directly via
`Settings.apiBaseUrl` / `process.env.NEXT_PUBLIC_BACKEND_API_HOST`.
Reasons:
- `NEXT_PUBLIC_*` env vars are inlined at build time. If the prod
  build forgets to set them, the bundle ships with the dev fallback
  (`http://localhost:8000`) and every request from prod browsers fails.
- Cross-origin browser → backend traffic needs CORS, leaks the API
  hostname, and can't use HttpOnly cookies for auth.

The pattern is:

1. **Client component** → `fetch("/api/<feature>/...", ...)` (same-origin,
   relative path).
2. **BFF route** at `src/app/api/<feature>/.../route.ts` (server-side
   handler) reads server-only env vars and forwards via
   `serverHttp` (`src/infrastructure/http/client.ts`), which already
   resolves `BACKEND_API_HOST` correctly in any environment.
3. The BFF is also where you set/read HttpOnly cookies (access/refresh
   tokens), inject `X-Api-Key`, and translate error payloads.

The login flow (`page.tsx` → `/api/auth/login` → BFF → `serverHttp`) is
the canonical reference; mirror it for every new feature.

For pre-authenticated client traffic, use `authHttp` (axios with
`baseURL: "/api"`) from `infrastructure/http/client.ts` — it already
hits the middleware proxy (`src/proxy.ts`) that rewrites `/api/v1/*`
to the backend with `X-Api-Key` attached. Never instantiate axios
against `Settings.apiBaseUrl` from a client module.

Server components and `src/app/api/**/route.ts` files run on the
server, so they *can* use `Settings.apiBaseUrl` / `serverHttp`.

## Style Guidelines
- Backend: Python, snake_case, type hints, async/await
- Frontend: TypeScript, camelCase, functional components
- API responses use camelCase (presenters convert from snake_case)
- Commit messages in English

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |
