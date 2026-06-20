# Feature module checklist

Use this when adding a new bounded-context module or a new entity to one. Skipping a
step usually surfaces as a runtime error on the first request. When a path is
ambiguous, mirror an existing sibling module that already exercises the same pattern.

## Where things live (shared-core layout)

This layout is **not** strictly per-feature. Shared types live under `src/common/`; the
feature module owns only its repository ABCs, use cases, bus handlers, SQL repos, and
presentation. Get this right first — most "where does X go?" mistakes start here.

| Artifact | Location |
|---|---|
| Entity (Pydantic) | `src/common/domain/entities/[area]/[entity].py` |
| Filters (Pydantic `ListFilters` subclass) | `src/common/domain/filters/[area]/[entity].py` |
| Enums | `src/common/domain/enums/[area].py` |
| Exceptions (`DomainError` subclasses) | `src/common/domain/exceptions/[bounded_context].py` |
| ORM model (`*ORM`) | `src/common/database/models/[area]/[entity].py` |
| Builder `build_[entity]` | `src/common/infrastructure/builders/[area]/[entity].py` |
| Command/Query **message** classes | `src/common/application/commands/[area].py` · `queries/[area].py` |
| Repository **ABC** | `src/[bounded_context]/domain/repositories/[entity].py` |
| Use cases | `src/[bounded_context]/application/use_cases/[entity]/*.py` |
| Command/Query **handlers** | `src/[bounded_context]/infrastructure/commands/*.py` · `queries/*.py` |
| `SQL*Repository` | `src/[bounded_context]/infrastructure/repositories/sql_[entity].py` |
| Bus wiring | `src/[bounded_context]/infrastructure/bus_wiring.py` |
| Presentation (inline requests, endpoints, presenters, router) | `src/[bounded_context]/presentation/` |

> Concrete example domain used in snippets below: feature = `projects`, entity =
> `Project`. So the entity lives at `src/common/domain/entities/projects/project.py`
> and the repo ABC at `src/projects/domain/repositories/project.py`.

## Domain layer

- [ ] **Entity** — Pydantic with `BaseModelMixin` (uuid7) + `TimestampMixin` (+ `SoftDeleteMixin` → `is_deleted: bool`). Expose `to_persist_dict` (enums → str) — repos use it to build the ORM. Example: `Project`.
- [ ] **Repository ABC** — `[Entity]Repository(ABC)` with the methods the use cases call: `find`, `persist`, `delete`, `filter_paginated`. Example: `ProjectRepository`.
- [ ] **Filters** — `[Entity]Filters(ListFilters)` (Pydantic, **not** `@dataclass`): `tenant_ids`, `cursor`, `limit`, plus entity-specific fields. Example: `ProjectFilters`.
- [ ] **Enums** — e.g. `[Entity]Status`. Example: `ProjectStatus` (`ACTIVE`, `ARCHIVED`).
- [ ] **Exceptions** — `[Entity]NotFoundError`, etc. as `DomainError` subclasses with `code="{bounded_context}.[ErrorName]"`, centralized in `src/common/domain/exceptions/[bounded_context].py`. Example: `ProjectNotFoundError` (code `"projects.ProjectNotFoundError"`).

## Application layer

- [ ] **Use cases** under `src/[bounded_context]/application/use_cases/[entity]/` (`[entity]` plural, e.g. `projects`): `creator.py` → `*Creator`, `getter.py`, `lister.py`, `updater.py`, `deleter.py` → `*Deleter`, plus state-mutators as needed (e.g. `archiver.py` → `*Archiver`). Each is a `@dataclass` extending `UseCase` with one `async def execute()`. Build only the verbs the feature needs. Example: `ProjectCreator`/`ProjectGetter`/`ProjectLister`/`ProjectUpdater`/`ProjectDeleter`/`ProjectArchiver`.
- [ ] **Mixin** — `mixins.py`/`_mixins.py` with `_get_[entity]()` doing the load + tenant-ownership check (raise `*NotFoundError`, never `Forbidden`). Example: `ProjectMixin._get_project()`.
- [ ] **Same-module writes call `self.repo.persist(entity)` directly** — do NOT invent a `Persist[Entity]Command`.
- [ ] **Only** for cross-module / async-via-SAQ work: add a `[Verb][Entity]Command` / `Get[Entity]ByIdQuery` message in `src/common/application/{commands,queries}/[area].py` + a handler in `src/[bounded_context]/infrastructure/{commands,queries}/`. If the command runs async, register it in `async_tasks_mapping` (`src/common/application/data/tasks_mapping.py`). Examples: cross-module `ArchiveProjectCommand`, async `ExportProjectsCommand`, query `GetProjectByIdQuery`.

## Infrastructure layer

