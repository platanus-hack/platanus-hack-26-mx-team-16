---
feature: data-model
type: plan
status: partial
coverage: 82
audited: 2026-06-16
---

# AppContext: Dependency Injection para Dominio y Buses en Doxiq

Este documento describe el patron de inyeccion de dependencias usado para conectar la capa de dominio (repositorios y servicios) con los buses CQRS (Command/Query/Event) en los endpoints de FastAPI.

## Arquitectura General

```
Request HTTP
    |
    v
+--------------------------------------------------+
|  FastAPI Depends() chain                         |
|                                                  |
|  AsyncSession --> DomainContext --> BusContext     |
|                        |               |         |
|                        +-------+-------+         |
|                                v                 |
|                          AppContext               |
+--------------------------------------------------+
    |
    v
Endpoint recibe AppContext con acceso a todo
```

Cada request HTTP crea su propia cadena de dependencias (request-scoped), garantizando aislamiento entre requests y atomicidad transaccional.

---

## 1. Contratos del Dominio (ABC)

### Command Bus

```python
# src/common/domain/buses/commands.py

class Command(ABC):
    @property
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self: ...


@dataclass
class CommandHandler[TCommand: Command](ABC):
    @abstractmethod
    async def execute(self, command: TCommand): ...


@dataclass
class CommandBus(ABC):
    @abstractmethod
    def subscribe(self, command: type[Command], handler: CommandHandler[Command]): ...

    @abstractmethod
    async def dispatch(
        self,
        command: Command,
        run_async: bool = False,
    ): ...
```

### Command Enqueuer (Async)

```python
# src/common/domain/buses/async_commands.py

@dataclass
class CommandEnqueuer(ABC):
    @abstractmethod
    async def enqueue(self, command: Command): ...
```

### Query Bus

```python
# src/common/domain/buses/queries.py

class Query:
    pass


@dataclass
class QueryHandler[TQuery: Query, TResult](ABC):
    @abstractmethod
    async def execute(self, query: TQuery) -> TResult | None: ...


@dataclass
class QueryBus(ABC):
    @abstractmethod
    def subscribe(self, query: type[Query], handler: QueryHandler[Query, object]) -> None: ...

    @abstractmethod
    async def ask(self, query: Query) -> object | None: ...
```

### Event Bus

```python
# src/common/domain/buses/events.py

@dataclass
class DomainEvent(ABC):
    id: UUID
    timestamp: datetime
    args: tuple[Any, ...] | None = None


class DomainEventHandler(ABC):
    @abstractmethod
    def execute(self, event: DomainEvent): ...


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event: type[DomainEvent], handler: DomainEventHandler): ...

    @abstractmethod
    def publish_batch(self, event: list[DomainEvent]): ...

    @abstractmethod
    def publish(self, events: list[DomainEvent]): ...
```

---

## 2. Los tres contextos

### DomainContext

Dataclass que agrupa **repositorios y servicios** del dominio que participan en el bus wiring. Se construye una vez por request con la misma `AsyncSession`.

```python
# src/common/domain/contexts/domain.py

@dataclass
class DomainContext:
    # -> USERS
    user_repository: UserRepository
    email_repository: EmailAddressRepository
    phone_repository: PhoneNumberRepository
    tenant_user_repository: TenantUserRepository

    # -> TENANTS
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository

    # -> COMMON
    token_service: TokenService

    # -> ASSETS
    storage_service: StorageService
```

> **Nota:** Al agregar un nuevo modulo, registra sus repositorios aqui en `DomainContext` (y su kwarg en `build_async_domain`) para que esten disponibles via el bus system.

### BusContext

Dataclass que agrupa los tres buses del sistema CQRS.

```python
# src/common/domain/contexts/bus.py

@dataclass
class BusContext:
    command_bus: CommandBus
    query_bus: QueryBus
    event_bus: EventBus
```

### AppContext

Composicion final que une dominio y buses en un solo objeto inyectable.

```python
# src/common/infrastructure/context_builder.py

@dataclass
class AppContext:
    domain: DomainContext
    bus: BusContext
    scheduler: None = None
```

