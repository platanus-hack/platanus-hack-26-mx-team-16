# Cursor Pagination & Filters

Cursor-based, stable under concurrent inserts, index-friendly. No offset
anywhere. Order is always `(created_at DESC, uuid DESC)`; the cursor is the
`(timestamp, uuid)` of the last returned row.

## `Page[T]` + `Pagination`

`src/common/domain/entities/common/pagination.py` (Pydantic, not dataclass):

```python
class Page[T](BaseModel):
    next_cursor: str | None = None
    items: list[T] | None = None
    limit: int = settings.PAGINATION_PAGE_SIZE   # 25 (src/common/settings.py)

    @classmethod
    def empty(cls, page_size=settings.PAGINATION_PAGE_SIZE, items=None) -> "Page[T]": ...

    def apply_presenter(self, presenter_class: type[Presenter[T]]) -> None:
        self.items = [presenter_class(item).to_dict for item in self.items]


class Pagination(BaseModel):
    next_cursor: str | None = None
    limit: int | None = None

    @classmethod
    def from_page(cls, page: "Page[Any]") -> Self:
        return cls(next_cursor=page.next_cursor, limit=page.limit)
```

There is **no `has_next`** field — "more pages?" means `next_cursor is not None`.
`PageIndex` (same file) is a helper that base64-encodes `(value, uuid)`; the cursor
token carried in filters is produced by `encode_cursor` below.

## Filters: `ListFilters` subclass (Pydantic, NOT `@dataclass`)

Base in `src/common/domain/entities/common/collection.py`:

```python
class ListFilters(CamelCaseRequest):   # CamelCaseRequest = Pydantic w/ camelCase aliases
    cursor: str | None = Field(default=None)
    limit: int = Field(default=settings.PAGINATION_PAGE_SIZE)

    @staticmethod
    def parse_enum_values(raw_values: str | None, enum_class: type[T]) -> list[T]: ...
```

One subclass per entity in `src/common/domain/filters/[area]/[entity].py`.
Example `src/common/domain/filters/projects/project.py`:

```python
class ProjectFilters(ListFilters):
    search: str | None = Field(default=None)
    statuses: str | None = Field(default=None)            # comma-separated, e.g. "ACTIVE,ARCHIVED"
    tenant_ids: list[UUID] | None = Field(default=None, alias="tenantIds")
    exclude_ids: list[UUID] | None = Field(default=None, alias="excludeIds")

    def model_post_init(self, context: Any, /) -> None:    # never leave list filters None
        self.tenant_ids = self.tenant_ids or []
        self.exclude_ids = self.exclude_ids or []

    @property
    def enum_statuses(self) -> list[ProjectStatus]:
        return self.parse_enum_values(self.statuses, ProjectStatus)
```

Conventions:
- Multi-value filters arrive as **comma-separated strings**, decoded lazily via
  `enum_*`/`parsed_*` properties (`parse_enum_values` / split on `,`). Do not type
  them as `list[Enum]` in the field.
- camelCase query params map via `alias=`. Filters are injected as
  `Depends()` — the endpoint receives the parsed `*Filters` directly.
- `limit` already defaults to 25 from `ListFilters`; cap it per-endpoint only if you
  need to. The `limit + 1` over-fetch happens in the repo, not the filter.

## Cursor encode/decode (Fernet-encrypted)

`src/common/application/helpers/pagination.py` — tokens are **encrypted**, not plain
base64, and accept `datetime | date`:

```python
SEPARATOR = "|"
fernet = get_fernet()

def encode_cursor(input_datetime: datetime | date, uuid: UUID) -> str:
    token = fernet.encrypt(_serialize(input_datetime, uuid))
    return base64.urlsafe_b64encode(token).decode().rstrip("=")

def decode_cursor(cursor: str) -> tuple[datetime | date, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = fernet.decrypt(base64.urlsafe_b64decode(padded))
        return _deserialize(raw)
    except Exception:
        raise InvalidPaginationCursorError   # -> 400 common.InvalidPaginationCursor
```

`_serialize` uses `isoformat(timespec="microseconds")` for datetimes; the composite
`(timestamp, uuid)` breaks ties when rows share a timestamp.

## Repo `filter_paginated`

Abstract method on the repository interface returns `Page[T]`. Single-table impl —
`src/projects/infrastructure/repositories/sql_project.py`:

