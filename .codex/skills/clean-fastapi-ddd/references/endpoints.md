# Endpoints, Requests, Presenters, Router

The presentation layer is thin: check permission, read the request DTO, call a
use case or dispatch a command/query, format with a Presenter, return
`ApiJSONResponse`. Endpoints live in `src/[bounded_context]/presentation/endpoints/`.

## Request DTOs

Defined **inline in the endpoint file** (no `requests/` directory). Inherit
`CamelCaseRequest` from `src.common.domain.entities.common.requests`.

```python
# src/projects/presentation/endpoints/projects.py
from src.common.domain.entities.common.requests import CamelCaseRequest

class CreateProjectRequest(CamelCaseRequest):
    name: str = Field()
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    description: str | None = Field(default=None)
```

`CamelCaseRequest` config: `alias_generator=to_snake`, `populate_by_name=True`,
`extra="ignore"`, `str_strip_whitespace=True`, plus a `convert_camel_to_snake`
`model_validator(mode="before")` that recursively snake-cases nested dict/list
keys. So a `firstName` body field binds to `first_name` regardless of the
inbound case.

The endpoint reads `request.field` directly and either passes kwargs into a
use-case constructor (`ProjectCreator(name=request.name, ...)`) or builds the
Command/Query inline and dispatches it (see below). There is **no
`to_params()` / `to_command()` convention** — keep the mapping explicit in the
handler.

## Endpoint handler

One async function per route. Inject context and the current tenant user via
`Depends(...)`. Always `check_tenant_permission` first.

```python
# src/projects/presentation/endpoints/projects.py
async def archive_project(
    project_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ProjectPermission.archive])

    project = await app_context.bus.command_bus.dispatch(
        command=ArchiveProjectCommand(
            project_id=project_id,
            tenant_id=current_tenant_user.tenant.uuid,
            initiated_by=current_tenant_user.uuid,
        )
    )
    return ApiJSONResponse(
        content=ProjectPresenter(project).to_dict,
        status_code=http_status.HTTP_200_OK,
    )
```

Dispatch points (from `app_context.bus`):
- write: `await app_context.bus.command_bus.dispatch(command=...)`
- read: `await app_context.bus.query_bus.ask(query=...)`

Use the command bus only for cross-module or async (`run_async=True`) work.
Same-module CRUD goes straight through a use case + `repo.persist()` — no bus,
inject repos/services from `app_context.domain`:

```python
# src/projects/presentation/endpoints/projects.py
project = await ProjectCreator(
    tenant_id=current_tenant_user.tenant.uuid,
    name=request.name,
    project_repository=app_context.domain.project_repository,
    notification_service=app_context.domain.notification_service,
    query_bus=app_context.bus.query_bus,
).execute()
```

### Imports (exact paths)

```python
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context, get_domain_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.domain.entities.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
```

### DI shorthand (`Annotated` aliases)

You can inject with bare `Depends(...)` or with `Annotated` alias deps — either
style is fine; pick one per module. The aliases that exist
(`dependencies/common.py`): `AsyncSessionDep`, `DomainContextDep`,
`BusContextDep`; plus `AuthenticatedUserDep` (`dependencies/session.py`, yields a
`User`) and `TenantUserDep` / `RequiredTenantUserDep` (`dependencies/tenant.py`).
There is **no `AppContextDep`** — for the full `AppContext` inject the function
directly: `Depends(get_app_context)`. See `references/dependency-injection.md`.

## Lists / pagination

Mutate the `*Filters` DTO (bound via `Depends()`), run the lister/query, then
`apply_presenter` in place and return the `Page`. `ApiJSONResponse` detects a
`Page` and wraps it as `ApiResponse(data=items, pagination=...)`.

```python
# src/projects/presentation/endpoints/projects.py
async def get_projects(
    domain_context: DomainContext = Depends(get_domain_context),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    filters: ProjectFilters = Depends(),
):
    check_tenant_permission(current_tenant_user, permissions=[ProjectPermission.view])
    filters.tenant_ids = [current_tenant_user.tenant_id]
    filters.localize(time_zone=str(current_tenant_user.tenant.time_zone))

    current_page = await ProjectLister(
        tenant_id=current_tenant_user.tenant_id,
        filters=filters,
        project_repository=domain_context.project_repository,
    ).execute()

    current_page.apply_presenter(ProjectPresenter)
    return ApiJSONResponse(content=current_page, status_code=status.HTTP_200_OK)
```

`Page.apply_presenter` (`src/common/domain/entities/common/pagination.py`):
`self.items = [presenter_class(item).to_dict for item in self.items]`. See
`references/pagination.md`.

## Presenters

