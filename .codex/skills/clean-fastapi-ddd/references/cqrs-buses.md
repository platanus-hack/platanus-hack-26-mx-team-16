# CQRS: Commands, Queries, Buses

Three buses live on `BusContext` (`src/common/domain/contexts/bus.py`):
`command_bus`, `query_bus`, `event_bus`. Writes → `CommandBus`. Reads → `QueryBus`.
Commands run **sync** (in-request) or **async** (enqueued to SAQ for a worker).
Queries are always sync.

> `event_bus` (the in-memory `DomainEvent` bus) is **dormant by design** — it is wired
> onto `BusContext` but nothing subscribes or publishes to it in this template. Route
> side-effects through `EventPublisher` (SSE/Redis) or async commands instead. See
> "Events" below.

## Contracts (domain)

```python
# src/common/domain/buses/commands.py
class Command(ABC):
    @property
    def timeout(self) -> int | None:        # per-command SAQ timeout override
        return None

    @property
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...      # serialize for SAQ payload

    @classmethod
    @abstractmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self: ...  # rebuild in worker

@dataclass
class CommandHandler[TCommand: Command](ABC):
    @abstractmethod
    async def execute(self, command: TCommand): ...

@dataclass
class CommandBus(ABC):
    @abstractmethod
    def subscribe(self, command: type[Command], handler: CommandHandler[Command]): ...
    @abstractmethod
    async def dispatch(self, command: Command, run_async: bool = False): ...

# src/common/domain/buses/queries.py
class Query:                                  # plain marker, not Pydantic
    pass

@dataclass
class QueryHandler[TQuery: Query, TResult](ABC):
    @abstractmethod
    async def execute(self, query: TQuery) -> TResult | None: ...

@dataclass
class QueryBus(ABC):
    @abstractmethod
    def subscribe(self, query: type[Query], handler: QueryHandler[Query, object]): ...
    @abstractmethod
    async def ask(self, query: Query) -> object | None: ...
```

Note: `Command`/`Query` payloads are `@dataclass`, **not** Pydantic `BaseModel`.
`dispatch` has **no** `defer_by` param. The query bus method is `ask`, not `dispatch`.

## Memory implementations (infrastructure)

```python
# src/common/infrastructure/buses/memory_command_bus.py
@dataclass
class MemoryCommandBus(CommandBus):
    enqueuer: CommandEnqueuer                 # SaqCommandEnqueuer in prod

    def __post_init__(self):
        self._commands: dict[type[Command], CommandHandler[Command]] = {}

    def subscribe(self, command, handler):
        if command in self._commands:
            raise CommandAlreadyExistError    # one handler per command type
        self._commands[command] = handler

    async def dispatch(self, command, run_async=False):
        if command.__class__ not in self._commands:
            raise CommandHandlerDoesNotExistError(command.__class__)
        if run_async:
            await self.enqueuer.enqueue(command)   # → SAQ, returns None
            return None
        return await self._commands[command.__class__].execute(command)
```

`MemoryQueryBus.ask` is the same lookup minus enqueue; missing handler raises
`QueryHandlerDoesNotExistError`. Exceptions live in
`src/common/infrastructure/buses/_exceptions.py`.

## Defining a command

```python
# src/common/application/commands/projects.py
@dataclass
class ArchiveProjectCommand(Command):
    project_id: UUID
    force: bool = False

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "force": self.force,
        }

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(
            project_id=UUID(kwargs["project_id"]),
            force=kwargs["force"],
        )
```

`to_dict`/`from_dict` only matter for commands dispatched with `run_async=True`
(they survive the SAQ round-trip). Convert UUIDs/Decimals to JSON-safe values in
`to_dict` and back in `from_dict`.

Handler (in `src/[bounded_context]/infrastructure/commands/`):

```python
# src/projects/infrastructure/commands/archive_project.py
@dataclass
class ArchiveProjectHandler(CommandHandler[ArchiveProjectCommand]):
    project_repository: ProjectRepository
    storage_service: StorageService
    query_bus: QueryBus
    event_publisher: EventPublisher

    async def execute(self, command: ArchiveProjectCommand): ...
```

Handlers are `@dataclass` with their dependencies as fields. They may hold
`query_bus` / `command_bus` to fan out, and `event_publisher` to emit SSE.

## Defining a query

```python
# src/common/application/queries/projects.py
@dataclass
class GetProjectByIdQuery(Query):
    instance_id: UUID

# src/projects/infrastructure/queries/get_project.py
@dataclass
class GetProjectByIdHandler(QueryHandler[GetProjectByIdQuery, Project]):
    project_repository: ProjectRepository

    async def execute(self, query: GetProjectByIdQuery) -> Project | None:
        return await self.project_repository.find(query.instance_id)
```

## Wiring — `[bounded_context]/infrastructure/bus_wiring.py`

Each feature exposes one `[bounded_context]_wiring(domain, bus)` function (e.g.
`projects_wiring`, `auth_wiring`, `users_wiring`). It instantiates handlers with
deps pulled off `domain` (the `DomainContext`) and registers them with **keyword**
args `command=`/`query=`/`handler=`.

