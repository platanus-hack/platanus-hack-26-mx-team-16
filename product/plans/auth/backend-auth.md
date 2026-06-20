---
feature: auth
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
---

# Autenticacion

Documentacion del sistema de autenticacion de Tripto WS. Cubre login, logout, refresh de tokens, blacklist, Google OAuth 2.0, reset de password y proteccion de rutas.

Esta documentacion incluye el codigo fuente completo de cada componente para permitir replicar la funcionalidad fielmente en otro proyecto.

## Stack de Autenticacion

| Componente | Tecnologia |
|---|---|
| Tokens | JWT (HS256) via `authlib` |
| Hashing de passwords | `bcrypt` |
| Blacklist de tokens | Redis con TTL automatico |
| IDs unicos de token | UUIDv7 (`uuid6.uuid7`) |
| OAuth externo | Google OAuth 2.0 |
| Transporte | Header `Authorization: Bearer <token>` |

### Dependencias (requirements)

```
authlib          # Creacion y verificacion de JWTs (authlib.jose)
bcrypt           # Hashing de passwords
redis[asyncio]   # Cliente Redis async (redis-py)
uuid6            # Generacion de UUIDv7
httpx            # Cliente HTTP async (para Google OAuth)
fastapi          # Framework web
pydantic         # Validacion de datos
pydantic-settings # Configuracion via variables de entorno
```

## Configuracion (Variables de Entorno)

```python
# src/common/settings.py
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    # Security Configuration
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30              # 30 minutos
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7    # 7 dias (10,080 minutos)
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "tripto"

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    GOOGLE_CERTS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"


settings = Settings()
```

## Endpoints

Todos los endpoints estan bajo el prefijo `/auth` y el tag `auth`.

| Metodo | Path | Descripcion | Auth requerida |
|---|---|---|---|
| `POST` | `/auth/login` | Login con email/password | No |
| `POST` | `/auth/google-login` | Login con Google OAuth 2.0 | No |
| `POST` | `/auth/refresh` | Renovar tokens con refresh token | No |
| `POST` | `/auth/logout` | Cerrar sesion (invalidar refresh token) | No |
| `POST` | `/auth/reset-password` | Solicitar reset de password | No |
| `GET` | `/auth/session` | Obtener perfil del usuario autenticado | Si (Bearer token) |

---

## 1. Fundamentos: Clases Base

Antes de los endpoints, estas son las clases base que usa todo el sistema.

### 1.1 BaseEnum

```python
# src/common/domain/enums/base_enum.py
from __future__ import annotations

from enum import Enum
from typing import Any, Self


class BaseEnum(Enum):
    @classmethod
    def get_members(cls) -> list[Self]:
        return [tag for tag in cls if type(tag.value) in [int, str, float]]

    @classmethod
    def choices(cls) -> list[tuple[Any, Any]]:
        return [(option.value, option.value) for option in cls if type(option.value) in [int, str, float]]

    @classmethod
    def values(cls) -> list[Any]:
        return [option.value for option in cls]

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def as_list(cls) -> list[str]:
        return [str(member.value) for member in cls]

    @classmethod
    def from_value(cls, value: str | int | None, default: Self | None = None) -> Self:
        if not value:
            return default
        for member in cls:
            if isinstance(member.value, str) and isinstance(value, str):
                if member.value.upper() == value.upper():
                    return member
            elif member.value == value:
                return member
        return default
```

### 1.2 CamelModel (Mixin para entidades)

```python
# src/common/domain/mixins/entities.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_snake


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        validate_assignment=True,
    )


class SnakeModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,
        validate_assignment=True,
    )
```

### 1.3 CamelCaseRequest (Base de requests)

```python
# src/common/domain/entities/common/requests.py
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_snake


class CamelCaseRequest(BaseModel):
    """
    Base model for API requests that automatically converts camelCase fields to snake_case.

    Example:
        Input JSON: {"firstName": "John", "lastName": "Doe"}
        Model fields: first_name="John", last_name="Doe"
    """

    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,
        validate_assignment=True,
        from_attributes=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def convert_camel_to_snake(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return cls._convert_keys_to_snake(data)
        return data

    @classmethod
    def _convert_keys_to_snake(cls, data: dict[str, Any]) -> dict[str, Any]:
        def camel_to_snake(name: str) -> str:
            result = []
            for i, char in enumerate(name):
                if char.isupper():
                    if i > 0 and (name[i - 1].islower() or (i < len(name) - 1 and name[i + 1].islower())):
                        result.append("_")
                    result.append(char.lower())
                else:
                    result.append(char)
            return "".join(result)

        converted: dict[str, Any] = {}
        for key, value in data.items():
            snake_key = camel_to_snake(key)
            if isinstance(value, dict):
                converted[snake_key] = cls._convert_keys_to_snake(value)
            elif isinstance(value, list):
                converted[snake_key] = [
                    cls._convert_keys_to_snake(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                converted[snake_key] = value
        return converted
```

### 1.4 DomainError (Base de excepciones)

```python
# src/common/domain/exceptions/_base.py
from typing import Any


class DomainError(Exception):
    code: str
    message: str
    status_code: int
    context: dict[str, Any] | None = None

    def __init__(self, code: str, message: str, status_code: int = 400, context: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context
        super().__init__(message)
```

### 1.5 TaskResult

```python
# src/common/domain/entities/common/task_result.py
from pydantic import BaseModel

from src.common.domain.enums.common import TaskStatus


class TaskResult(BaseModel):
    status: TaskStatus
    message: str | None = None

    @property
    def to_dict(self):
        data = {"status": str(self.status)}
        if self.message:
            data["message"] = self.message
        return data

    @classmethod
    def success(cls, message: str | None = None) -> "TaskResult":
        return cls(status=TaskStatus.SUCCESS, message=message)

    @classmethod
    def failure(cls, message: str | None = None) -> "TaskResult":
        return cls(status=TaskStatus.FAILURE, message=message)
```

### 1.6 UseCase (Interfaz base)

```python
# src/common/domain/interfaces/use_case.py
from abc import ABC, abstractmethod


class UseCase(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs) -> object | None:
        raise NotImplementedError
```

### 1.7 Presenter (Interfaz base)

```python
# src/common/domain/interfaces/presenter.py
from typing import Any, Protocol, TypeVar

TItem = TypeVar("TItem", covariant=True)


class Presenter(Protocol[TItem]):
    def __init__(self, instance: TItem): ...

    @property
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError
```