`Presenter` is a `Protocol[TItem]` at `src.common.domain.interfaces.presenter`:
`__init__(self, instance)` + a `to_dict` property. Implementations are
`@dataclass` with a positional `instance` field. Presenters live in
`src/[bounded_context]/presentation/presenters/` (module-specific) or
`src/common/presentation/presenters/` (shared).

```python
# src/projects/presentation/presenters/project.py
@dataclass
class ProjectPresenter(Presenter[Project]):
    instance: Project

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "status": optional_enum_string(self.instance.status),
            "created_at": optional_datetime_string(self.instance.created_at),
            "members": self._get_members(),  # nested presenter
        }
```

Notes:
- Keys are snake_case; the response middleware camelCases them on the way out.
- Use the `optional_*` helpers (`src/common/application/helpers/`) for nullable enums/decimals/datetimes.
- Compose presenters for nested objects (e.g. a `ProjectMemberPresenter`).
- One entity may have several presenters for different audiences/shapes.

## Response: `ApiJSONResponse`

`src/common/infrastructure/responses/api_json.py`, extends
`CamelCaseJSONResponse`. Its `render`:
- a `Page` → `ApiResponse(data=items, pagination=Pagination.from_page(...), timestamp=...)`
- any other jsonable content → `ApiResponse(data=content, timestamp=...)`
- an error dict (`{"errors": ...}`) → only injects `timestamp`

`CamelCaseJSONResponse` (`responses/camel_case.py`) then converts every key to
camelCase via `jsonable_encoder_camel` + `CamelCaseJSONEncoder`. Pass a `to_dict`
or a `Page`; do not wrap it yourself.

## camelCase ↔ snake_case (both directions)

- **Inbound request body**: `CamelCaseToSnakeCaseMiddleware`
  (`src/common/infrastructure/middlewares/camel_case.py`, registered in
  `config/main.py`) rewrites JSON body keys to snake_case before validation;
  `CamelCaseRequest`'s validator is a second safety net for nested keys.
- **Outbound response**: `ApiJSONResponse` → `CamelCaseJSONResponse` camelCases
  every key. Presenter dicts stay snake_case internally.

## Router (`add_api_route`)

```python
# src/projects/presentation/router.py
from fastapi import APIRouter
from src.common.infrastructure.dependencies.api_keys import require_api_key

projects_router = router = APIRouter(prefix="/projects", tags=["projects"])

projects_router.add_api_route(
    path="/{project_id}/archive",
    endpoint=archive_project,
    methods=["POST"],
    dependencies=require_api_key,
)
```

- The module router sets its own `prefix=` and `tags=` on `APIRouter(...)`.
- `require_api_key` is an optional list of header-validating deps (e.g.
  `[Depends(get_integration_api_key)]` in `dependencies/api_keys.py`). Apply per
  route via `dependencies=require_api_key`; omit it on public routes.
- `add_api_route` keeps path / method / deps / summary visible together — easier
  to audit which routes are auth-gated.

## Register in `config/router.py`

Lazy-import the module router inside the `SERVER_MODE` guard, then `include_router`
with the `/v1` prefix (the module already carries `/projects`):

```python
# config/router.py
if settings.SERVER_MODE in (AppMode.all, AppMode.platform):
    from src.projects.presentation.router import projects_router
    api_router.include_router(projects_router, prefix="/v1", tags=["projects"])
```

`AppMode` is `src.common.domain.enums.common.AppMode`. Use the modes that match
your deploy topology (`all` / `platform` here are examples — replace with your
own); `common_router` (health) is always included.

## Common mistakes

- **Skipping `check_tenant_permission`** — every tenant-scoped endpoint calls it first with the right `*Permission`.
- **Deriving tenant from the request body** instead of `current_tenant_user.tenant_id` / `.tenant.uuid` → cross-tenant leak.
- **Returning the Pydantic entity / `model_dump()`** instead of a Presenter `to_dict` → couples the API to the domain shape.
- **Manually wrapping in `ApiResponse`** — `ApiJSONResponse` does it; pass `to_dict` or a `Page`.
- **Catching `DomainError`** in the endpoint — the global handler maps it (see `references/errors.md`).
- **Inventing `to_command()` / `to_params()`** — read `request.field` and build the command / use-case inline.
- **`@router.get(...)` decorators** — use `add_api_route(...)` for consistency.

## See also

- `references/dependency-injection.md` — `AppContext`, `get_app_context`, `*Dep` aliases
- `references/cqrs-buses.md` — `command_bus.dispatch` / `query_bus.ask`
- `references/use-cases.md` — when to use a use case vs a bus command
- `references/pagination.md` — `Page`, `Pagination`, `apply_presenter`
- `references/errors.md` — `DomainError` → HTTP mapping
- `references/auth-multi-tenant.md` — `get_required_tenant_user`, permissions