```python
async def filter_paginated(self, filters: ProjectFilters) -> Page[Project]:
    stmt = await self._filter(filters, paginated=True)
    orm_instances = list((await self.session.execute(stmt)).scalars())

    next_cursor = None
    if len(orm_instances) == filters.limit + 1:      # over-fetched -> there is more
        last = orm_instances.pop()
        next_cursor = encode_cursor(last.created_at, last.uuid)

    return Page(
        next_cursor=next_cursor,
        items=[build_project(o) for o in orm_instances],
        limit=filters.limit,
    )

async def _filter(self, filters, paginated=False) -> Select:
    q = self._build_base_query().order_by(
        ProjectORM.created_at.desc(), ProjectORM.uuid.desc()
    )
    if paginated:
        q = q.limit(filters.limit + 1)
    if filters.tenant_ids:
        q = q.where(ProjectORM.tenant_id.in_(filters.tenant_ids))
    if filters.enum_statuses:
        q = q.where(ProjectORM.status.in_(filters.enum_statuses))
    if filters.search:
        pat = f"%{filters.search}%"
        q = q.where(or_(ProjectORM.name.ilike(pat), ...))
    if filters.cursor:
        ts, last_uuid = decode_cursor(filters.cursor)
        q = q.where(tuple_(ProjectORM.created_at, ProjectORM.uuid) <= (ts, last_uuid))
    return q
```

Notes:
- Pair `filter` (no pagination, returns `list[T]`) with `filter_paginated` — same
  `_filter` builder, `paginated` toggles the `limit + 1`. The non-paginated variant
  feeds exporters and bulk jobs.
- For multi-source lists (union of two tables), `union_all` the id/date subqueries
  into a `combined` select, paginate on `tuple_(combined.c.<date>, combined.c.uuid)`,
  then hydrate entities by id.

## Endpoint

Filters via `Depends()`, set `tenant_ids` from the authenticated tenant user, dispatch
a `FilterPaginated*Query`, apply a presenter, return `ApiJSONResponse(content=page)`.
`src/projects/presentation/endpoints/projects.py`:

```python
async def get_projects(
    params: ProjectFilters = Depends(),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    app_context: AppContext = Depends(get_app_context),
):
    check_tenant_permission(current_tenant_user, permissions=[ProjectPermission.view])
    params.tenant_ids = [current_tenant_user.tenant.uuid]      # enforce tenant scope here

    page: Page = await app_context.bus.query_bus.ask(
        query=FilterPaginatedProjectsQuery(filters=params),
    )
    page.apply_presenter(ProjectPresenter)
    return ApiJSONResponse(content=page, status_code=status.HTTP_200_OK)
```

`apply_presenter` mutates `page.items` in place to dicts. Don't rebuild a new `Page`.

## Envelope auto-detection

`src/common/infrastructure/responses/api_json.py` — `ApiJSONResponse.render` checks
`isinstance(content, Page)` and wraps via `ApiResponse` + `Pagination.from_page`:

```python
if self.is_paginated(content):                 # isinstance(content, Page)
    wrapped = ApiResponse(
        data=content.items,
        pagination=Pagination.from_page(content),
        timestamp=datetime.now(UTC),
    )
```

Non-`Page` content is wrapped with `pagination` excluded. `ApiResponse`
(`src/common/domain/entities/common/reponses.py`) is `{data, pagination, timestamp}`;
camelCase conversion is automatic. Wire response:

```json
{
  "data": [ /* presented items */ ],
  "pagination": { "nextCursor": "gAAAAA...", "limit": 25 },
  "timestamp": "2026-05-22T15:30:00Z"
}
```

## Common mistakes

- **Typing multi-value filters as `list[Enum]`** — they are comma-separated `str`,
  decoded by `enum_*` properties.
- **Sorting by `created_at` only** — unstable on ties; always add `, uuid DESC`.
- **Returning the over-fetched row** — `pop()` the extra row before building items.
- **Rebuilding `Page` in the endpoint** — call `page.apply_presenter(...)` instead.
- **Plain base64 cursor** — cursors are Fernet-encrypted (`get_fernet()`); a bad token
  raises `InvalidPaginationCursorError` (400), not a parse error.
- **Not setting `tenant_ids` in the endpoint** — cross-tenant leak; the repo trusts
  whatever the filter carries.

## See also

- `repositories.md` — repo interface/impl split, builders, `atomic_transaction`.
- `cqrs-buses.md` — `FilterPaginated*Query` + handler wiring.
- `endpoints.md` — `Depends()` DI, presenters, `ApiJSONResponse`.
