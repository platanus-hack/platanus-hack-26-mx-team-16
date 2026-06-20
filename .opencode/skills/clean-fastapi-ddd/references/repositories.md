# Models, entities, repositories

Worked end-to-end example below: `Project` (`src/projects` + `src/common`). The same shape applies to every aggregate; swap `[bounded_context]`/`[entity]`/`[Entity]`/`[area]` for your own names.

## Four artifacts per aggregate

| Layer | Path | Class / fn |
|---|---|---|
| Domain entity | `src/common/domain/entities/[area]/[entity].py` | `Project(BaseModelMixin, TimestampMixin)` |
| ORM model | `src/common/database/models/[area]/[entity].py` | `ProjectORM(Base, UUIDTimestampMixin)` |
| Builder (ORM→entity) | `src/common/infrastructure/builders/[area]/[entity].py` | `build_project(orm) -> entity` |
| Repo ABC + impl | `src/[bounded_context]/domain/repositories/[entity].py` + `src/[bounded_context]/infrastructure/repositories/sql_[entity].py` | `ProjectRepository` / `SQLProjectRepository` |

Entities + ORM + builders live under `src/common/` (shared). The repo ABC and `SQL*` impl live in the owning feature module.

## Domain entity (Pydantic)

```python
# src/common/domain/entities/projects/project.py
class Project(BaseModelMixin, TimestampMixin):
    tenant_id: UUID
    name: str
    status: ProjectStatus | None = Field(default=None)   # domain enums, not strings

    @property
    def is_active(self) -> bool:                          # behavior lives on the entity
        return self.status == ProjectStatus.ACTIVE

    @property
    def to_persist_dict(self) -> dict[str, object]:       # entity -> ORM column kwargs
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": str(self.status) if self.status else None,  # enums serialized to str
            ...
        }
```

Entity mixins (`src/common/domain/entities/mixins/common.py`):
- `BaseModelMixin` → `uuid` (default `uuid7()`), `model_config = ConfigDict(from_attributes=True, extra="ignore")`.
- `TimestampMixin` → `created_at`, `updated_at` (both `datetime | None`).
- `SoftDeleteMixin` → `is_deleted: bool = False`.
- Enum fields are domain enums (e.g. `ProjectStatus`), never raw strings.
- Every entity that maps to a table defines `to_persist_dict` — the repo never calls `model_dump()` directly.

## ORM model + mixins

```python
# src/common/database/models/projects/project.py
class ProjectORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "projects"
    name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(25), default=str(ProjectStatus.ACTIVE), index=True)
```

ORM enum columns are stored as `String(...)` with `default=str(SomeEnum.MEMBER)`, not native PG enums.

Mixins (`src/common/database/mixins/`):
- `common.py` → `Base`, `UUIDPrimaryKeyModelMixin` (`uuid` PK, uuid7), `TimeStampedModelMixin` (`created_at`/`updated_at` via `func.now()`), `UUIDTimestampMixin` (combines both), `SoftDeleteMixin` (`is_deleted: bool`).
- `tenants.py` → `UUIDTenantTimestampMixin` (`tenant_id` FK→`tenants.uuid`, **required**), `OptionalTenantTimestampMixin` (nullable `tenant_id`).

Soft delete is the boolean `is_deleted` (there is no separate `deleted_at` column). For a tenant-scoped table inherit `UUIDTenantTimestampMixin` (or `OptionalTenantTimestampMixin`); use plain `UUIDTimestampMixin` only for tables that aren't tenant-scoped.

Relationships are declared explicitly; set `lazy` per-relationship (e.g. `"select"`, `"noload"`) rather than relying on a global lazy-load guard.

## Builder (ORM → entity)

```python
# src/common/infrastructure/builders/projects/project.py
def build_project(orm_instance: ProjectORM) -> Project:
    return Project(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        name=orm_instance.name,
        status=ProjectStatus.from_value(orm_instance.status),   # str column -> enum
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
```

Pure function, one per entity. Reverses `to_persist_dict`: string columns become enums via `EnumClass.from_value(...)`.

## Repository ABC (domain)

```python
# src/projects/domain/repositories/project.py
class ProjectRepository(ABC):
    @abstractmethod
    async def find(self, instance_id: UUID) -> Project | None: ...
    @abstractmethod
    async def find_by_name(self, tenant_id: UUID, name: str) -> Project | None: ...
    @abstractmethod
    async def persist(self, instance: Project) -> Project: ...
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID,
                             limit: int = 100, offset: int = 0) -> list[Project]: ...
```

All methods `async`. Signatures take/return **domain entities** — never `*ORM`. `abstractmethod` bodies `raise NotImplementedError`.

## SQL implementation

