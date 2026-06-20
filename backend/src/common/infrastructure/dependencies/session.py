from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from uuid6 import UUID

from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.models.user import User
from src.common.domain.exceptions.common import InvalidOrExpiredTokenError
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.infrastructure.dependencies.common import BusContextDep, DomainContextDep

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


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


async def get_optional_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
) -> User | None:
    if not credentials:
        return None

    access_token = credentials.credentials
    token_service = domain_context.token_service

    claim = await token_service.get_claims(token=access_token, scope=JwtTokenScope.ACCESS)
    if not claim or not claim.sub:
        return None

    result = await bus_context.query_bus.ask(
        query=GetUserByIdQuery(user_id=UUID(claim.sub)),
    )

    if not isinstance(result, User):
        return None

    return result


async def get_authenticated_superuser(
    user: Annotated[User, Depends(get_authenticated_user)],
) -> User:
    if not user.is_superuser:
        raise InvalidOrExpiredTokenError
    return user


AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]
OptionalAuthenticatedUserDep = Annotated[User | None, Depends(get_optional_authenticated_user)]
AuthenticatedSuperuserDep = Annotated[User, Depends(get_authenticated_superuser)]
