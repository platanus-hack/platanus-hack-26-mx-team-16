# Authentication & Multi-tenant

JWT bearer auth + tenant isolation. Two independent identities: the **user** (from `Authorization: Bearer`) and the **active tenant** (from the `X-Tenant` header). Both must resolve for tenant-scoped reads/writes.

## JWT strategy

- HS256, single issuer. Settings live in `src/common/settings.py`: `JWT_SECRET_KEY` (default `secrets.token_urlsafe(32)`), `JWT_ALGORITHM="HS256"`, `JWT_ISSUER`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_MINUTES`.
- **Access token**: stateless — only signature + expiry + scope checked per request. Never blacklisted.
- **Refresh token**: rotating. Each `refresh_token()` call blacklists the prior refresh and issues a fresh access+refresh pair.
- **Namespace** (`ns` claim) separates token domains so revocation keys don't collide. Use one namespace per authentication audience (e.g. `"USER"`); add more (`"SERVICE"`, `"DEVICE"`) only when you have a genuinely distinct identity type — each gets its own session builder.

Claims (`JwtTokenClaims` in `src/common/domain/services/token_builder.py`): `iss, sub, iat, exp, jti, ns, scope`. **No `tenant_id` in the token** — the active tenant is resolved separately (see below).

## TokenService

Interface `src/common/domain/services/token_service.py`, impl `JwtTokenService` in `src/common/infrastructure/services/jwt_token_service.py` (a `@dataclass` wrapping `TokenStore` + `TokenBuilder`):

```python
class TokenService(ABC):
    async def generate_token(self, sub: str, namespace: str = "JWT") -> JwtSession: ...
    async def refresh_token(self, refresh_token: str) -> tuple[JwtTokenClaims, JwtSession]: ...
    async def get_claims(self, token: str, scope: JwtTokenScope) -> JwtTokenClaims | None: ...
    async def expire_refresh_token(self, refresh_token: str): ...  # logout
```

`JwtSession` = `{access_token, refresh_token}`. `JwtTokenScope` = `ACCESS | REFRESH`. Verification + decode is `get_claims` (delegates to `TokenBuilder.verify_token`) — the public API is `get_claims` / `generate_token` / `refresh_token` / `expire_refresh_token`, nothing else.

## Redis token store

`RedisTokenStore(TokenStore)` in `src/common/infrastructure/services/redis_token_store.py`. Key scheme, all TTL-scoped:

- `{ns}_RT:{sub}` → the active refresh `jti` for that sub (one live refresh per sub).
- `{ns}_BL:{jti}` → blacklist marker. `is_blacklisted` checks `EXISTS {ns}_BL:{jti}`.

`blacklist_token_sub(sub, ttl, ns)` looks up `{ns}_RT:{sub}` and blacklists that jti — used on login (`generate_token`), rotation (`refresh_token`), and logout (`expire_refresh_token`). TTL = remaining token lifetime via `_get_exp_remaining_seconds(exp)`, so entries self-expire.

## Authenticated user dependency

`src/common/infrastructure/dependencies/session.py`. Uses FastAPI's `HTTPBearer` security scheme — not manual header parsing.

```python
security = HTTPBearer()

async def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> User:
    claim = await domain_context.token_service.get_claims(
        token=credentials.credentials, scope=JwtTokenScope.ACCESS,
    )
    if not claim or not claim.sub:
        raise InvalidOrExpiredTokenError
    result = await bus_context.query_bus.ask(GetUserByIdQuery(user_id=UUID(claim.sub)))
    if not isinstance(result, User):
        raise InvalidOrExpiredTokenError
    return result

AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]
```

- Injects `DomainContextDep` + `BusContextDep` directly (there is no combined `AppContextDep`).
- A new authentication audience (e.g. a service token or device) gets its own parallel dep modeled on this one, resolving its own entity through a query — keep `get_authenticated_user` for human users.

## How `current_tenant_id` is resolved

`current_tenant_id` is a **persisted nullable column** on `UserORM` (`src/common/database/models/user.py`, FK → `tenants.uuid`), hydrated into the `User` entity by `build_user` (`src/common/infrastructure/builders/user.py`). It is the user's *last-selected* tenant, NOT carried in the JWT, and NOT the authority for scoping.

- Switch active tenant: a `PUT` endpoint dispatches `SetUserCurrentTenantCommand`, which runs `UPDATE users SET current_tenant_id=... WHERE uuid=...` in `SQLUserRepository`.
- Fallback: `SQLTenantRepository.find_by_user` returns the row's `current_tenant_id` tenant, else the user's first tenant.

**For tenant-scoped endpoints the active tenant comes from the `X-Tenant` header, not `current_tenant_id`** (see next section).

## Tenant resolution via `X-Tenant` header

`src/common/infrastructure/dependencies/tenant.py` — chained deps off the `X-Tenant` slug header:

```python
RequiredTenantDep      # get_required_tenant: slug -> Tenant or raise TenantRequiredError
RequiredTenantUserDep  # get_required_tenant_user: (AuthenticatedUserDep, RequiredTenantDep)
                       #   -> TenantUser or raise TenantUserRequiredError
