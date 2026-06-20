# Utility scripts (`scripts/*.py`)

One-off / operational tasks run OUTSIDE the request cycle: backfills, recalculations, bootstrappers, re-syncs. They reuse domain repos / use-cases / buses — never raw SQL for writes when a use-case exists.

Patterns a script falls into:
- **Dry-run/apply backfill** — read rows, log `would_*`, mutate + commit only under `--apply`.
- **Per-tenant bootstrapper** — iterate tenants, run a use-case once per tenant.
- **Full-domain task** — build the wired `build_async_domain`/`build_async_bus`, use per-item sessions, optionally a CSV report.
- **Interactive task** — `typer.prompt`/`confirm`, no `--apply` (the prompt is the safety gate).

Keep external-integration helpers (raw `httpx` + stdlib `logging` + `dotenv`) separate from this DB pattern — don't copy them for DB work.

## Skeleton (copy-paste)

```python
"""
<One-line what + why>.

Usage:
    python scripts/<name>.py                       # dry run (all)
    python scripts/<name>.py --apply               # apply
    python scripts/<name>.py --tenant-id <uuid>    # filter
"""

import asyncio
from typing import Annotated
from uuid import UUID

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.logging import get_logger
from src.common.database.config import get_database_config

logger = get_logger(__name__)


async def dry_run(session: AsyncSession, tenant_id: UUID | None) -> None:
    # read + log "would_*" events; NEVER commit
    logger.info("dry_run.start")
    ...
    logger.info("dry_run.done", would_change=0)


async def apply_changes(session: AsyncSession, tenant_id: UUID | None) -> None:
    logger.info("apply.start")
    updated = 0
    # mutate entities/ORM, log progress every 100
    await session.commit()                          # commit ONLY here
    logger.info("apply.done", updated=updated)


async def run(should_apply: bool, tenant_id: UUID | None = None) -> None:
    db_config = get_database_config()
    async with db_config.session_maker() as session:
        if should_apply:
            await apply_changes(session, tenant_id)
        else:
            await dry_run(session, tenant_id)
    logger.info("finished", mode="apply" if should_apply else "dry_run")


app = typer.Typer()


@app.command()
def main(
    apply: Annotated[bool, typer.Option(help="Apply changes (default is dry run)")] = False,
    tenant_id: Annotated[str | None, typer.Option(help="Filter by tenant UUID")] = None,
) -> None:
    asyncio.run(run(should_apply=apply, tenant_id=UUID(tenant_id) if tenant_id else None))


if __name__ == "__main__":
    app()
```

## Worked example — `scripts/backfill_project_status.py`

A backfill that normalizes legacy `Project` rows to a default `ProjectStatus`, driven through the repo, dry-run by default:

```python
async def dry_run(session: AsyncSession, tenant_id: UUID | None) -> None:
    repo = SQLProjectRepository(session=session)
    projects = await repo.find_all(tenant_id=tenant_id)
    would_change = sum(1 for p in projects if p.status is None)
    logger.info("dry_run.done", total=len(projects), would_change=would_change)


async def apply_changes(session: AsyncSession, tenant_id: UUID | None) -> None:
    repo = SQLProjectRepository(session=session)
    projects = await repo.find_all(tenant_id=tenant_id)
    updated = 0
    for i, project in enumerate(projects):
        if project.status is None:                  # compare before write → idempotent
            project.status = ProjectStatus.ACTIVE
            await repo.persist(project)
            updated += 1
        if i % 100 == 0:
            logger.info("apply.progress", processed=i, total=len(projects))
    await session.commit()
    logger.info("apply.done", updated=updated)
```

## Non-negotiable conventions

**Entrypoint** = Typer, not argparse. `app = typer.Typer()`, `@app.command() def main(...)`, `if __name__ == "__main__": app()`. CLI options via `Annotated[T, typer.Option(...)]`. `main` parses args (e.g. `UUID(...)`, `date.fromisoformat(...)`) then `asyncio.run(run(...))`. `main` is sync; `run` is the async body.