`AppContextBuilder` permite intercambiar entre contextos reales y mocks segun el entorno:

```python
# src/common/infrastructure/context_builder.py

class AppContextBuilder:
    @classmethod
    def from_env(
        cls,
        environment: Environment | None = None,
        domain: DomainContext | None = None,
        bus: BusContext | None = None,
    ) -> AppContext:
        environment = environment or settings.ENVIRONMENT
        if environment.is_production or environment.is_development:
            return AppContext(domain=domain, bus=bus)
        if environment.is_testing:
            return AppContext(
                domain=MockDomainSingleton.instance,
                bus=MockBusSingleton.instance,
            )
```

---

## 3. Builders: Construccion de los Contextos

### Domain Builder

Instancia **todas las implementaciones concretas** (SQL repositories, servicios externos) pasandoles la misma `AsyncSession`:

```python
# src/common/infrastructure/domain_builder.py

def build_async_domain(session: AsyncSession) -> DomainContext:
    return DomainContext(
        # -> USERS
        user_repository=SQLUserRepository(session=session),
        email_repository=SQLEmailAddressRepository(session=session),
        phone_repository=SQLPhoneNumberRepository(session=session),
        tenant_user_repository=SQLTenantUserRepository(session=session),
        # -> TENANTS
        tenant_repository=SQLTenantRepository(session=session),
        tenant_role_repository=SQLTenantRoleRepository(session=session),
        # -> COMMON
        token_service=JwtTokenService(
            token_builder=JwtTokenBuilder(),
            token_store=RedisTokenStore(redis_client=Redis.from_url(settings.redis_url)),
        ),
        # -> ASSETS
        storage_service=S3StorageService(),
    )
```

### Bus Builder

Crea los buses en memoria y ejecuta las funciones de **wiring** de cada modulo para registrar handlers:

```python
# src/common/infrastructure/bus_builder.py

def build_async_bus(
    session: AsyncSession,
    domain: DomainContext | None = None,
    arq_pool: ArqRedis | None = None,
) -> BusContext:
    domain = domain or build_async_domain(session=session)
    bus = BusContext(
        command_bus=MemoryCommandBus(
            enqueuer=ArqCommandEnqueuer(
                redis_settings=RedisSettings.from_dsn(settings.redis_url),
                pool=arq_pool,
            ),
        ),
        query_bus=MemoryQueryBus(),
        event_bus=MemoryEventBus(),
    )

    # Cada modulo registra sus handlers
    auth_wiring(domain, bus)
    messaging_wiring(domain, bus)
    tenants_wiring(domain, bus)
    users_wiring(domain, bus)
    return bus
```

---

## 4. Bus Wiring: Registro de Handlers

Cada modulo tiene un archivo `infrastructure/bus_wiring.py` que conecta Commands/Queries con sus Handlers, inyectando los repositorios necesarios desde el `DomainContext`.

### Modulos con wiring activo

| Modulo | Archivo | Queries | Commands |
|--------|---------|---------|----------|
| auth | `src/auth/infrastructure/bus_wiring.py` | - | - |
| messaging | `src/messaging/infrastructure/bus_wiring.py` | - | Si |
| tenants | `src/tenants/infrastructure/bus_wiring.py` | 5 | 3 |
| users | `src/users/infrastructure/bus_wiring.py` | 7 | 7 |

### Ejemplo: users_wiring

```python
# src/users/infrastructure/bus_wiring.py

def users_wiring(
    domain: DomainContext,
    bus: BusContext,
) -> None:
    # ->  Q U E R I E S
    bus.query_bus.subscribe(
        query=GetUserByIdQuery,
        handler=GetUserByIdHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetUserByEmailQuery,
        handler=GetUserByEmailHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetOrCreateUserQuery,
        handler=GetOrCreateUserHandler(
            user_repository=domain.user_repository,
            email_repository=domain.email_repository,
            query_bus=bus.query_bus,
        ),
    )
    # ... mas queries y commands

    # ->  C O M M A N D S
    bus.command_bus.subscribe(
        command=PersistUserCommand,
        handler=PersistUserHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=SetUserCurrentTenantCommand,
        handler=SetUserCurrentTenantHandler(
            user_repository=domain.user_repository,
            query_bus=bus.query_bus,
        ),
    )
    # ... mas commands
```

