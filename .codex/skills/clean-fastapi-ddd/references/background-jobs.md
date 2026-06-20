# Background Jobs (SAQ + Redis)

Async tasks run on **SAQ** (Simple Async Queue) over Redis. The same `Command`
type runs inline in a request OR on the worker — the only difference is the
`run_async` flag at dispatch. Worker entrypoint: `config/tasks.py`.

Run the worker: `saq config.tasks.worker_settings`.

## Enqueue from an endpoint / use case

`dispatch(command, run_async=True)` serializes the command and pushes it to SAQ
instead of executing the handler inline. Fire-and-forget — it returns `None`.

```python
# src/projects/presentation/endpoints/export_projects.py
await bus.command_bus.dispatch(
    command=ExportProjectsCommand(
        tenant_id=current_tenant_user.tenant.uuid,
        requested_by=current_tenant_user.uuid,
    ),
    run_async=True,
)
```

`run_async=False` (default) runs the handler inline in the current session. See
`cqrs-buses.md` for the bus contract.

## Serialization path

`MemoryCommandBus.dispatch(run_async=True)` → `SaqCommandEnqueuer.enqueue(command)`
(`src/common/infrastructure/buses/saq_command_enqueuer.py`):

1. Wraps the command in `MetaCommand` (`{command_name, payload}`) via
   `MetaCommand.from_command(command)` — `command_name` is `command.__class__.__name__`,
   `payload` is `command.to_dict`.
2. Calls `queue.enqueue("handle_command", command_data=meta.to_dict, key=<uuid4>, timeout=..., retries=..., retry_delay=..., retry_backoff=...)`.

So every `Command` MUST implement `to_dict` / `from_dict` (UUID/Decimal/datetime
must be stringified). And the command MUST be registered in `async_tasks_mapping`
or the worker drops it.

`SaqCommandEnqueuer` reuses the shared `queue` when present (API path, injected
via `SaqQueueDep` → `app.state.saq_queue`) and creates a temporary `Queue.from_url`
that it disconnects when `queue is None` (worker-to-worker enqueue).

## Register the command — `async_tasks_mapping`

`src/common/application/data/tasks_mapping.py`. The worker re-hydrates commands by
name from this dict. Unregistered → `AsyncTaskResolver` logs `NotRegisteredCommand`
and returns a failed `AsyncTask` (the job does NOT retry on this).

```python
async_tasks_mapping: dict[str, Type[Command]] = {
    SendEmailCommand.__name__: SendEmailCommand,
    ExportProjectsCommand.__name__: ExportProjectsCommand,
    ArchiveStaleProjectsCommand.__name__: ArchiveStaleProjectsCommand,
    # ...
}
```

## Worker side — `config/tasks.py`

`handle_command` is the single SAQ function. It rebuilds a fresh
session/domain/bus and delegates to `AsyncTaskResolver`, which dispatches the
re-hydrated command **inline** (`run_async` defaults to `False`).

```python
async def handle_command(ctx: dict[str, Any], *, command_data: dict[str, Any]) -> None:
    job = ctx["job"]
    database_config: DatabaseConfig = ctx["db_config"]
    async with database_config.session_maker() as session:
        bus = build_async_bus(session=session, domain=build_async_domain(session=session))
        task_result = await AsyncTaskResolver(
            command_bus=bus.command_bus,
            payload=command_data,
        ).execute()
```

`AsyncTaskResolver.execute()` (`src/common/application/buses/command_solver.py`):
`MetaCommand.from_dict(payload)` → look up class in `async_tasks_mapping` →
`command_class.from_dict(meta.payload)` → `command_bus.dispatch(command=...)`.
It re-raises on handler error so SAQ retries; returns an `AsyncTask` on success.

`startup`/`shutdown` put `db_config` on `ctx` and dispose the engine.

## Why rebuild session/domain/bus in the worker

The HTTP `AsyncSession` closed when the response shipped. The worker opens its
own session per job via `database_config.session_maker()` and builds a worker-scoped
bus with `build_async_bus(...)` — same builder the API uses. Never close over the
request session in a deferred command.

## Retries, timeouts, backoff