```python
# src/projects/infrastructure/bus_wiring.py
def projects_wiring(domain: DomainContext, bus: BusContext):
    bus.query_bus.subscribe(
        query=GetProjectByIdQuery,
        handler=GetProjectByIdHandler(
            project_repository=domain.project_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=ArchiveProjectCommand,
        handler=ArchiveProjectHandler(
            project_repository=domain.project_repository,
            storage_service=domain.storage_service,
            query_bus=bus.query_bus,
            event_publisher=domain.event_publisher,
        ),
    )
```

## `build_async_bus` — assembly

```python
# src/common/infrastructure/bus_builder.py
def build_async_bus(
    session: AsyncSession,
    domain: DomainContext | None = None,
    saq_queue: Queue | None = None,
) -> BusContext:
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

A new feature is live only after its `_wiring` call is added here. The wired-feature
list lives in `bus_builder.py` imports — keep both in sync.

## Using buses from a use case / handler

```python
project = await self.query_bus.ask(GetProjectByIdQuery(instance_id=project_id))
await self.command_bus.dispatch(ArchiveProjectCommand(project_id=project_id))
```

## Async dispatch (background via SAQ)

```python
# src/projects/presentation/endpoints/export_projects.py
await bus.command_bus.dispatch(
    command=ExportProjectsCommand(
        tenant_id=current_tenant_user.tenant.uuid,
        requested_by=current_tenant_user.user_id,
    ),
    run_async=True,            # enqueues into SAQ, returns None
)
```

Round-trip for `run_async=True`:
1. `SaqCommandEnqueuer.enqueue` wraps the command in `MetaCommand` (`command_name`
   + `to_dict` payload) and enqueues SAQ job `"handle_command"`
   (`src/common/infrastructure/buses/saq_command_enqueuer.py`).
2. Worker `handle_command` (`config/tasks.py`) opens a fresh session, calls
   `build_async_bus`, then `AsyncTaskResolver`.
3. `AsyncTaskResolver` (`src/common/application/buses/command_solver.py`) looks the
   `command_name` up in `async_tasks_mapping`, rebuilds via `from_dict`, and
   dispatches it **sync** in the worker's context.

**A command is only async-dispatchable if it is registered in
`src/common/application/data/tasks_mapping.py`** (`async_tasks_mapping`). Missing
there → `AsyncTaskResolver` returns `NotRegisteredCommand` and silently drops it
(no exception at the API boundary). See `background-jobs.md`.

## Events

This template ships no active domain-event flow. Two mechanisms cover "something
happened":

- **`EventPublisher`** (`src/common/domain/services/event_publisher.py`) — async
  `publish(channel, event)`, used for SSE/realtime. Handlers get it as
  `domain.event_publisher` and emit `SseEvent`s:
  ```python
  event = SseEvent(event_type=SseEventType.PROJECT_ARCHIVED)
  await self.event_publisher.publish(channel=projects_channel(tenant_id), event=event)
  ```
- **Async commands** — to react to something elsewhere, `dispatch(..., run_async=True)`
  the follow-up command.

`EventBus` / `DomainEvent` / `MemoryEventBus` (`src/common/domain/buses/events.py`,
sync `publish(events: list[DomainEvent])`) is plumbed onto `BusContext.event_bus`
but ships with **zero** subscribers or publishers. It's an intentional extension
point, not a path to use today — reach for `EventPublisher` or an async command.

## Decision tree

```
In a use case / handler I need to...
├─ Read (no mutation)
│  ├─ List with filters/pagination   → repo directly (in a Lister) or Filter*Query
│  └─ Get one                          → Query + QueryHandler via query_bus.ask
├─ Mutate (create/update/delete)      → Command + CommandHandler via dispatch
├─ Mutate later / off the request     → dispatch(..., run_async=True) + register in
│                                        async_tasks_mapping
└─ Notify a client in realtime        → event_publisher.publish(channel, SseEvent)
```

## Common mistakes

- **Forgot to wire** → `CommandHandlerDoesNotExistError` / `QueryHandlerDoesNotExistError`
  at dispatch/ask. Add it to `[bounded_context]_wiring` and confirm that function is called
  in `build_async_bus`.
- **Two subscribers, one command** → `CommandAlreadyExistError`. Exactly one handler
  per command type (queries: `QueryAlreadyExistError`).
- **`run_async=True` without registering in `async_tasks_mapping`** → the worker
  drops it as `NotRegisteredCommand`. No error surfaces in-request.
- **`run_async=True` and expecting a return** → you always get `None`.
- **Bad `to_dict`/`from_dict`** for an async command → fails round-trip in the worker.
  Keep payload JSON-safe (stringify UUID/Decimal/datetime).
- **Business logic in the handler** → handlers stay thin and delegate to
  repos/services/use-cases.
- **Using `event_bus`** → it's a dormant extension point; use `EventPublisher` or an
  async command instead.

## See also

- `background-jobs.md` — SAQ worker, cron jobs, `handle_command`, retries.
- `dependency-injection.md` — `DomainContext`, `BusContext`, `AppContext`, `Depends`.
- `use-cases.md` — orchestration that drives these buses.
- `config-bootstrap.md` — where `build_async_bus` is invoked per request and in workers.