### Ejemplo: tenants_wiring

```python
# src/tenants/infrastructure/bus_wiring.py

def tenants_wiring(
    domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=PersistTenantCommand,
        handler=PersistTenantHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=BootstrapTenantRolesCommand,
        handler=BootstrapTenantRolesHandler(
            role_repository=domain.tenant_role_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=AssignTenantRoleInBatchCommand,
        handler=AssignTenantRolenBatchHandler(
            role_repository=domain.tenant_role_repository,
            tenant_user_repository=domain.tenant_user_repository,
            tenant_repository=domain.tenant_repository,
        ),
    )

    #  Q U E R I E S
    bus.query_bus.subscribe(
        query=GetUserTenantsQuery,
        handler=GetUserTenantsHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetTenantByIdQuery,
        handler=GetTenantByIdHandler(
            repository=domain.tenant_repository,
        ),
    )
    # ... mas queries
```

**Patron clave:** cada Handler recibe solo las dependencias que necesita (repositorios especificos, otros buses), no el DomainContext completo.

---

## 5. Implementaciones In-Memory de los Buses

### MemoryCommandBus

```python
# src/common/infrastructure/buses/memory_command_bus.py

@dataclass
class MemoryCommandBus(CommandBus):
    enqueuer: CommandEnqueuer

    def __post_init__(self):
        self._commands: dict[type[Command], CommandHandler[Command]] = {}

    def subscribe(self, command: type[Command], handler: CommandHandler[Command]):
        if command in self._commands:
            raise CommandAlreadyExistError
        self._commands[command] = handler

    async def dispatch(
        self,
        command: Command,
        run_async: bool = False,
    ):
        if command.__class__ not in self._commands:
            raise CommandHandlerDoesNotExistError(command.__class__)

        if run_async:
            # Encola en ARQ (Redis) para ejecucion en background worker
            await self.enqueuer.enqueue(command)
            return
        await self._commands[command.__class__].execute(command)
```

### MemoryQueryBus

```python
# src/common/infrastructure/buses/memory_query_bus.py

class MemoryQueryBus(QueryBus):
    def __init__(self) -> None:
        self._queries: dict[type[Query], QueryHandler[Query, object]] = {}

    def subscribe(self, query: type[Query], handler: QueryHandler[Query, object]) -> None:
        if query in self._queries:
            raise QueryAlreadyExistError
        self._queries[query] = handler

    async def ask(self, query: Query) -> object | None:
        if query.__class__ not in self._queries:
            raise QueryHandlerDoesNotExistError(query.__class__)
        return await self._queries[query.__class__].execute(query)
```

---

## 6. FastAPI Dependencies: La Cadena de Inyeccion

El archivo `src/common/infrastructure/dependencies/common.py` define la cadena de `Depends()`:

```python
# 1. Session de base de datos (request-scoped)
async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession]:
    database_config: DatabaseConfig = request.app.state.database_config
    async with database_config.session_maker() as session:
        request.state.db_session = session
        try:
            yield session
        finally:
            await session.close()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_database_session)]


# 2. Contexto de dominio (repositorios + servicios)
async def get_domain_context(session: AsyncSessionDep) -> DomainContext:
    return build_async_domain(session=session)

DomainContextDep = Annotated[DomainContext, Depends(get_domain_context)]


# 2.5. Pool de ARQ para tareas async (inicializado en app startup)
def get_arq_pool(request: Request) -> ArqRedis:
    return cast("ArqRedis", request.app.state.arq_pool)

ArqPoolDep = Annotated[ArqRedis, Depends(get_arq_pool)]


# 3. Contexto de buses (command + query + event)
async def get_bus_context(
    session: AsyncSessionDep,
    domain: DomainContextDep,
    arq_pool: ArqPoolDep,
) -> BusContext:
    return build_async_bus(session=session, domain=domain, arq_pool=arq_pool)

BusContextDep = Annotated[BusContext, Depends(get_bus_context)]


# 4. App context (dominio + buses combinados)
async def get_app_context(
    domain: DomainContextDep,
    bus: BusContextDep,
) -> AppContext:
    return AppContext(domain=domain, bus=bus)
```