Defaults are SAQ enqueue kwargs sourced from `src/common/constants.py`:

```python
DEFAULT_WORKER_TIMEOUT = 180          # seconds
DEFAULT_WORKER_RETRIES = 3
DEFAULT_WORKER_RETRY_DELAY = 5.0      # seconds
DEFAULT_WORKER_RETRY_BACKOFF = True
```

Per-command timeout override: the `Command` base exposes a `timeout` property
(default `None` → falls back to `DEFAULT_WORKER_TIMEOUT`). Override it for long jobs:

```python
# src/common/application/commands/projects.py – ExportProjectsCommand
@property
def timeout(self) -> int:
    return 900  # 15 min
```

Because failed jobs retry up to `DEFAULT_WORKER_RETRIES`, **handlers must be
idempotent** — re-running must not duplicate rows, re-send the same notification,
or double-apply a state change. Dedupe on a stable key (e.g. skip work already
marked done, or upsert instead of insert).

## Cron / scheduled jobs

Cron functions take only `ctx` (no payload), rebuild the bus, and dispatch a
command inline. Register them as `CronJob` in `_cron_jobs`, gated by `SERVER_MODE`:

```python
# config/tasks.py
async def archive_stale_projects(ctx: dict[str, Any]) -> None:
    async with ctx["db_config"].session_maker() as session:
        bus = build_async_bus(session=session, domain=build_async_domain(session=session))
        await bus.command_bus.dispatch(command=ArchiveStaleProjectsCommand())

_cron_jobs = (
    [
        CronJob(archive_stale_projects, cron="0 * * * *", retries=DEFAULT_WORKER_RETRIES),
    ]
    if settings.SERVER_MODE in (AppMode.all, AppMode.platform)
    else []
)
```

## Redis / queue settings

- `settings.redis_url` is built from the Redis host/port/user/password/db settings
  (`src/common/settings.py`).
- Queue created with `Queue.from_url(settings.redis_url)` in both `config/lifespan.py`
  (API, stored on `app.state.saq_queue`) and `config/tasks.py` (`worker_settings["queue"]`).
- Worker concurrency = `DB_POOL_SIZE + DB_MAX_OVERFLOW` (`_calculate_concurrency`),
  so concurrent jobs never exceed the DB pool.

## Add a new async task end-to-end

1. Define the `Command` (`src/[bounded_context]/.../commands/` or `src/common/application/commands/`)
   as a `@dataclass(Command)` with `to_dict` / `from_dict` that fully serialize
   every field (stringify UUID/Decimal/datetime).
2. Wire its handler in the module's `[bounded_context]_wiring` (`command_bus.subscribe(...)`),
   same as a sync command — see `cqrs-buses.md`.
3. Register it in `async_tasks_mapping` (`src/common/application/data/tasks_mapping.py`).
4. Enqueue with `dispatch(command=..., run_async=True)`.
5. (Optional) Override `timeout` on the command for long-running work.
6. No `config/tasks.py` change needed for regular tasks — only cron jobs touch it.

## Common mistakes

- **Reading the return value of `run_async=True`** → always `None`.
- **Forgetting `async_tasks_mapping`** → worker logs `NotRegisteredCommand`, job
  succeeds-as-failure, work never runs.
- **`to_dict` leaking non-JSON types** (raw `UUID`/`Decimal`/`datetime`) → enqueue/
  re-hydrate breaks. Stringify and rebuild in `from_dict`.
- **Closing over the request `AsyncSession`** in a deferred command → it's gone by
  the time the worker runs. The worker makes its own.
- **Non-idempotent handlers** → retries duplicate side effects.
- **New cron not firing** → check `SERVER_MODE` gate in `_cron_jobs`.

## Cross-links

- `cqrs-buses.md` — Command/Query/Event bus contract, `[bounded_context]_wiring`.
- `config-bootstrap.md` — `lifespan`, `worker_settings`, settings/Redis URL.
- `dependency-injection.md` — `BusContextDep`, `SaqQueueDep`, `build_async_bus`.
- `scripts.md` — one-off/backfill scripts: the other way to run work outside the request cycle (manual, not queued).
