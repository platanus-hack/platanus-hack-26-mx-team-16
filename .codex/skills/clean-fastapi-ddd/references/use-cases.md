# Use Cases (Application Layer)

A use case orchestrates one operation. It takes repositories, domain services, and
(only when reading cross-module data) a `QueryBus` as constructor params, mutates
domain entities, and returns a domain entity / `Page` / tuple. It **never** imports
FastAPI, SQLAlchemy, or HTTP types, and raises `DomainError` subclasses — never
`HTTPException`.

## Base interface

```python
# src/common/domain/interfaces/use_case.py
class UseCase(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs) -> object | None:
        raise NotImplementedError
```

Use cases are `@dataclass` so dependencies are explicit constructor fields. The single
public method is `execute()`. Default `None`/list fields go last; use `__post_init__`
for defaults that can't be literals (e.g. `self.members = self.members or []`).

## The standard set per entity

Under `src/[bounded_context]/application/use_cases/[entity]/` (the folder is the entity, snake
singular, e.g. `project`):

- `creator.py`   → `[Entity]Creator`   — create + persist
- `getter.py`    → `[Entity]Getter`    — fetch one, tenant-checked
- `lister.py`    → `[Entity]Lister`    — paginated list
- `updater.py` / `archiver.py` → mutate state
- `deleter.py`   → `[Entity]Deleter`   — delete (soft or hard)
- `mixins.py` or `_mixins.py` → shared `_get_[entity]` + validation helpers

Not every entity has all five; only build the verbs the feature needs.

## Mixin pattern — load + ownership check

The mixin centralizes "fetch by id or raise". Use cases inherit it so the check can't
be forgotten. It declares the fields it reads as **class-level annotations** (the
concrete `@dataclass` use case supplies them).

```python
# src/projects/application/use_cases/project/_mixins.py
class ProjectMixin:
    project_id: UUID
    project_repository: ProjectRepository

    async def _get_project(self) -> Project:
        project = await self.project_repository.find(self.project_id)
        if not project:
            raise ProjectNotFoundError
        return project
```

Tenant ownership is enforced by comparing on the loaded entity and raising
**`NotFound` (not `Forbidden`)** so cross-tenant ids leak nothing:

```python
# src/projects/application/use_cases/project/getter.py
project = await self.project_repository.find(self.project_id)
if not project or project.tenant_id != self.tenant.uuid:
    raise ProjectNotFoundError
```

A feature may have several focused mixins when domain rules grow (e.g. a load mixin, a
validation mixin, a state-transition mixin) — each grouping related rules.

## Creator (calls repo directly; QueryBus only for cross-module reads)

```python
# src/projects/application/use_cases/project/creator.py
@dataclass
class ProjectCreator(UseCase):
    name: str
    status: ProjectStatus
    project_repository: ProjectRepository
    query_bus: QueryBus
    tenant_id: UUID
    notification_service: NotificationService
    description: str | None = None
    members: list[ProjectMember] = None

    async def execute(self) -> Project:
        tenant = await self.query_bus.ask(GetTenantByIdQuery(tenant_id=self.tenant_id))
        project = Project(
            uuid=uuid7(),                       # from uuid6 import uuid7
            tenant_id=self.tenant_id,
            name=self.name,
            description=self.description,
            status=ProjectStatus.ACTIVE,
            members=self._build_members(),
            created_at=utc_now(),
        )
        saved = await self.project_repository.persist(project)   # repo, not command bus
        await self.notification_service.notify_project_created(saved, tenant)
        return saved
```

Notes:
- `uuid7()` from `uuid6`; `utc_now()` from `src.common.application.helpers.datetimes`.
- Cross-module reads (e.g. the owning tenant) go through
  `query_bus.ask(GetTenantByIdQuery(...))` — defined in
  `src.common.application.queries.tenants`.
- Same-module writes/reads use the injected repository directly.

## Getter

```python
@dataclass
class ProjectGetter(UseCase):
    tenant: Tenant
    project_id: UUID
    project_repository: ProjectRepository

    async def execute(self) -> Project:
        project = await self.project_repository.find(self.project_id)
        if not project or project.tenant_id != self.tenant.uuid:
            raise ProjectNotFoundError
        return project
```

When an operation needs related entities, return a tuple (e.g.
`tuple[Project, list[ProjectMember]]`) — never a presenter.

## Lister (repo.filter_paginated, returns `Page`)