**Orden de resolucion por request:**
1. `get_database_session` -> crea `AsyncSession`
2. `get_domain_context` -> construye repositorios con esa session
3. `get_bus_context` -> crea buses y registra handlers con los repositorios
4. `get_app_context` -> combina domain + bus

FastAPI resuelve automaticamente las dependencias compartidas (no duplica la session).

---

## 7. Autenticacion como Dependencia

```python
# src/common/infrastructure/dependencies/session.py

async def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> User:
    access_token = credentials.credentials
    token_service = domain_context.token_service

    claim = await token_service.get_claims(token=access_token, scope=JwtTokenScope.ACCESS)
    if not claim or not claim.sub:
        raise InvalidOrExpiredTokenError

    result = await bus_context.query_bus.ask(
        query=GetUserByIdQuery(user_id=UUID(claim.sub)),
    )

    if not isinstance(result, User):
        raise InvalidOrExpiredTokenError

    return result

AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]


# Variante opcional (no lanza error si no hay token)
async def get_optional_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> User | None:
    if not credentials:
        return None
    # ... misma logica, retorna None en vez de raise
    ...

OptionalAuthenticatedUserDep = Annotated[User | None, Depends(get_optional_authenticated_user)]
```

---

## 8. App Lifespan: Inicializacion y Shutdown

```python
# config/lifespan.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --------- STARTUP ----------
    database_config = get_database_config()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True, encoding="utf-8")
    arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    app.state.database_config = database_config
    app.state.redis_client = redis_client
    app.state.arq_pool = arq_pool

    yield  # app empieza a atender requests

    # --------- SHUTDOWN ----------
    await arq_pool.aclose()
    await database_config.dispose()
    await redis_client.aclose()
```

Servicios inicializados en startup y disponibles via `request.app.state`:
- **DatabaseConfig** - pool de conexiones PostgreSQL async
- **Redis** - cliente para cache y token store
- **ARQ pool** - pool de conexiones Redis para job queue

---

## 9. Uso en Endpoints

### Endpoint publico (sin autenticacion)

```python
# src/auth/presentation/endpoints/google_login.py

async def google_login(
    payload: GoogleLoginRequest,
    app_context: AppContext = Depends(get_app_context),
):
    google_tokens = await get_google_tokens(payload.code)
    google_user = await verity_google_id_token(google_tokens.id_token)

    user_session = await GoogleSessionBuilder(
        google_tokens=google_tokens,
        google_user=google_user,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(user_session).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
```

### Endpoint autenticado

```python
async def get_profile(
    app_context: AppContext = Depends(get_app_context),
    current_user: User = Depends(get_authenticated_user),
):
    profile = await app_context.bus.query_bus.ask(
        query=GetTenantUserByIdQuery(user_id=current_user.id),
    )
    return profile
```

### Comando asincrono (background worker via ARQ)

```python
await app_context.bus.command_bus.dispatch(
    command=SendEmailCommand(to=email, template="welcome"),
    run_async=True,  # se encola en ARQ/Redis
)
```

---

## 10. Repositorios y Servicios del Sistema

### En DomainContext (participan en bus wiring)

| Modulo | Repositorio ABC | Implementacion SQL |
|--------|----------------|-------------------|
| users | `UserRepository` | `SQLUserRepository` |
| users | `EmailAddressRepository` | `SQLEmailAddressRepository` |
| users | `PhoneNumberRepository` | `SQLPhoneNumberRepository` |
| tenants | `TenantRepository` | `SQLTenantRepository` |
| tenants | `TenantRoleRepository` | `SQLTenantRoleRepository` |
| tenants | `TenantUserRepository` | `SQLTenantUserRepository` |