- [ ] **ORM model** — `[Entity]ORM` with `UUIDTenantTimestampMixin` (required `tenant_id`) or `OptionalTenantTimestampMixin` (nullable `tenant_id`) (+ `SoftDeleteMixin` if applicable). Example: `ProjectORM`.
- [ ] **Builder** — `build_[entity](orm, ...) -> [Entity]`; coerce string columns to enums via `EnumClass.from_value(...)`. Example: `build_project`.
- [ ] **SQL repo** — `SQL[Entity]Repository` `@dataclass` with field `session: AsyncSession`; `persist` via `override_dict_properties(orm, instance.to_persist_dict)`; `selectinload(...)` every FK the Presenter reads (e.g. eager-load `ProjectMember` rows); soft-delete filter `is_deleted.is_(False)`. Example: `SQLProjectRepository`.
- [ ] **Bus wiring** — `[bounded_context]_wiring(domain, bus)` in `bus_wiring.py` registering every Command/Query handler for the module. Example: `projects_wiring`.
- [ ] **Add to `DomainContext`** (`src/common/domain/contexts/domain.py`): `[entity]_repository: [Entity]Repository`.
- [ ] **Add to `build_async_domain`** (`src/common/infrastructure/domain_builder.py`): `SQL[Entity]Repository(session=session)`.
- [ ] **Call `[bounded_context]_wiring(domain, bus)`** in `build_async_bus` (`src/common/infrastructure/bus_builder.py`) — once per module, not per entity.
- [ ] **Migration**: `make migrations ARG="add [bounded_context] [entity] table"` (illustrative — use your migration tool, e.g. Alembic). Inspect the generated file. Commit.

## Presentation layer

- [ ] **Request DTO** — `[Action][Entity]Request(CamelCaseRequest)` defined **inline in the endpoint file** (no shared `requests/` dir; no `to_params()`/`to_command()`). Read `request.field` directly. Example: `CreateProjectRequest`.
- [ ] **Endpoint** — async handler injecting `app_context: AppContext = Depends(get_app_context)` (or `DomainContextDep`/`BusContextDep`) + `current_tenant_user: TenantUser = Depends(get_required_tenant_user)`. Call `check_tenant_permission(...)` first (e.g. `ProjectPermission.view`).
- [ ] **Presenter** — `[Entity]Presenter(Presenter[Entity])` with `@property def to_dict`; positional `instance`. Return `ApiJSONResponse(content=presenter(obj).to_dict)`; lists return the `Page` after `apply_presenter`. Example: `ProjectPresenter`.
- [ ] **Router** — `[bounded_context]_router` using `add_api_route(...)` (not `@router.get`); gate with `dependencies=require_api_key` where needed. Example: `projects_router`.
- [ ] **Register in `config/router.py`** under the correct `SERVER_MODE` branch (e.g. `all` / `platform`), `include_router(..., prefix="/v1")`.

## Tenant safety (don't skip)

- [ ] List endpoints set `filters.tenant_ids = [current_tenant_user.tenant_id]`.
- [ ] Every `_get_[entity]` mixin compares `entity.tenant_id` against the current tenant.
- [ ] Tenant id comes from `current_tenant_user.tenant_id` / `.tenant.uuid` (server-set), **never** from the request body. `current_user.current_tenant_id` is only the user's last-selected hint, not an authorization boundary.
- [ ] Soft-deleted rows excluded by default (`is_deleted.is_(False)`).

## Quality gates

- [ ] format · lint · type-check · test (example toolchain: `make format` = ruff format, `make lint` = ruff, `make tycheck` = `ty`, `make test` = pytest — swap for your own).
- [ ] Manual smoke test of one endpoint (e.g. via Swagger UI).

## Tests

See `testing.md` for the kind → layer map and per-layer patterns. Cover domain
(pure), application use cases (mocked repos/buses), infrastructure repo (real DB +
factories, incl. a wrong-tenant case), and API (`@pytest.mark.api`).

## Things that often get forgotten

1. Adding the repo to `DomainContext` but not `build_async_domain` (or vice versa) → `TypeError` / unreachable repo.
2. Not calling `[bounded_context]_wiring` in `build_async_bus` → `CommandHandlerDoesNotExistError`.
3. Migration not generated / committed → CI breaks.
4. `selectinload` missing for a FK the Presenter reads → N+1 in production.
5. Router registered under the wrong `SERVER_MODE` → 404 on the deployed mode.
6. Wiring a `DomainEvent` to the `EventBus` — it is **dormant** (no subscribers in this template); use `EventPublisher` or an async command (`run_async=True`) instead (see `cqrs-buses.md`).
7. Logging a `DomainError`'s `context` to clients → leaks PII.