```python
# src/projects/infrastructure/repositories/sql_project.py
@dataclass
class SQLProjectRepository(ProjectRepository):
    session: AsyncSession

    async def find(self, instance_id: UUID) -> Project | None:
        stmt = select(ProjectORM).where(ProjectORM.uuid == instance_id)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        if not orm or orm.is_deleted:
            return None
        return build_project(orm)

    async def persist(self, instance: Project) -> Project:
        async with atomic_transaction(self.session):
            orm = await self._find_by_id(instance.uuid)
            if orm:
                override_dict_properties(orm, instance.to_persist_dict)   # in-place update
            else:
                orm = ProjectORM(uuid=instance.uuid, **instance.to_persist_dict)
                self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)        # load server defaults / relations
            return build_project(orm)
```

Conventions:
- `@dataclass` with a single `session: AsyncSession` field. Repos are request-scoped.
- `persist` is upsert by `uuid`: private `_find_by_id` returns the ORM (only place ORM escapes a method), update via `override_dict_properties(orm, entity.to_persist_dict)`, else construct `*ORM(**to_persist_dict)` and `session.add`.
- Read methods return `build_[entity](orm)` or `None`; never expose `scalar_one_or_none()` ORM upward.
- `override_dict_properties` (`src/common/domain/helpers/models.py`) `setattr`s every key from the dict onto the ORM — it does not skip `None`.

## Transactions: `atomic_transaction`

```python
# src/common/infrastructure/helpers/database.py
@asynccontextmanager
async def atomic_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession]:
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

- Wraps every **write** path (`persist`, `delete`, soft-delete). Read methods do not open it.
- Commits on clean exit, rolls back on any exception. Never call `session.commit()` directly.
- `await session.flush()` inside the block to push INSERT/UPDATE before a read/`refresh`; the actual COMMIT happens when the context exits.
- Cross-repo atomicity: orchestrate the calls inside one `atomic_transaction(session)` at the use-case layer sharing the same session (see `use-cases.md`).

## Eager loading (N+1)

Use `selectinload` in `.options(...)` for any relation a presenter/builder will touch in a list query:

```python
base_query = (
    select(ProjectORM)
    .options(selectinload(ProjectORM.members))   # ProjectMember child rows
    .order_by(ProjectORM.created_at.desc(), ProjectORM.uuid.desc())
)
```

For a single upserted row, name the relations to load on `refresh`:

```python
await self.session.refresh(project_orm, ["updated_at", "members"])
```

## Soft delete

Mixin adds `is_deleted: bool` (no `deleted_at`). Pattern:

```python
# find: treat a soft-deleted row as missing
if not orm_instance or orm_instance.is_deleted:
    return None

# list / filter queries: exclude soft-deleted
base_query = base_query.where(ProjectORM.is_deleted.is_(False))

# delete: flip the flag inside atomic_transaction, do NOT session.delete()
project_orm.is_deleted = True
```

Hard delete (`session.delete(orm)`) is only for tables without `SoftDeleteMixin`.

## Multi-tenant filtering

List queries scope by tenant from the filter object, not a hardcoded column read:

```python
if filters.tenant_ids:
    base_query = base_query.where(ProjectORM.tenant_id.in_(filters.tenant_ids))
```

Forgetting this on a `UUIDTenantTimestampMixin` table is a cross-tenant leak. See `pagination.md` for cursor filters and `Page`.

## Wiring a new model+entity+repo

1. Entity: `src/common/domain/entities/[area]/[entity].py` — extend `BaseModelMixin, TimestampMixin`, add `to_persist_dict`.
2. ORM: `src/common/database/models/[area]/[entity].py` — `Base + UUIDTimestampMixin` (or `UUIDTenantTimestampMixin` if tenant-scoped, `+ SoftDeleteMixin` for soft delete). Import it in the models `__init__` so migrations see it.
3. Builder: `src/common/infrastructure/builders/[area]/[entity].py` — `build_[entity](orm) -> entity`, coercing string columns with `EnumClass.from_value(...)`.
4. ABC: `src/[bounded_context]/domain/repositories/[entity].py`.
5. Impl: `src/[bounded_context]/infrastructure/repositories/sql_[entity].py` — `@dataclass`, `session: AsyncSession`, writes in `atomic_transaction`.
6. Register the repo in the module's DI context (`dependency-injection.md`).
7. Migration: e.g. `make migrations ARG="add [entity] table"` then `make migrate`. Commit the migration with the model change.

## Common mistakes

- Returning a `*ORM` from a public repo method → leaks SQLAlchemy into the domain. Always `build_[entity](orm)`.
- Calling `entity.model_dump()` instead of `entity.to_persist_dict` → enum/relation columns serialize wrong.
- `session.delete()` on a `SoftDeleteMixin` table → should set `is_deleted = True`.
- Missing `is_deleted.is_(False)` on a list query → returns soft-deleted rows.
- Missing `selectinload`/`refresh` for a relation a builder reads → N+1 or `MissingGreenlet`/lazy-load error.
- `session.commit()` outside `atomic_transaction` → bypasses rollback handling.
- Forgetting the `tenant_id` filter on a tenant-scoped list query → cross-tenant leak.