**Session bootstrap** — there is NO request DI. Get a session factory yourself:
```python
db_config = get_database_config()            # src.common.database.config
async with db_config.session_maker() as session:
    ...
```
`session_maker` has `expire_on_commit=False`, `autocommit=False`. You own the commit — call `await session.commit()` explicitly, only in the apply path.

**Logging** = structured: `logger = get_logger(__name__)` from `src.common.application.logging`. Emit `logger.info("event.name", key=value, ...)` — first arg is an event slug (`dry_run.start`, `would_change`, `apply.progress`, `finished`), rest are kwargs. No f-string log messages. UUIDs → `str(...)`.

**Dry-run / idempotency** — backfills default to a no-write dry run; `--apply` is opt-in (`apply: bool = False`). Split logic into `dry_run()` (read + log `would_*`) and `apply_changes()` (mutate + commit). Compare before writing so re-runs are idempotent:
```python
if project.status != ProjectStatus.ACTIVE:
    project.status = ProjectStatus.ACTIVE
    updated += 1
```
Log progress every N rows: `if i % 100 == 0: logger.info("apply.progress", processed=i, total=len(projects))`.

## Reuse the domain — three escalating levels

Pick the lightest that works. Drive writes through use-cases/repos, not ad-hoc SQL.

1. **Repos directly** — instantiate `SQL*` repos with `session=session`:
   ```python
   tenant_repository = SQLTenantRepository(session=session)
   tenants = await tenant_repository.find_all(exclude_ids=exclude_ids)
   ```
2. **A use-case** for the actual mutation (preferred over hand-written updates):
   ```python
   await ProjectArchiver(project_id=project.uuid, project_repository=project_repo).execute()
   ```
3. **A bus** when a use-case/query handler needs one:
   - Need only one query → hand-build a `MemoryQueryBus` and subscribe just what you use:
     ```python
     query_bus = MemoryQueryBus()
     query_bus.subscribe(GetProjectByIdQuery, GetProjectByIdHandler(project_repository=project_repo))
     project = await query_bus.ask(query=GetProjectByIdQuery(project_id=project_id))
     ```
   - Need the full wired domain (commands enqueue to background jobs, all modules wired) → use the builders:
     ```python
     from src.common.infrastructure.domain_builder import build_async_domain
     from src.common.infrastructure.bus_builder import build_async_bus
     domain = build_async_domain(session=session)
     bus = build_async_bus(session=session, domain=domain)
     await bus.command_bus.dispatch(ExportProjectsCommand(tenant_id=tenant_id), run_async=True)
     ```
     Note `build_async_bus`'s command bus enqueues to Redis-backed jobs — side effects (exports, notifications) become background work. Dispatch with `run_async=False` when you want a command to run inline.

## Invocation

```bash
make script ARG="backfill_project_status.py --apply --tenant-id <uuid>"
# expands to: docker compose ... python scripts/backfill_project_status.py --apply ...
```
Runs inside the API container (correct env + DB/Redis hostnames). Direct `python scripts/x.py` only works inside `make bash`. Frequently-run scripts may earn a dedicated `make` target.

## Reports

Long-running tasks write a CSV to a gitignored output dir (`scripts/reports/`). Accumulate counts in a `@dataclass` report, then `report.write_csv(mode)` returning a timestamped `Path` (`backfill_project_status_apply_<YYYYMMDD_HHMMSS>.csv`); log the path in the final `finished` event.

## Heavy fan-out tasks

For tasks that fan out over an external API or large dataset: discover with a `ThreadPoolExecutor` (sync SDKs in threads via `loop.run_in_executor`), then process each item in its OWN short-lived session with bounded batches + retry — not one giant transaction. Wrap each item in a `process_single_*_with_retry` helper and batch the `apply_changes` loop.

## See also
- `repositories.md` — `SQL*` repo construction, entity ↔ ORM builders.
- `dependency-injection.md` — how the request path builds the same contexts (`DomainContext`/`BusContext`) that scripts assemble by hand.
- `cqrs-buses.md` — `MemoryQueryBus.subscribe`/`ask`, query/handler wiring.
