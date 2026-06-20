---
name: clean-fastapi-ddd
description: Build async FastAPI services using Clean Architecture + DDD + CQRS. Use when scaffolding a new FastAPI service, adding a feature module, designing endpoints/use cases/repositories/buses, wiring multi-tenant auth and DI, paginating, handling errors, or running background jobs with SAQ/Redis. Triggers on phrases like "new FastAPI service", "add module to FastAPI app", "create use case / command / query", "add repository", "set up AppContext / DomainContext / BusContext", "implement CRUD with clean architecture", "FastAPI multi-tenant", "FastAPI background jobs", or files matching `src/*/domain|application|infrastructure|presentation`.
---

# Clean FastAPI + DDD + CQRS

A **portable, opinionated template** for async Python FastAPI services. Copy it
into a new project and follow it as-is. Code is organized into 4 concentric
layers and a request-scoped DI graph. Every feature follows the same shape, so
reading any module teaches you the whole codebase.

Examples below use a single neutral domain — a `projects` feature with a
`Project` entity — so the snippets look runnable. Swap it for your own domain
when you apply the skill (see "Adapting to a new project").

## Stack & assumptions

- **Async FastAPI** + **SQLAlchemy async** + **asyncpg** over **PostgreSQL**.
- **Multi-tenant**: rows scoped by `tenant_id`; `User` / `Tenant` / `TenantUser` foundation in `src/common`.
- **JWT auth** with a **Redis token blacklist**.
- **Redis + SAQ** for background jobs and cron.
- **camelCase on the wire, snake_case inside** (auto-converted both directions).
- **Cursor pagination** for every list endpoint.
- Single service, single DB, multiple deploy modes via `SERVER_MODE`.

## Core principles

1. **Dependencies point inward**: `presentation → application → domain ← infrastructure`. Domain has zero framework imports.
2. **Async everywhere**: FastAPI + SQLAlchemy async + asyncpg + SAQ.
3. **Request-scoped DI**: each request gets its own `AsyncSession`, repositories, bus handlers — isolated and transactional.
4. **CQRS**: `CommandBus` for writes (sync or queued via SAQ), `QueryBus` for reads. A third `EventBus` (`MemoryEventBus`) is wired on `BusContext` but **dormant** by default (no subscribers) — side-effects go through `EventPublisher` or async commands (`run_async=True`). Add subscribers when you actually need fan-out.
5. **Use cases own business logic**: orchestrate buses + repos; never touch FastAPI or SQLAlchemy directly.
6. **Typed errors**: `DomainError` with `code`, `message`, `status_code` — mapped to HTTP by global handlers.
7. **camelCase outside, snake_case inside**: middleware + response class do the conversion automatically.
8. **Cursor pagination**: stable, index-friendly. The response envelope auto-detects `Page[T]`.

## When this skill applies

- Designing the directory layout for a new FastAPI service.
- Adding a new bounded-context module (`src/[bounded_context]/`).
- Implementing CRUD: entity, repository (ABC + SQL impl), use cases, commands/queries, endpoints, presenter, router.
- Wiring `DomainContext` + `BusContext` + `AppContext`.
- Setting up auth (JWT + Redis blacklist), multi-tenant filtering, and the `AuthenticatedUserDep`.
- Error handling, response envelope, validation.
- Background jobs (SAQ + Redis), cron jobs.

## Quick layout

```
config/                        # bootstrap (FastAPI app, lifespan, router, tasks)
src/
├── common/                    # shared base classes, contexts, middlewares
└── [bounded_context]/
    ├── domain/                # entities, repository ABCs, exceptions, filters
    ├── application/           # use cases, commands, queries, handlers
    ├── infrastructure/        # SQL repos, bus_wiring, builders
    └── presentation/          # endpoints, requests, presenters, router
```

## How to apply this skill

When the user asks for something that fits this architecture:

1. **Identify which layers are involved** for the task (often all 4).
2. **Read the relevant reference file** for detailed patterns:
   - `references/layers.md` — the 4 layers, allowed imports, file conventions.
   - `references/dependency-injection.md` — `AppContext` / `DomainContext` / `BusContext`, FastAPI `Depends` chain.
   - `references/cqrs-buses.md` — `Command`/`Query` definitions, `CommandBus.dispatch(run_async=True)`, bus wiring.
   - `references/repositories.md` — ABC + `SQL*` impl, `atomic_transaction`, eager loading, builders (ORM → entity).
   - `references/use-cases.md` — `Creator`/`Getter`/`Lister`/`Updater`/`Deleter` + mixins.
   - `references/endpoints.md` — requests, endpoints, presenters, router (`add_api_route`).
   - `references/auth-multi-tenant.md` — JWT, blacklist, `get_authenticated_user`, tenant scoping.
   - `references/errors.md` — `DomainError` subclassing, global handlers, error envelope.
   - `references/pagination.md` — cursor pagination, `Page[T]`, filters.
   - `references/background-jobs.md` — SAQ worker, enqueue commands, cron.
   - `references/config-bootstrap.md` — Settings, lifespan, main.py, router with `SERVER_MODE`.
   - `references/scripts.md` — operational/backfill scripts in `scripts/*` (Typer, build the context by hand, dry-run/`--apply`).
   - `references/testing.md` — test kind → layer map; per-layer patterns (unit/integration/API), self-contained.
3. **Follow the checklist** in `references/feature-checklist.md` when adding a new feature module.
4. **Reuse names exactly** — `DomainContext`, `BusContext`, `AppContext`, `build_async_domain`, `build_async_bus`, `DomainContextDep`, `BusContextDep`, `AuthenticatedUserDep`, `get_app_context`, `SQL*Repository`, `*ORM`, `build_*`, `*Creator/Getter/Lister/Updater/Deleter`, `[bounded_context]_wiring`, `Get*ByIdQuery`. (No `AppContextDep` alias — endpoints needing the whole context use `Depends(get_app_context)`. No `Persist*Command` for routine CRUD — call `repo.persist()`; reserve the command bus for cross-module or async work.) Consistency across projects is the whole point.

## Non-negotiables

- No `import sqlalchemy` from `domain/` or `application/`.
- No raising `HTTPException` from use cases or repositories — raise a `DomainError` subclass.
- No `session.commit()` outside of `atomic_transaction` (which lives in repos).
- Every list endpoint paginates with cursors and filters by `tenant_id`.
- Every endpoint that mutates is behind `AuthenticatedUserDep` unless explicitly public.
- Every new entity persisted by a repo also has: ABC interface + `SQL*` impl + `build_*` mapper + ORM model + migration.

## Adapting to a new project

- **Swap the example domain.** Replace `projects` / `Project` with your own `[bounded_context]` / `[Entity]` everywhere — the structure stays identical.
- **Single-tenant?** Drop `tenant_id` scoping, the tenant deps (`current_tenant_user`, `check_tenant_permission`), and the tenant mixins; keep the rest.
- **Replace the example services.** `DomainContext` ships with a sample service set — `token_service` (`TokenService`), `storage_service` (`StorageService`), `event_publisher` (`EventPublisher`), `notification_service` (`NotificationService`). Keep the wiring pattern; substitute the implementations your project actually needs.
- **Pick your own deploy topology.** `SERVER_MODE` (example modes `all`, `platform`) gates which routers load. Define the modes your deployment needs.
- **Infra is generic.** Bootstrap expects PostgreSQL + Redis + an S3-compatible object store + SMTP. No product names or fixed ports are assumed.
- **Quality gates** are format / lint / type-check / test — wire in whatever toolchain you use (e.g. ruff + ty + pytest, Alembic for migrations).

## What this skill is NOT

- Not a generic FastAPI tutorial.
- Not a microservice framework — it's an internal convention. One service, one DB, multiple deploy modes (`SERVER_MODE`).
- Not opinionated about the front-end. The API contract is `{ data, pagination?, timestamp }` / `{ errors, validation?, timestamp }` with camelCase keys.

Reference details live in `references/*.md`. Open the file that matches the
sub-task rather than dumping all patterns at once.