```

`get_required_tenant_user` is the workhorse: it confirms the authenticated user actually belongs to the requested tenant (`tenant_user_repository.find_by_args(user_id, tenant_id)`). The `TenantUser` it returns — bound as `current_tenant_user` — carries `tenant`, `tenant_role`, and permissions.

## Multi-tenant data model

- Tenant-owned ORMs use `UUIDTenantTimestampMixin` (`src/common/database/mixins/tenants.py`) → non-null `tenant_id: Mapped[UUID]` FK to `tenants.uuid`. Optional variant: `OptionalTenantTimestampMixin` for rows that may or may not belong to a tenant.
- A `User` belongs to many tenants through `TenantUserORM`.

```
TenantORM ──< TenantUserORM >── UserORM
       │                   └─ current_tenant_id (last selected)
       └──< [Entity]ORM (tenant-scoped feature rows)
```

## Tenant scoping rules

1. **`tenant_id` is NEVER read from the request body.** Source it from the validated `RequiredTenantUserDep` → `current_tenant_user.tenant.uuid`.
2. **List/filter queries set the tenant on the filters object server-side**, e.g. `params.tenant_ids = [current_tenant_user.tenant.uuid]`. Filters subclass `ListFilters`; if the filter type exposes a `tenant_ids` field, the endpoint overwrites it (never trust the client value).
3. **Repositories take `tenant_id` explicitly and `.where([Entity]ORM.tenant_id == tenant_id)`.** There is no implicit/global tenant filter; pass it on every query.
4. **Permission gate before tenant ops**: `check_tenant_permission(current_tenant_user, permissions=[...])` (`src/common/domain/permissions/checker.py`) raises `InsufficientPermissionsError`. No-ops when `PERMISSIONS_ENABLED` is false.

## Tenant-scoped endpoint shape

```python
async def list_projects(
    params: ProjectFilters = Depends(),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    app_context: AppContext = Depends(get_app_context),
):
    check_tenant_permission(current_tenant_user, permissions=[ProjectPermission.view])
    params.tenant_ids = [current_tenant_user.tenant.uuid]          # ← server-set, always
    page = await app_context.bus.query_bus.ask(FilterPaginatedProjectsQuery(filters=params))
    return ApiJSONResponse(content=page)
```

Endpoints needing the whole context use `Depends(get_app_context)` (there is no `AppContextDep` alias). For user-only endpoints (no tenant needed) inject `AuthenticatedUserDep` / `get_authenticated_user` alone.

## Public endpoints (no auth)

`/login`, `/refresh`, `/health`: omit the auth deps entirely. Use separate handlers — don't branch on a maybe-present token.

## Common mistakes

- **Trusting `tenant_id`/`tenantIds` from the request body** → privilege escalation. Always overwrite with `current_tenant_user.tenant.uuid`.
- **Using `current_user.current_tenant_id` for scoping** → it's only the last-selected hint; the authoritative active tenant is the `X-Tenant`-validated `RequiredTenantUserDep`.
- **Skipping `get_required_tenant_user`** → no check that the user belongs to the tenant. `get_authenticated_user` alone validates identity, not tenant membership.
- **Forgetting `.where(tenant_id == ...)` in a new repo method** → cross-tenant data leak; scoping is explicit, never automatic.
- **Inventing token methods** (`decode`, `issue_access`, `revoke`) → the API is `get_claims` / `generate_token` / `refresh_token` / `expire_refresh_token`.

## See also

- `dependency-injection.md` — `DomainContextDep`, `BusContextDep`, `AppContext`, `get_app_context`.
- `cqrs-buses.md` — `query_bus.ask` / `command_bus.dispatch` used by the auth deps.
- `repositories.md` — explicit `tenant_id` filtering in SQL repos.
- `errors.md` — `InvalidOrExpiredTokenError`, `TenantRequiredError`, `InsufficientPermissionsError`.
