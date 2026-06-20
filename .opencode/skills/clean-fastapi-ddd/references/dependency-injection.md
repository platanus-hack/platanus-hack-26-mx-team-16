# Dependency Injection: AppContext / DomainContext / BusContext

Every request gets a fresh graph: one `AsyncSession` → all repos/services
(`DomainContext`) → buses with handlers wired (`BusContext`) → `AppContext`.
FastAPI memoizes each dep within a request, so the session/domain/bus are
each built exactly once.

## The three contexts

### `DomainContext` — `src/common/domain/contexts/domain.py`

`@dataclass` with one field per repository / domain service. Only **interfaces**
(ABCs from `src/[bounded_context]/domain/repositories/` and `src/common/domain/services/`)
appear — no SQL, no vendor SDKs. Keep one field per repo and one per service;
add your own as the app grows.

```python
@dataclass
class DomainContext:
    user_repository: UserRepository
    tenant_repository: TenantRepository
    project_repository: ProjectRepository
    # ... one field per repo
    token_service: TokenService
    storage_service: StorageService
    notification_service: NotificationService
    event_publisher: EventPublisher
    # ... add yours
```

`token_service`, `storage_service`, `notification_service`, `event_publisher`
are the example service set — swap them for whatever ports your app needs.

### `BusContext` — `src/common/domain/contexts/bus.py`

```python
@dataclass
class BusContext:
    command_bus: CommandBus
    query_bus: QueryBus
    event_bus: EventBus
```

### `AppContext` + `AppContextBuilder` — `src/common/infrastructure/context_builder.py`

```python
@dataclass
class AppContext:
    domain: DomainContext
    bus: BusContext
    scheduler: None = None


class AppContextBuilder:
    @classmethod
    def from_env(cls, environment=None, domain=None, bus=None) -> AppContext:
        environment = environment or settings.ENVIRONMENT
        if environment.is_production or environment.is_development:
            return AppContext(domain=domain, bus=bus)
        if environment.is_testing:
            return AppContext(
                domain=MockDomainSingleton.instance,
                bus=MockBusSingleton.instance,
            )
        raise NotImplementedError(...)
```

Tests get `MockDomainSingleton` / `MockBusSingleton` (`src/common/infrastructure/contexts/`).

## Builders

### `build_async_domain(session)` — `src/common/infrastructure/domain_builder.py`

Instantiates every `SQL*` repo with the **same** `session` (that single session
is what makes one transaction span multiple repos). Stateless/shared services
are `@lru_cache(maxsize=1)` singletons (e.g. `get_notification_service`,
`get_event_publisher`) so one HTTP/Redis pool is reused across requests and
background jobs.

```python
def build_async_domain(session: AsyncSession) -> DomainContext:
    return DomainContext(
        user_repository=SQLUserRepository(session=session),
        tenant_repository=SQLTenantRepository(session=session),
        project_repository=SQLProjectRepository(session=session),
        # ... every SQL* repo gets the same session
        token_service=JwtTokenService(
            token_builder=JwtTokenBuilder(),
            token_store=RedisTokenStore(redis_client=Redis.from_url(settings.redis_url)),
        ),
        storage_service=S3StorageService(),
        notification_service=get_notification_service(),  # EmailNotificationService
        event_publisher=get_event_publisher(),
    )
```

```python
@lru_cache(maxsize=1)
def get_notification_service() -> NotificationService:
    return EmailNotificationService()
```

### `build_async_bus(session, domain=None, saq_queue=None)` — `src/common/infrastructure/bus_builder.py`

Builds the three in-memory buses, then calls each module's `[bounded_context]_wiring(domain, bus)`
to subscribe handlers. `domain` defaults to a fresh `build_async_domain(session)`
when omitted (the SAQ-worker path passes it explicitly).

```python
def build_async_bus(session, domain=None, saq_queue=None) -> BusContext:
    domain = domain or build_async_domain(session=session)
    bus = BusContext(
        command_bus=MemoryCommandBus(
            enqueuer=SaqCommandEnqueuer(redis_url=settings.redis_url, queue=saq_queue),
        ),
        query_bus=MemoryQueryBus(),
        event_bus=MemoryEventBus(),
    )
    auth_wiring(domain, bus)
    users_wiring(domain, bus)
    tenants_wiring(domain, bus)
    projects_wiring(domain, bus)
    return bus
```

Adding a new module means importing and calling its `[bounded_context]_wiring(domain, bus)` here.
See `cqrs-buses.md` for how `[bounded_context]_wiring` subscribes handlers.

## The Depends chain — `src/common/infrastructure/dependencies/common.py`