```python
# src/projects/application/use_cases/project/lister.py
@dataclass
class ProjectLister(UseCase):
    tenant_id: UUID
    filters: ProjectFilters
    project_repository: ProjectRepository

    async def execute(self) -> Page:
        return await self.project_repository.filter_paginated(
            tenant_id=self.tenant_id, filters=self.filters,
        )
```

The endpoint scopes the tenant before listing: `filters.tenant_ids = [current_tenant_user.tenant_id]`.
See `pagination.md` for `Page` / `filter_paginated` / `apply_presenter`.

## Updater / Archiver (load via mixin, mutate, persist)

```python
# src/projects/application/use_cases/project/archiver.py
@dataclass
class ProjectArchiver(ProjectMixin, UseCase):
    project_id: UUID
    project_repository: ProjectRepository

    async def execute(self):
        project = await self._get_project()        # ownership check
        project.status = ProjectStatus.ARCHIVED
        await self.project_repository.persist(project)
```

Entities are Pydantic models mutated in place (`project.status = ...`) then
re-persisted; `repository.persist` upserts.

## Deleter

```python
# src/projects/application/use_cases/project/deleter.py
@dataclass
class ProjectDeleter(ProjectMixin, UseCase):
    project_id: UUID
    project_repository: ProjectRepository

    async def execute(self):
        project = await self._get_project()
        await self.project_repository.delete(project.uuid)
```

## How endpoints construct a use case

The endpoint instantiates the dataclass inline, pulling deps off `AppContext`, then
calls `.execute()`. The use case never sees `Depends`, `Request`, or the session.

```python
# src/projects/presentation/endpoints/projects.py
project = await ProjectCreator(
    tenant_id=current_tenant_user.tenant.uuid,
    name=request.name,
    description=request.description,
    status=ProjectStatus.ACTIVE,
    project_repository=app_context.domain.project_repository,
    notification_service=app_context.domain.notification_service,
    query_bus=app_context.bus.query_bus,
).execute()
```

Repos come from `app_context.domain.[entity]_repository`, services from
`app_context.domain.[service]` (e.g. `notification_service`), buses from
`app_context.bus.{query_bus,command_bus}`. See `dependency-injection.md`.

## Validation boundary: request vs use case

| Where | Validates | Tools |
|---|---|---|
| Request DTO (`presentation/.../requests` or inline `CamelCaseRequest`) | Shape: required fields, types, formats, ranges | Pydantic `Field`, validators |
| Use case + mixins | Domain rules: existence, tenant ownership, state transitions, uniqueness, cross-entity consistency | repo lookups → raise `DomainError` |

Request validation rejects malformed input with 422 before the use case runs. Domain
validation needs the DB / other entities and lives only in the use case, raising a
typed `DomainError` (e.g. `ProjectNotFoundError`).

## Raising errors

`DomainError` subclasses live in `src/common/domain/exceptions/[bounded_context].py` and set
`code`, `message`, `status_code`, `context`:

```python
# src/common/domain/exceptions/projects.py
class ProjectNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="projects.ProjectNotFoundError",
            message="Project Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )
```

Pass `context={...}` to attach debugging data (e.g.
`ProjectNotFoundError(context={"project_id": project_id})`). Global handlers map
`status_code` → HTTP. See `errors.md`.

## Complex / orchestration-heavy flows

When one operation coordinates an external service call + several entities, split
helper steps into sibling files in the same `[entity]/` folder, for example:

```
project/   creator.py  archiver.py  member_synchronizer.py  export_builder.py
```

The top-level `[Entity]Creator` / `[Entity]Archiver` composes these. Big multi-step
entry points keep this shape — one public `execute()`, private `_helpers`, no
FastAPI/SQLAlchemy imports. Genuinely cross-module or fire-and-forget work is dispatched
through the command bus instead (e.g. `ArchiveProjectCommand`, or
`ExportProjectsCommand` with `run_async=True`) — see `cqrs-buses.md`.

## Common mistakes

- **Returning a presenter** → use cases return domain entities/`Page`/tuples; presenters live in `presentation`.
- **Importing `Session` / SQLAlchemy** → wrong layer. That work belongs in a repository.
- **Raising `HTTPException`** → raise a `DomainError` subclass; handlers convert to HTTP.
- **Using `Forbidden` for cross-tenant access** → raise the entity's `[Entity]NotFoundError` (don't leak existence).
- **Skipping the ownership check** → load through the mixin's `_get_[entity]` or compare `entity.tenant_id` explicitly.
- **Inventing a `Persist[Entity]Command`** → same-module persistence is `await self.[entity]_repository.persist(entity)` directly. The `command_bus` is for genuine cross-module/event-driven writes (see `cqrs-buses.md`), not for routine CRUD.