| Modulo | Servicio ABC | Implementacion |
|--------|-------------|----------------|
| common | `TokenService` | `JwtTokenService` (usa `JwtTokenBuilder` + `RedisTokenStore`) |
| assets | `StorageService` | `S3StorageService` |

### Fuera de DomainContext (instanciados directamente en use cases/builders)

| Modulo | Servicio | Descripcion |
|--------|---------|-------------|
| messaging | `EmailService` | `SmtpEmailService` |
| common | `CodeGenerator` | `CallbackCodeGenerator` |
| auth | `LegacyTokenBuilder` | `LegacyJWTTokenBuilder` |

---

## 11. Como Agregar un Nuevo Modulo al Sistema de Buses

### Paso 1: Agregar repositorios al DomainContext

```python
# src/common/domain/contexts/domain.py
@dataclass
class DomainContext:
    # ... existentes ...

    # -> NUEVO MODULO
    nuevo_repository: NuevoRepository
```

### Paso 2: Agregar implementacion al Domain Builder

```python
# src/common/infrastructure/domain_builder.py
def build_async_domain(session: AsyncSession) -> DomainContext:
    return DomainContext(
        # ... existentes ...
        nuevo_repository=SQLNuevoRepository(session=session),
    )
```

### Paso 3: Crear bus_wiring en el modulo

```python
# src/nuevo_modulo/infrastructure/bus_wiring.py

def nuevo_modulo_wiring(domain: DomainContext, bus: BusContext) -> None:
    bus.query_bus.subscribe(
        query=GetNuevoByIdQuery,
        handler=GetNuevoByIdHandler(
            repository=domain.nuevo_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=PersistNuevoCommand,
        handler=PersistNuevoHandler(
            repository=domain.nuevo_repository,
        ),
    )
```

### Paso 4: Registrar wiring en el Bus Builder

```python
# src/common/infrastructure/bus_builder.py
from src.nuevo_modulo.infrastructure.bus_wiring import nuevo_modulo_wiring

def build_async_bus(...) -> BusContext:
    # ... existente ...
    nuevo_modulo_wiring(domain, bus)
    return bus
```

---

## Diagrama de Flujo Completo

```
HTTP Request
    |
    v
+-- FastAPI Depends() -----------------------------------------+
|                                                              |
|  AsyncSession (from session_maker)                           |
|       |                                                      |
|       +---> build_async_domain(session)                      |
|       |       |                                              |
|       |       +-- SQLUserRepository(session)                 |
|       |       +-- SQLEmailAddressRepository(session)         |
|       |       +-- SQLPhoneNumberRepository(session)          |
|       |       +-- SQLTenantUserRepository(session)           |
|       |       +-- SQLTenantRepository(session)               |
|       |       +-- SQLTenantRoleRepository(session)           |
|       |       +-- JwtTokenService(builder, redis_store)      |
|       |       +-- S3StorageService()                         |
|       |       |                                              |
|       |       v                                              |
|       |   DomainContext                                      |
|       |       |                                              |
|       +---> build_async_bus(session, domain, arq_pool)       |
|               |                                              |
|               +-- MemoryCommandBus(ArqCommandEnqueuer)       |
|               +-- MemoryQueryBus()                           |
|               +-- MemoryEventBus()                           |
|               |                                              |
|               +-- auth_wiring(domain, bus)                   |
|               +-- messaging_wiring(domain, bus)              |
|               +-- tenants_wiring(domain, bus)                |
|               +-- users_wiring(domain, bus)                  |
|               |                                              |
|               v                                              |
|           BusContext                                          |
|               |                                              |
|               v                                              |
|           AppContext(domain, bus)                             |
|                                                              |
+--------------------------------------------------------------+
    |
    v
Endpoint: app_context.bus.command_bus.dispatch(...)
          app_context.bus.query_bus.ask(...)
          app_context.domain.token_service.generate_token(...)
```