```python
async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession]:
    database_config: DatabaseConfig = request.app.state.database_config
    async with database_config.session_maker() as session:
        request.state.db_session = session
        try:
            yield session
        finally:
            await session.close()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_database_session)]


async def get_domain_context(session: AsyncSessionDep) -> DomainContext:
    return build_async_domain(session=session)

DomainContextDep = Annotated[DomainContext, Depends(get_domain_context)]


def get_saq_queue(request: Request) -> Queue:
    return cast("Queue", request.app.state.saq_queue)

SaqQueueDep = Annotated[Queue, Depends(get_saq_queue)]
RedisDep = Annotated[Redis, Depends(get_redis_client)]  # get_redis_client from dependencies/rate_limit.py


async def get_bus_context(
    session: AsyncSessionDep,
    domain: DomainContextDep,
    saq_queue: SaqQueueDep,
) -> BusContext:
    return build_async_bus(session=session, domain=domain, saq_queue=saq_queue)

BusContextDep = Annotated[BusContext, Depends(get_bus_context)]


async def get_app_context(domain: DomainContextDep, bus: BusContextDep) -> AppContext:
    return AppContext(domain=domain, bus=bus)
```

> There is **no `AppContextDep` alias**. Aliases stop at `DomainContextDep` /
> `BusContextDep`; endpoints that need the whole context inject the function:
> `app_context: AppContext = Depends(get_app_context)`.

Resolution order per request: `get_database_session` → `get_domain_context`
→ `get_bus_context` → `get_app_context`.

## Auth deps — `src/common/infrastructure/dependencies/session.py`

`get_authenticated_user` pulls the `DomainContextDep` + `BusContextDep`, reads the
bearer token via `token_service.get_claims(..., scope=JwtTokenScope.ACCESS)`, then
asks `GetUserByIdQuery` on the query bus. Raises `InvalidOrExpiredTokenError`.

```python
AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]
```

Use `AuthenticatedUserDep` for identity. For tenant-scoped endpoints inject
`current_tenant_user: TenantUser = Depends(get_required_tenant_user)` and scope by
`current_tenant_user.tenant_id` / `.tenant.uuid`. `current_user.current_tenant_id` is
only the user's last-selected-tenant hint — not an authorization boundary. See
`auth-multi-tenant.md`.

## Using it from an endpoint

Endpoints inject what they need: the alias form (`BusContextDep` /
`DomainContextDep`) when one piece suffices, or the bare `Depends(get_app_context)`
form when the handler needs both. Response goes through `ApiJSONResponse`
(snake_case → camelCase auto-conversion).

```python
async def list_projects(
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    bus_context: BusContextDep = ...,
):
    result = await bus_context.query_bus.ask(
        query=ListProjectsQuery(tenant_id=current_tenant_user.tenant_id),
    )
    projects = result if isinstance(result, list) else []
    return ApiJSONResponse(
        content=[ProjectPresenter(instance=p).to_dict for p in projects],
    )
```

## Outside the request cycle — SAQ workers (`config/tasks.py`)

Workers have no `Request`, so they open their own session and build the bus by
hand. Same builders, no `Depends`:

```python
async with database_config.session_maker() as session:
    bus = build_async_bus(session=session, domain=build_async_domain(session=session))
    await bus.command_bus.dispatch(command=ExportProjectsCommand())
```

`ctx["db_config"]` is the worker's `DatabaseConfig`. See `background-jobs.md`.

## Adding a new dependency

1. **New repo/service** → add an interface field to `DomainContext`
   (`contexts/domain.py`) and construct it (with `session=session`) in
   `build_async_domain` (`domain_builder.py`). Skipping either means handlers
   can't reach it.
2. **New module of handlers** → import + call `[bounded_context]_wiring(domain, bus)` in
   `build_async_bus`.
3. **New request-scoped dep** → add `get_<thing>(...)` + `XxxDep = Annotated[T,
   Depends(get_<thing>)]` in `dependencies/common.py`; compose from existing
   `*Dep` aliases so FastAPI memoizes the shared session.

## Common mistakes

- Add a repo to `DomainContext` but forget `build_async_domain` (or vice versa) → `TypeError` on construction or unreachable repo.
- Passing different sessions to different repos → breaks transactional atomicity. One session per request.
- Constructing handlers in the endpoint instead of in `[bounded_context]_wiring` → leaks infrastructure into presentation.
- Storing mutable state on `DomainContext` → it's request-scoped and short-lived. State belongs in Redis/DB.
- Pulling the whole `AppContext` when you only need the bus — inject `BusContextDep` / `DomainContextDep` (there is no `AppContextDep` alias).