### 1.8 CamelCaseJSONResponse

```python
# src/common/infrastructure/responses/camel_case.py
import json
from typing import Any

from fastapi.responses import JSONResponse as FastAPIJSONResponse

from src.common.application.helpers.json_encoder import CamelCaseJSONEncoder, jsonable_encoder_camel


class CamelCaseJSONResponse(FastAPIJSONResponse):
    """Custom JSONResponse that automatically converts all keys to camelCase."""

    def render(self, content: Any) -> bytes:
        camel_content = jsonable_encoder_camel(content)
        return self.json_dumps(camel_content, cls=CamelCaseJSONEncoder).encode("utf-8")

    @staticmethod
    def json_dumps(obj: Any, *, cls: Any = CamelCaseJSONEncoder, **kwargs: Any) -> str:
        return json.dumps(obj, cls=cls, **kwargs)
```

### 1.9 ApiJSONResponse

```python
# src/common/infrastructure/responses/api_json.py
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder

from src.common.domain.entities.common.pagination import Page, Pagination
from src.common.domain.entities.common.reponses import ApiResponse
from src.common.infrastructure.responses.camel_case import CamelCaseJSONResponse


class ApiJSONResponse(CamelCaseJSONResponse):
    def render(self, content: Any) -> bytes:
        is_error_response = isinstance(content, dict) and "errors" in content

        if self.has_jsonable_content(content):
            if self.is_paginated(content):
                content: Page = content
                wrapped_content = ApiResponse(
                    data=content.items,
                    pagination=Pagination.from_page(content),
                    timestamp=datetime.now(UTC),
                )
                content = jsonable_encoder(obj=wrapped_content)
            else:
                wrapped_content = ApiResponse(
                    data=content,
                    timestamp=datetime.now(UTC),
                )
                content = jsonable_encoder(obj=wrapped_content, exclude={"pagination"})
        elif is_error_response:
            content["timestamp"] = datetime.now(UTC).isoformat()

        return super().render(content)

    @classmethod
    def is_paginated(cls, content: Any) -> bool:
        return isinstance(content, Page)

    @classmethod
    def has_jsonable_content(cls, content: Any) -> bool:
        is_error_response = isinstance(content, dict) and "errors" in content
        return (
            content is not None
            and not isinstance(content, str | bytes)
            and not is_error_response
            and not (isinstance(content, dict) and "data" in content and "timestamp" in content)
        )
```

Todas las respuestas se envuelven automaticamente en:
```json
{
  "data": { ... },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## 2. Excepciones de Autenticacion

```python
# src/common/domain/exceptions/auth.py
from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidCredentials",
            message="Credenciales Invalidas",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class InvalidGoogleIdTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidGoogleIdoken",
            message="Invalid Google Id Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class RetrieveGoogleUserError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.RetrieveGoogleUser",
            message="Retrieve Google User",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
```

```python
# src/common/domain/exceptions/common.py (excepciones relevantes a auth)
from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidOrExpiredTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidOrExpiredToken",
            message="Invalid or expired token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class InvalidOrExpiredRefreshTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidRefreshToken",
            message="Invalid Refresh Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
```

```python
# src/auth/domain/exceptions.py
from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidRefreshTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidRefreshToken",
            message="Invalid Refresh Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
```

---

## 3. Entidades de Dominio

### 3.1 JwtSession

```python
# src/common/domain/entities/common/jtw_session.py
from src.common.domain.mixins.entities import CamelModel


class JwtSession(CamelModel):
    access_token: str
    refresh_token: str
```

### 3.2 Entidades de sesion de usuario

```python
# src/common/domain/entities/auth/user_session.py
from pydantic import Field

from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.entities.tenant import Tenant
from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.entities.tenants.tenant_user import TenantUser
from src.common.domain.entities.user import User
from src.common.domain.mixins.entities import CamelModel


class UserSession(CamelModel):
    session: JwtSession
    user: User


class TenantUserProfile(CamelModel):
    user: User
    tenant: Tenant | None = None
    tenant_role: TenantRoleMeta | None = None


class TenantSessionParams(CamelModel):
    tenant: Tenant | None = Field(default=None)
    tenant_user: TenantUser | None = Field(default=None)
    tenant_role: TenantRoleMeta | None = Field(default=None)


class TenantUserSession(TenantUserProfile, TenantSessionParams):
    session: JwtSession
    user: User

    @property
    def display_first_name(self) -> str | None:
        if self.tenant_user:
            return self.tenant_user.first_name
        return self.user.first_name

    @property
    def display_last_name(self) -> str | None:
        if self.tenant_user:
            return self.tenant_user.last_name
        return self.user.last_name
```

### 3.3 Entidades de Google OAuth

```python
# src/auth/domain/entities/google_login.py
from pydantic import BaseModel


class GoogleAuthTokens(BaseModel):
    access_token: str
    id_token: str


class GoogleUser(BaseModel):
    email: str
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
```

---

## 4. Interfaces del Dominio (Contratos)

### 4.1 TokenBuilder (Creacion/Verificacion de JWTs)

```python
# src/common/domain/services/token_builder.py
from abc import ABC, abstractmethod
from datetime import timedelta

from src.common.domain.enums.base_enum import BaseEnum
from src.common.domain.mixins.entities import CamelModel


class JwtTokenScope(BaseEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class JwtTokenClaims(CamelModel):
    iss: str
    sub: str
    iat: int
    exp: int
    jti: str
    ns: str
    scope: JwtTokenScope


class TokenBuilder(ABC):
    @abstractmethod
    def create_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        exp_delta: timedelta,
        namespace: str = "JWT",
        jti: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_token(
        self,
        token: str,
        expected_scope: JwtTokenScope,
    ) -> JwtTokenClaims | None:
        raise NotImplementedError
```

### 4.2 TokenService (Orquestacion de Sesiones)

```python
# src/common/domain/services/token_service.py
from abc import ABC, abstractmethod

from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.services.token_builder import JwtTokenClaims, JwtTokenScope


class TokenService(ABC):
    @abstractmethod
    async def generate_token(self, sub: str, namespace: str = "JWT") -> JwtSession:
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> tuple[JwtTokenClaims, JwtSession]:
        raise NotImplementedError

    @abstractmethod
    async def get_claims(self, token: str, scope: JwtTokenScope) -> JwtTokenClaims | None:
        raise NotImplementedError

    @abstractmethod
    async def expire_refresh_token(self, refresh_token: str):
        raise NotImplementedError
```

### 4.3 TokenStore (Almacenamiento de Tokens)

```python
# src/common/domain/services/token_store.py
from abc import ABC, abstractmethod


class TokenStore(ABC):
    @abstractmethod
    async def store_token(self, sub: str, jti: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def get_token_jti(self, sub: str, namespace: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def blacklist_token_jti(self, jti: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def blacklist_token_sub(self, sub: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def is_blacklisted(self, jti: str, namespace: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def clean(self, jti: str, sub: str, namespace: str) -> bool:
        raise NotImplementedError
```

---

## 5. Implementaciones de Infraestructura

### 5.1 JwtTokenBuilder (Creacion y verificacion de JWTs)

```python
# src/common/infrastructure/services/jwt_token_builder.py
from datetime import UTC, datetime, timedelta
from typing import Any

from authlib.jose import JoseError, jwt
from uuid6 import uuid7

from src.common.application.logging import get_logger
from src.common.domain.services.token_builder import JwtTokenClaims, JwtTokenScope, TokenBuilder
from src.common.settings import settings

logger = get_logger(__name__)


class JwtTokenBuilder(TokenBuilder):
    def create_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        exp_delta: timedelta,
        namespace: str = "JWT",
        jti: str | None = None,
    ) -> str:
        jti = jti or uuid7().hex
        claims = self._build_claims(
            sub=sub,
            jti=jti,
            scope=str(scope),
            exp_delta=exp_delta,
            ns=namespace,
        )
        return jwt.encode(
            header={"alg": settings.JWT_ALGORITHM},
            payload=claims,
            key=settings.JWT_SECRET_KEY.encode("utf-8"),
        ).decode()

    def verify_token(
        self,
        token: str,
        expected_scope: JwtTokenScope,
    ) -> JwtTokenClaims | None:
        try:
            claims = jwt.decode(token, key=settings.JWT_SECRET_KEY.encode("utf-8"))
            if claims["scope"] != str(expected_scope):
                logger.error(
                    "jwt.token.scope_mismatch",
                    expected_scope=str(expected_scope),
                    actual_scope=claims.get("scope"),
                )
                return None
            claims.validate(now=int(datetime.now(UTC).timestamp()))
            return JwtTokenClaims.model_validate(claims)
        except JoseError as e:
            logger.error(
                "jwt.token.invalid",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    @classmethod
    def _build_claims(
        cls,
        sub: str,
        exp_delta: timedelta,
        jti: str,
        scope: str,
        ns: str = "JWT",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        return {
            "iss": settings.JWT_ISSUER,
            "sub": sub,
            "iat": int(now.timestamp()),
            "exp": int((now + exp_delta).timestamp()),
            "jti": jti,
            "ns": ns,
            "scope": scope,
        }
```

### 5.2 RedisTokenStore (Blacklist y tracking en Redis)

```python
# src/common/infrastructure/services/redis_token_store.py
from dataclasses import dataclass

from redis.asyncio import Redis

from src.common.domain.services.token_store import TokenStore


@dataclass
class RedisTokenStore(TokenStore):
    redis_client: Redis

    async def store_token(self, sub: str, jti: str, ttl: int, namespace: str):
        await self.redis_client.setex(f"{namespace}_RT:{sub}", ttl, jti)

    async def get_token_jti(self, sub: str, namespace: str) -> str | None:
        return await self.redis_client.get(f"{namespace}_RT:{sub}")

    async def blacklist_token_jti(self, jti: str, ttl: int, namespace: str):
        if ttl <= 0:
            return
        await self.redis_client.setex(f"{namespace}_BL:{jti}", ttl, 1)

    async def blacklist_token_sub(self, sub: str, ttl: int, namespace: str):
        token_jti = await self.get_token_jti(sub, namespace)
        if not token_jti:
            return
        await self.blacklist_token_jti(token_jti, ttl=ttl, namespace=namespace)

    async def is_blacklisted(self, jti: str, namespace: str) -> bool:
        return await self.redis_client.exists(f"{namespace}_BL:{jti}") == 1

    async def clean(self, jti: str, sub: str, namespace: str) -> bool:
        await self.redis_client.delete(f"{namespace}_RT:{sub}")
        await self.redis_client.delete(f"{namespace}_BL:{jti}")
        return await self.redis_client.delete(f"{namespace}_BL:{jti}")
```

**Claves en Redis:**

| Patron de clave | Proposito | Valor | TTL |
|---|---|---|---|
| `{namespace}_RT:{sub}` | Refresh token activo del usuario | JTI del refresh token | 7 dias |
| `{namespace}_BL:{jti}` | Token en blacklist (invalidado) | `1` | Tiempo restante de expiracion del token |

Ejemplo concreto:
- `USER_RT:550e8400-...` → `"0190a1b2c3d4..."` (JTI del refresh token activo)
- `USER_BL:0190a1b2c3d4...` → `1` (este JTI esta invalidado)

### 5.3 JwtTokenService (Orquestacion completa)

```python
# src/common/infrastructure/services/jwt_token_service.py
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from uuid6 import uuid7

from src.common.application.logging import get_logger
from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.exceptions.common import InvalidOrExpiredRefreshTokenError
from src.common.domain.services.token_builder import JwtTokenClaims, JwtTokenScope, TokenBuilder
from src.common.domain.services.token_service import TokenService
from src.common.domain.services.token_store import TokenStore
from src.common.settings import settings

logger = get_logger(__name__)


@dataclass
class JwtTokenService(TokenService):
    token_store: TokenStore
    token_builder: TokenBuilder

    async def generate_token(self, sub: str, namespace: str = "JWT") -> JwtSession:
        # 1. Blacklistear cualquier refresh token previo del usuario
        await self.token_store.blacklist_token_sub(
            sub=sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=namespace,
        )

        # 2. Generar JTIs unicos (UUIDv7)
        access_token_jti = uuid7().hex
        refresh_token_jti = uuid7().hex

        # 3. Crear ambos tokens
        access_token = self.token_builder.create_token(
            jti=access_token_jti,
            sub=sub,
            scope=JwtTokenScope.ACCESS,
            exp_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            namespace=namespace,
        )
        refresh_token = self.token_builder.create_token(
            jti=refresh_token_jti,
            sub=sub,
            scope=JwtTokenScope.REFRESH,
            exp_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
            namespace=namespace,
        )

        # 4. Almacenar JTI del refresh token en Redis
        await self.token_store.store_token(
            jti=refresh_token_jti,
            sub=sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=namespace,
        )

        return JwtSession(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> tuple[JwtTokenClaims, JwtSession]:
        # 1. Verificar el refresh token (decode + validate scope + expiracion)
        claims = self.token_builder.verify_token(
            token=refresh_token,
            expected_scope=JwtTokenScope.REFRESH,
        )

        if not claims:
            raise InvalidOrExpiredRefreshTokenError

        # 2. Verificar que no este en la blacklist
        if await self.token_store.is_blacklisted(jti=claims.jti, namespace=claims.ns):
            logger.warning(
                "jwt.token.blacklisted",
                jti=claims.jti,
                sub=claims.sub,
                namespace=claims.ns,
            )
            raise InvalidOrExpiredRefreshTokenError

        # 3. Rotacion: blacklistear el refresh token actual
        await self.token_store.blacklist_token_sub(
            sub=claims.sub,
            ttl=self._get_exp_remaining_seconds(claims.exp),
            namespace=claims.ns,
        )

        # 4. Generar nuevo par de tokens
        access_token_jti = uuid7().hex
        refresh_token_jti = uuid7().hex

        access_token = self.token_builder.create_token(
            jti=access_token_jti,
            sub=claims.sub,
            scope=JwtTokenScope.ACCESS,
            exp_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = self.token_builder.create_token(
            jti=refresh_token_jti,
            sub=claims.sub,
            scope=JwtTokenScope.REFRESH,
            exp_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
        )

        # 5. Almacenar nuevo refresh token en Redis
        await self.token_store.store_token(
            jti=refresh_token_jti,
            sub=claims.sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=claims.ns,
        )

        return claims, JwtSession(access_token=access_token, refresh_token=refresh_token)

    async def get_claims(self, token: str, scope: JwtTokenScope) -> JwtTokenClaims | None:
        return self.token_builder.verify_token(
            token=token,
            expected_scope=scope,
        )

    async def expire_refresh_token(self, refresh_token: str):
        jwt_claims = await self.get_claims(refresh_token, scope=JwtTokenScope.REFRESH)
        await self.token_store.blacklist_token_sub(
            sub=jwt_claims.sub,
            ttl=self._get_exp_remaining_seconds(jwt_claims.exp),
            namespace=jwt_claims.ns,
        )
        await self.token_store.clean(
            jti=jwt_claims.jti,
            sub=jwt_claims.sub,
            namespace=jwt_claims.ns,
        )

    @classmethod
    def _get_exp_remaining_seconds(cls, exp: int) -> int:
        return max(exp - int(datetime.now(UTC).timestamp()), 0)
```

### 5.4 Password Hashing

```python
# src/common/infrastructure/helpers/password.py
import bcrypt


def hash_password(raw_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def check_password(raw_password: str, encoded_password: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), encoded_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False
```

---

## 6. Dependency de Autenticacion (Proteccion de Rutas)

```python
# src/common/infrastructure/dependencies/session.py
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from uuid6 import UUID

from src.common.application.queries.poses import GetTenantPosByIdQuery
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.entities.tenants.tenant_pos import TenantPOS
from src.common.domain.entities.user import User
from src.common.domain.exceptions.common import InvalidOrExpiredTokenError
from src.common.domain.services.token_builder import JwtTokenScope
from src.common.infrastructure.dependencies.common import BusContextDep, DomainContextDep

security = HTTPBearer()


async def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> User:
    access_token = credentials.credentials
    token_service = domain_context.token_service

    claim = await token_service.get_claims(token=access_token, scope=JwtTokenScope.ACCESS)
    if not claim:
        raise InvalidOrExpiredTokenError

    if not claim or not claim.sub:
        raise InvalidOrExpiredTokenError

    result = await bus_context.query_bus.ask(
        query=GetUserByIdQuery(user_id=UUID(claim.sub)),
    )

    if not isinstance(result, User):
        raise InvalidOrExpiredTokenError

    return result


AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]


async def get_authenticated_pos(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> TenantPOS:
    token = credentials.credentials
    token_service = domain_context.token_service

    claim = await token_service.get_claims(token=token, scope=JwtTokenScope.ACCESS)
    if not claim:
        raise InvalidOrExpiredTokenError

    if not claim or not claim.sub:
        raise InvalidOrExpiredTokenError

    result = await bus_context.query_bus.ask(
        query=GetTenantPosByIdQuery(instance_id=UUID(claim.sub)),
    )

    if not isinstance(result, TenantPOS):
        raise InvalidOrExpiredTokenError

    return result


AuthenticatedPOSDep = Annotated[User, Depends(get_authenticated_pos)]
```

**Header requerido para rutas protegidas:**
```
Authorization: Bearer eyJ...
```

El `HTTPBearer()` de FastAPI automaticamente:
- Valida que el header `Authorization` exista.
- Valida que tenga el esquema `Bearer`.
- Extrae el token.
- Si no hay header o el esquema es incorrecto, retorna 403.

---

## 7. Use Cases de Autenticacion

### 7.1 TenantSessionMixin (Mixin compartido)

```python
# src/auth/application/use_cases/mixins.py
from uuid import UUID

from src.common.application.queries.tenants import GetTenantPermaLinkQuery, GetTenantUserQuery, GetUserTenantQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantSessionParams
from src.common.domain.entities.payments.payment_permalink import PaymentPermaLink
from src.common.domain.entities.tenant import Tenant
from src.common.domain.entities.tenants.tenant_user import TenantUser
from src.common.domain.entities.user import User
from src.common.domain.enums.users import TenantUserStatus


class TenantSessionMixin:
    query_bus: QueryBus

    async def _get_tenant_session_params(self, user: User) -> TenantSessionParams:
        tenant = await self._get_tenant(user_id=user.uuid)

        tenant_user = await self._get_tenant_user(user=user, tenant=tenant)
        tenant_role = tenant_user.tenant_role_meta if tenant_user else None
        render_tenant = tenant if tenant_user else None

        return TenantSessionParams(
            tenant=render_tenant,
            tenant_user=tenant_user,
            tenant_role=tenant_role,
        )

    async def _get_tenant(self, user_id: UUID) -> Tenant | None:
        tenant: Tenant | None = await self.query_bus.ask(
            query=GetUserTenantQuery(user_id),
        )
        if not tenant:
            return None
        tenant.payment_permalink = tenant.payment_permalink or await self._get_tenant_permalink(tenant.uuid)
        return tenant

    async def _get_tenant_user(
        self,
        user: User,
        tenant: Tenant | None = None,
    ) -> TenantUser | None:
        if not tenant:
            return None
        return await self.query_bus.ask(
            query=GetTenantUserQuery(
                user_id=user.uuid,
                tenant_id=tenant.uuid,
                status=TenantUserStatus.ACTIVE,
            ),
        )

    async def _get_tenant_permalink(self, tenant_id: UUID) -> PaymentPermaLink | None:
        return await self.query_bus.ask(
            query=GetTenantPermaLinkQuery(tenant_id),
        )
```

### 7.2 TenantUserSessionBuilder (Login)

```python
# src/auth/application/use_cases/session_builder.py
from dataclasses import dataclass
from uuid import UUID

from src.auth.application.use_cases.mixins import TenantSessionMixin
from src.common.application.queries.users import CheckPasswordQuery, GetUserByEmailQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserProfile, TenantUserSession
from src.common.domain.entities.user import User
from src.common.domain.exceptions.auth import InvalidCredentialsError
from src.common.domain.exceptions.users import UserNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService


@dataclass
class TenantUserProfileBuilder(TenantSessionMixin, UseCase):
    user: User
    query_bus: QueryBus

    async def execute(self) -> TenantUserProfile:
        tenant = await self._get_tenant(user_id=self.user.uuid)
        tenant_user = await self._get_tenant_user(user=self.user, tenant=tenant)
        tenant_role = tenant_user.tenant_role_meta if tenant_user else None

        return TenantUserProfile(
            user=self.user,
            tenant=tenant,
            tenant_role=tenant_role,
        )


@dataclass
class TenantUserSessionBuilder(TenantSessionMixin, UseCase):
    email: str
    password: str
    query_bus: QueryBus
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
        user = await self._get_user()
        await self._validate_password(user.uuid)

        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
        )
        params = await self._get_tenant_session_params(user=user)
        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=params.tenant,
            tenant_user=params.tenant_user,
            tenant_role=params.tenant_role,
        )

    async def _get_user(self) -> User:
        result = await self.query_bus.ask(
            query=GetUserByEmailQuery(email=self.email),
        )
        if not isinstance(result, User):
            raise UserNotFoundError
        return result

    async def _validate_password(self, user_id: UUID):
        result = await self.query_bus.ask(
            query=CheckPasswordQuery(user_id=user_id, raw_password=self.password),
        )
        if not isinstance(result, bool) or not result:
            raise InvalidCredentialsError
```

### 7.3 TenantUserRefreshSessionBuilder (Refresh)

```python
# src/auth/application/use_cases/refresh_builder.py
from dataclasses import dataclass

from uuid6 import UUID

from src.auth.application.use_cases.mixins import TenantSessionMixin
from src.auth.domain.exceptions import InvalidRefreshTokenError
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.entities.user import User
from src.common.domain.exceptions.users import UserNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService


@dataclass
class TenantUserRefreshSessionBuilder(TenantSessionMixin, UseCase):
    refresh_token: str
    query_bus: QueryBus
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
        await self._validate_refresh_token()
        jwt_claims, jwt_session = await self.token_service.refresh_token(self.refresh_token)

        user = await self._get_user(UUID(jwt_claims.sub))
        params = await self._get_tenant_session_params(user=user)

        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=params.tenant,
            tenant_user=params.tenant_user,
            tenant_role=params.tenant_role,
        )

    async def _validate_refresh_token(self):
        if not self.refresh_token:
            raise InvalidRefreshTokenError

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.query_bus.ask(
            query=GetUserByIdQuery(user_id),
        )
        if not isinstance(result, User):
            raise UserNotFoundError
        return result
```

### 7.4 GoogleSessionBuilder (Google OAuth)

```python
# src/auth/application/use_cases/google_session_builder.py
from dataclasses import dataclass
from uuid import UUID

from src.auth.domain.entities.google_login import GoogleAuthTokens, GoogleUser
from src.common.application.queries.tenants import GetUserTenantQuery
from src.common.application.queries.users import GetOrCreateUserQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.entities.tenant import Tenant
from src.common.domain.entities.user import User
from src.common.domain.exceptions.auth import InvalidGoogleIdTokenError, RetrieveGoogleUserError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService


@dataclass
class GoogleSessionBuilder(UseCase):
    google_tokens: GoogleAuthTokens
    google_user: GoogleUser | None
    query_bus: QueryBus
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
        if not self.google_user:
            raise InvalidGoogleIdTokenError

        user: User | None = await self.query_bus.ask(
            query=GetOrCreateUserQuery(
                email=self.google_user.email,
                first_name=self.google_user.given_name,
                last_name=self.google_user.family_name,
                picture=self.google_user.picture,
            )
        )

        if not isinstance(user, User):
            raise RetrieveGoogleUserError

        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
        )
        tenant = await self._get_tenant(user_id=user.uuid)

        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=tenant,
        )

    async def _get_tenant(self, user_id: UUID) -> Tenant | None:
        return await self.query_bus.ask(
            query=GetUserTenantQuery(user_id),
        )
```

---

## 8. Endpoints (Presentation Layer)

### 8.1 Login

```python
# src/auth/presentation/endpoints/login.py
from fastapi import Depends, status

from src.auth.application.use_cases.session_builder import TenantUserSessionBuilder
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class LoginRequest(CamelCaseRequest):
    email: str
    password: str


async def login(
    payload: LoginRequest,
    app_context: AppContext = Depends(get_app_context),
):
    tenant_user_session = await TenantUserSessionBuilder(
        email=payload.email,
        password=payload.password,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(tenant_user_session).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
```

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "mi_password"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "session": {
      "accessToken": "eyJ...",
      "refreshToken": "eyJ..."
    },
    "user": {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "username": "usuario",
      "firstName": "Juan",
      "lastName": "Perez",
      "phoneNumber": null,
      "emailAddress": null
    },
    "tenant": {
      "uuid": "...",
      "name": "Mi Empresa",
      "slug": "mi-empresa",
      "timeZone": "America/Mexico_City",
      "countryCode": "MX",
      "currencyCode": "MXN",
      "category": "restaurant",
      "logoUrl": null,
      "contactEmail": "...",
      "status": "active",
      "paymentLink": null,
      "paymentPermalink": null
    },
    "tenantRole": { ... }
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

### 8.2 Google Login

```python
# src/auth/presentation/endpoints/google_login.py
from fastapi import Depends, status

from src.auth.application.use_cases.google_session_builder import GoogleSessionBuilder
from src.auth.presentation.endpoints.helpers.google import get_google_tokens, verity_google_id_token
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class GoogleLoginRequest(CamelCaseRequest):
    code: str


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

### 8.3 Google OAuth Helper

```python
# src/auth/presentation/endpoints/helpers/google.py
import httpx
from authlib.jose import JsonWebKey, KeySet, jwt
from fastapi import HTTPException, status

from src.auth.domain.entities.google_login import GoogleAuthTokens, GoogleUser
from src.common.application.logging import get_logger
from src.common.settings import settings

logger = get_logger(__name__)


async def get_google_tokens(code: str) -> GoogleAuthTokens:
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(settings.GOOGLE_TOKEN_URL, data=token_data)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al obtener tokens de Google: {e.response.text}",
            )

        token_response = response.json()
        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")

        if not access_token or not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudieron obtener tokens de Google válidos.",
            )
    return GoogleAuthTokens(access_token=access_token, id_token=id_token)


async def get_google_certs() -> KeySet:
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.GOOGLE_CERTS_URL, timeout=5)
        return JsonWebKey.import_key_set(response.json())


async def verity_google_id_token(id_token: str) -> GoogleUser | None:
    google_key_set = await get_google_certs()
    try:
        claims = jwt.decode(
            id_token,
            key=google_key_set,
            claims_options={"aud": {"values": [settings.GOOGLE_CLIENT_ID]}},
        )
        claims.validate()

        user_email = claims.get("email")
        user_given_name = claims.get("given_name", user_email)
        user_family_name = claims.get("family_name")
        user_picture = claims.get("picture")

        if not user_email:
            logger.error(
                "google.auth.token.invalid",
                reason="email_missing",
                error="ID Token does not contain email",
            )
            return None

        return GoogleUser(
            email=user_email,
            given_name=user_given_name,
            family_name=user_family_name,
            picture=user_picture,
        )

    except Exception as e:
        logger.error(
            "google.auth.token.validation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
```

### 8.4 Refresh

```python
# src/auth/presentation/endpoints/refresh.py
from fastapi import Depends

from src.auth.application.use_cases.refresh_builder import TenantUserRefreshSessionBuilder
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.constants import status
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UserRefreshRequest(CamelCaseRequest):
    refresh_token: str


async def refresh(
    payload: UserRefreshRequest,
    app_context: AppContext = Depends(get_app_context),
):
    user_session = await TenantUserRefreshSessionBuilder(
        refresh_token=payload.refresh_token,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(user_session).to_dict,
        status_code=status.HTTP_200_OK,
    )
```

**Request:**
```json
{
  "refreshToken": "eyJ..."
}
```

**Response (200 OK):** Misma estructura que login.

### 8.5 Logout

```python
# src/auth/presentation/endpoints/logout.py
from fastapi import Depends

from src.common.domain.constants import status
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UserLogoutRequest(CamelCaseRequest):
    refresh_token: str


async def logout(
    payload: UserLogoutRequest,
    app_context: AppContext = Depends(get_app_context),
):
    token_service = app_context.domain.token_service
    await token_service.expire_refresh_token(payload.refresh_token)

    return ApiJSONResponse(content=TaskResult.success(), status_code=status.HTTP_200_OK)
```

**Request:**
```json
{
  "refreshToken": "eyJ..."
}
```

**Response (200 OK):**
```json
{
  "data": {
    "status": "success"
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

Despues del logout:
- El refresh token queda invalidado en Redis.
- El access token **sigue siendo valido** hasta que expire (30 min max), ya que no se verifica contra blacklist en cada request (es stateless).
- El cliente debe descartar el access token de su almacenamiento local.

### 8.6 Session

```python
# src/auth/presentation/endpoints/session.py
from fastapi import Depends

from src.auth.application.use_cases.session_builder import TenantUserProfileBuilder
from src.auth.presentation.presenters.session import TenantUserProfilePresenter
from src.common.domain.constants import status
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.entities.user import User
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def session(
    app_context: AppContext = Depends(get_app_context),
    current_user: User = Depends(get_authenticated_user),
    response_model=TenantUserSession,
):
    tenant_user_profile = await TenantUserProfileBuilder(
        user=current_user,
        query_bus=app_context.bus.query_bus,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserProfilePresenter(instance=tenant_user_profile).to_dict,
        status_code=status.HTTP_200_OK,
    )
```

**Headers:** `Authorization: Bearer eyJ...`

**Response (200 OK):** Retorna perfil sin tokens (user + tenant + tenantRole).

### 8.7 Reset Password

```python
# src/auth/presentation/endpoints/reset_password.py
from fastapi import Depends, status

from src.common.application.commands.common import SendEmailCommand
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class ResetPasswordRequest(CamelCaseRequest):
    email: str


async def reset_password(
    payload: ResetPasswordRequest,
    app_context: AppContext = Depends(get_app_context),
):
    await app_context.bus.command_bus.dispatch(
        command=SendEmailCommand(
            to_emails=["example@gmail.com"],
            template_name="reset_password",
            context={
                "name": payload.email,
            },
        ),
        run_async=False,
    )

    return ApiJSONResponse(
        content=TaskResult.success(),
        status_code=status.HTTP_200_OK,
    )
```

> **Nota:** Este endpoint esta en un estado basico. Actualmente envia un email con template `reset_password` pero no genera un token de reset ni tiene un endpoint para confirmar el cambio de password.

---

## 9. Presenters (Formateo de Respuestas)

```python
# src/auth/presentation/presenters/session.py
from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.uuids import optional_string
from src.common.domain.entities.auth.user_session import TenantUserProfile, TenantUserSession
from src.common.domain.entities.payments.payment_link import PaymentLink
from src.common.domain.entities.tenant import Tenant
from src.common.domain.entities.user import User
from src.common.domain.interfaces.presenter import Presenter
from src.common.infrastructure.helpers.statics import get_static_path
from src.common.presentation.presenters.payment_permalink import PaymentPermaLinkPresenter
from src.common.presentation.presenters.tenant_role import TenantMetaRolePresenter


@dataclass
class UserPresenter(Presenter[User]):
    instance: User
    first_name: str | None = None
    last_name: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "username": self.instance.username,
            "first_name": self.first_name or self.instance.first_name,
            "last_name": self.last_name or self.instance.last_name,
            "phone_number": (self.instance.phone_number.model_dump() if self.instance.phone_number else None),
            "email_address": (self.instance.email_address.model_dump() if self.instance.email_address else None),
        }


class TenantPublicPresenter(Presenter[Tenant]):
    instance: Tenant

    def __init__(self, instance: Tenant):
        self.instance = instance
        super().__init__(instance)  # type: ignore

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "slug": self.instance.slug,
            "time_zone": str(self.instance.time_zone),
            "country_code": str(self.instance.country_code),
            "currency_code": str(self.instance.currency_code),
            "category": optional_string(self.instance.category),
            "logo_url": (get_static_path(self.instance.logo_url) if self.instance.logo_url else None),
            "contact_email": self.instance.contact_email,
            "status": str(self.instance.status),
            "payment_link": None,
            "payment_permalink": (
                PaymentPermaLinkPresenter(self.instance.payment_permalink).to_dict
                if self.instance.payment_permalink
                else None
            ),
        }


@dataclass
class TenantUserSessionPresenter(Presenter[TenantUserSession]):
    instance: TenantUserSession

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.instance.session.model_dump(),
            "user": UserPresenter(
                instance=self.instance.user,
                first_name=self.instance.display_first_name,
                last_name=self.instance.display_last_name,
            ).to_dict,
            "tenant": (TenantPublicPresenter(self.instance.tenant).to_dict if self.instance.tenant else None),
            "tenant_role": (
                TenantMetaRolePresenter(self.instance.tenant_role).to_dict if self.instance.tenant_role else None
            ),
        }


@dataclass
class TenantUserProfilePresenter(Presenter[TenantUserProfile]):
    instance: TenantUserProfile

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "user": UserPresenter(instance=self.instance.user).to_dict,
            "tenant": (TenantPublicPresenter(self.instance.tenant).to_dict if self.instance.tenant else None),
            "tenant_role": (
                TenantMetaRolePresenter(self.instance.tenant_role).to_dict if self.instance.tenant_role else None
            ),
        }
```

> `TenantPublicPresenter` esta definido en el mismo archivo. `TenantMetaRolePresenter` se importa de `src/common/presentation/presenters/tenant_role.py` y `PaymentPermaLinkPresenter` de `src/common/presentation/presenters/payment_permalink.py`.

---

## 10. Router

```python
# src/auth/presentation/router.py
from fastapi import APIRouter

from src.auth.presentation.endpoints.google_login import google_login
from src.auth.presentation.endpoints.login import login
from src.auth.presentation.endpoints.logout import logout
from src.auth.presentation.endpoints.refresh import refresh
from src.auth.presentation.endpoints.reset_password import reset_password
from src.auth.presentation.endpoints.session import session

auth_router = router = APIRouter(prefix="/auth", tags=["auth"])

auth_router.add_api_route(path="/login", endpoint=login, methods=["POST"])
auth_router.add_api_route(path="/google-login", endpoint=google_login, methods=["POST"])
auth_router.add_api_route(path="/reset-password", endpoint=reset_password, methods=["POST"])
auth_router.add_api_route(path="/refresh", endpoint=refresh, methods=["POST"])
auth_router.add_api_route(path="/logout", endpoint=logout, methods=["POST"])
auth_router.add_api_route(path="/session", endpoint=session, methods=["GET"])
```

---

## 11. Middleware de Headers de Seguridad

```python
# src/common/infrastructure/middlewares/security_headers.py
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if "Server" in response.headers:
            del response.headers["Server"]

        return response
```

---

## 12. Diagramas de Flujo

### Login
```
Cliente                    API                      Redis                BD
  |                         |                        |                   |
  |-- POST /auth/login ---->|                        |                   |
  |   {email, password}     |                        |                   |
  |                         |-- GetUserByEmailQuery ----------------->  |
  |                         |<-- User -------------------------------|  |
  |                         |-- CheckPasswordQuery ------------------>  |
  |                         |<-- true/false --------------------------|  |
  |                         |                        |                   |
  |                         |-- blacklist_token_sub ->|                  |
  |                         |   (invalida sesion     |                   |
  |                         |    anterior si existe)  |                  |
  |                         |-- store_token --------->|                  |
  |                         |   (guarda nuevo JTI)    |                  |
  |                         |                        |                   |
  |<-- 201 {session, user,  |                        |                   |
  |    tenant, tenantRole}  |                        |                   |
```

### Refresh
```
Cliente                    API                      Redis
  |                         |                        |
  |-- POST /auth/refresh -->|                        |
  |   {refreshToken}        |                        |
  |                         |-- verify JWT           |
  |                         |   (decode + validate)  |
  |                         |-- is_blacklisted? ----->|
  |                         |<-- false ---------------|
  |                         |-- blacklist old token ->|
  |                         |-- store new token ----->|
  |                         |                        |
  |<-- 200 {session, ...}   |                        |
```

### Logout
```
Cliente                    API                      Redis
  |                         |                        |
  |-- POST /auth/logout --->|                        |
  |   {refreshToken}        |                        |
  |                         |-- decode claims        |
  |                         |-- blacklist_token_sub ->|
  |                         |-- clean (delete keys) ->|
  |                         |                        |
  |<-- 200 {success}        |                        |
```

### Validacion de Access Token (rutas protegidas)
```
Cliente                    API                       BD
  |                         |                        |
  |-- GET /auth/session --->|                        |
  |   Authorization: Bearer |                        |
  |                         |-- decode JWT           |
  |                         |   (verify signature    |
  |                         |    + scope + exp)      |
  |                         |-- GetUserByIdQuery --->|
  |                         |<-- User ---------------|
  |                         |                        |
  |<-- 200 {user, tenant}   |                        |
```

---

## 13. Estructura de Archivos

```
src/
├── auth/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── google_login.py          # GoogleAuthTokens, GoogleUser
│   │   ├── exceptions.py               # InvalidRefreshTokenError
│   │   ├── repositories/
│   │   │   └── otp.py                   # (legacy) OTPRepository - sin uso
│   │   └── services/
│   │       └── token_builder.py         # (legacy) LegacyTokenBuilder - sin uso
│   ├── application/
│   │   └── use_cases/
│   │       ├── mixins.py                # TenantSessionMixin
│   │       ├── session_builder.py       # TenantUserSessionBuilder, TenantUserProfileBuilder
│   │       ├── refresh_builder.py       # TenantUserRefreshSessionBuilder
│   │       └── google_session_builder.py # GoogleSessionBuilder
│   ├── infrastructure/
│   │   ├── bus_wiring.py                # (legacy) auth_wiring() - vacio
│   │   └── services/
│   │       └── jwt_token_builder.py     # (legacy) LegacyJWTTokenBuilder - sin uso
│   └── presentation/
│       ├── endpoints/
│       │   ├── login.py
│       │   ├── google_login.py
│       │   ├── refresh.py
│       │   ├── logout.py
│       │   ├── reset_password.py
│       │   ├── session.py
│       │   └── helpers/
│       │       └── google.py            # get_google_tokens, verity_google_id_token
│       ├── presenters/
│       │   └── session.py               # TenantUserSessionPresenter, TenantUserProfilePresenter
│       ├── requests/
│       │   └── google_login.py          # (legacy) - sin uso
│       ├── responses/
│       │   └── google_login.py          # (legacy) - sin uso
│       └── router.py                    # auth_router
├── common/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── common/
│   │   │   │   ├── jtw_session.py       # JwtSession
│   │   │   │   ├── requests.py          # CamelCaseRequest
│   │   │   │   └── task_result.py       # TaskResult
│   │   │   └── auth/
│   │   │       └── user_session.py      # TenantUserSession, TenantUserProfile
│   │   ├── enums/
│   │   │   └── base_enum.py             # BaseEnum
│   │   ├── exceptions/
│   │   │   ├── _base.py                 # DomainError
│   │   │   ├── auth.py                  # InvalidCredentialsError, etc.
│   │   │   └── common.py               # InvalidOrExpiredTokenError, etc.
│   │   ├── interfaces/
│   │   │   ├── use_case.py              # UseCase (ABC)
│   │   │   └── presenter.py            # Presenter (Protocol)
│   │   ├── mixins/
│   │   │   └── entities.py              # CamelModel, SnakeModel
│   │   └── services/
│   │       ├── token_builder.py         # TokenBuilder (ABC), JwtTokenClaims, JwtTokenScope
│   │       ├── token_service.py         # TokenService (ABC)
│   │       └── token_store.py           # TokenStore (ABC)
│   ├── infrastructure/
│   │   ├── dependencies/
│   │   │   └── session.py               # get_authenticated_user, AuthenticatedUserDep
│   │   ├── helpers/
│   │   │   └── password.py              # hash_password, check_password
│   │   ├── middlewares/
│   │   │   └── security_headers.py      # SecurityHeadersMiddleware
│   │   ├── responses/
│   │   │   ├── camel_case.py            # CamelCaseJSONResponse
│   │   │   └── api_json.py             # ApiJSONResponse
│   │   └── services/
│   │       ├── jwt_token_builder.py     # JwtTokenBuilder
│   │       ├── jwt_token_service.py     # JwtTokenService
│   │       └── redis_token_store.py     # RedisTokenStore
│   └── settings.py                      # Settings (JWT_*, GOOGLE_*)
```

---

## 14. Archivos Legacy (no usados en el flujo actual)

El modulo `src/auth/` contiene algunos archivos legacy que **no participan** en el flujo de autenticacion actual. Se listan aqui para evitar confusion al explorar el codigo:

| Archivo | Contenido | Razon de exclusion |
|---|---|---|
| `domain/repositories/otp.py` | `OTPRepository` (ABC) para OTP por telefono | Sin implementacion, no usado por ningun endpoint |
| `domain/services/token_builder.py` | `LegacyTokenBuilder` (ABC) | Reemplazado por `common/domain/services/token_builder.py` (`TokenBuilder`) |
| `infrastructure/services/jwt_token_builder.py` | `LegacyJWTTokenBuilder` | Reemplazado por `common/infrastructure/services/jwt_token_builder.py` (`JwtTokenBuilder`). Usa `pytz` y `user.token_data` (patron anterior) |
| `infrastructure/bus_wiring.py` | `auth_wiring()` | Funcion vacia (`pass`), sin handlers registrados |
| `presentation/requests/google_login.py` | Request model legacy para Google Login | El endpoint actual define `GoogleLoginRequest` directamente en `endpoints/google_login.py` |
| `presentation/responses/google_login.py` | Response models legacy para Google Login | El endpoint actual usa `TenantUserSessionPresenter` |

El sistema de autenticacion activo usa exclusivamente las interfaces y servicios en `src/common/domain/services/` con sus implementaciones en `src/common/infrastructure/services/`.

---

## 15. Consideraciones para Replicar

1. **Una sesion activa por usuario**: Al hacer login o refresh, el refresh token anterior se blacklistea automaticamente. Solo puede haber un refresh token activo por `{namespace}:{sub}`.

2. **Rotacion de refresh tokens**: Cada uso del refresh token genera uno nuevo e invalida el anterior. Si alguien intenta reusar un refresh token ya rotado, sera rechazado por la blacklist.

3. **Access tokens son stateless**: No se verifican contra Redis en cada request. Solo se valida la firma HS256 y la expiracion. La invalidacion real depende de su corta vida (30 min).

4. **TTLs auto-limpiantes**: Las entradas de blacklist en Redis usan TTL = tiempo restante de expiracion del token. Se auto-eliminan cuando el token habria expirado naturalmente.

5. **Namespace separado**: El campo `ns` permite diferentes dominios de tokens (USER, JWT, POS) sin colision en las claves de Redis.

6. **Multi-tenant**: La sesion incluye informacion del tenant, el tenant_user y su rol. Un usuario puede pertenecer a multiples tenants.

7. **Conversion automatica camelCase/snake_case**: `CamelCaseRequest` convierte input camelCase a snake_case. `CamelCaseJSONResponse` convierte output snake_case a camelCase.

8. **Respuestas envueltas**: Todas las respuestas se envuelven en `{ "data": ..., "timestamp": "..." }` via `ApiJSONResponse`.

9. **Clean Architecture**: Las interfaces (ABC) viven en `domain/services/`, las implementaciones en `infrastructure/services/`. Se inyectan via FastAPI `Depends()`.
