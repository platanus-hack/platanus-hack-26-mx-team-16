"""Dependencias del plano ``/staff/v1`` (ADR 0001).

- ``get_staff_user``: claim ``is_staff`` presente **Y** fila activa en
  ``staff_users`` (consulta por request ⇒ revocación inmediata). SIN bypass
  dev — el claim solo gatea, nunca autoriza.
- ``reject_tenant_header``: ``X-Tenant`` recibido ⇒ 400 (el tenant de cada
  recurso sale del recurso mismo).
- ``staff_audit``: dependencia-yield a nivel de router — escribe una fila en
  ``staff_access_events`` por CADA request (cobertura por construcción),
  con sesión propia para sobrevivir transacciones rotas del handler.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials

from src.common.application.logging import get_logger
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.infrastructure.dependencies.common import AsyncSessionDep, DomainContextDep
from src.common.infrastructure.dependencies.session import security
from src.common.infrastructure.middlewares.request_tracking import get_request_id
from src.staff.domain.exceptions import (
    StaffAccessRequiredError,
    StaffAuditWriteError,
    StaffTenantHeaderError,
)
from src.staff.domain.models.staff_access_event import StaffAccessEvent
from src.staff.domain.models.staff_user import StaffUser
from src.staff.infrastructure.repositories.sql_staff_access_event import (
    SQLStaffAccessEventRepository,
)
from src.staff.infrastructure.repositories.sql_staff_user import SQLStaffUserRepository

logger = get_logger(__name__)

# (método, sufijo de ruta, acción del audit). Todo endpoint nuevo del router
# staff DEBE añadirse aquí — el test de cobertura lo exige.
ROUTE_ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("GET", "/tasks", "tasks.list"),
    ("POST", "/tasks/{task_id}/claim", "tasks.claim"),
    ("POST", "/tasks/{task_id}/resolve", "tasks.resolve"),
    ("GET", "/cases/{case_id}", "cases.view"),
    ("GET", "/audit", "audit.list"),
    ("GET", "/metrics", "metrics.view"),
)


# Acciones que MUTAN estado: su audit debe escribirse o la request falla
# (ADR 0001 — cobertura 100 %). Las lecturas degradan con warning.
_MUTATING_ACTIONS: frozenset[str] = frozenset({"tasks.claim", "tasks.resolve"})


def action_for_route(method: str, path_template: str) -> str | None:
    for route_method, suffix, action in ROUTE_ACTIONS:
        if route_method == method and path_template.endswith(suffix):
            return action
    return None


def _client_ip(request: Request) -> str | None:
    """IP del cliente respetando el proxy (prod): primer hop de
    ``X-Forwarded-For`` si está presente, con fallback a ``client.host``."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop[:64]
    return request.client.host if request.client else None


async def get_staff_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: AsyncSessionDep,
    domain_context: DomainContextDep,
) -> StaffUser:
    claims = await domain_context.token_service.get_claims(
        token=credentials.credentials,
        scope=JwtTokenScope.ACCESS,
    )
    # Claim ausente y fila inactiva son la MISMA 403: no se filtra cuál falló.
    if not claims or not claims.sub or not claims.is_staff:
        raise StaffAccessRequiredError

    staff_user = await SQLStaffUserRepository(session).find_active_by_user_id(UUID(claims.sub))
    if staff_user is None:
        # Revocación inmediata: el token puede seguir vivo, la fila manda.
        raise StaffAccessRequiredError
    return staff_user


StaffUserDep = Annotated[StaffUser, Depends(get_staff_user)]


async def reject_tenant_header(
    tenant_slug: Annotated[str | None, Header(alias="X-Tenant")] = None,
) -> None:
    if tenant_slug is not None:
        raise StaffTenantHeaderError


def _path_param_uuid(request: Request, name: str) -> UUID | None:
    raw = request.path_params.get(name)
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return None


def _action_for_request(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", request.url.path)
    return action_for_route(request.method, template) or f"{request.method}:{template}"[:40]


async def _write_access_event(request: Request, staff_user: StaffUser, action: str) -> None:
    event = StaffAccessEvent(
        uuid=uuid4(),
        staff_user_id=staff_user.uuid,
        action=action,
        # Los handlers enriquecen vía request.state cuando cargan el recurso.
        tenant_id=getattr(request.state, "staff_audit_tenant_id", None),
        case_id=getattr(request.state, "staff_audit_case_id", None) or _path_param_uuid(request, "case_id"),
        task_id=_path_param_uuid(request, "task_id"),
        request_id=get_request_id(request),
        # Proxy en prod: primer hop de X-Forwarded-For, fallback a client.host.
        ip=_client_ip(request),
        metadata={"path": str(request.url.path), "method": request.method},
    )
    # Sesión PROPIA: el audit debe escribirse aunque el handler haya dejado
    # la sesión del request en una transacción fallida.
    database_config = request.app.state.database_config
    async with database_config.session_maker() as session:
        await SQLStaffAccessEventRepository(session).append(event)


async def staff_audit(request: Request, staff_user: StaffUserDep):
    """Audit a nivel de router (ADR 0001): 100 % de las requests staff.

    Cobertura 100 % obligatoria: si el write falla en una acción MUTANTE
    (claim/resolve) ⇒ la request falla (no se confirma una acción sin
    rastro). Las lecturas degradan con warning (la respuesta ya se produjo).
    """
    action = _action_for_request(request)
    try:
        yield
    finally:
        try:
            await _write_access_event(request, staff_user, action)
        except Exception as error:  # noqa: BLE001
            logger.exception(
                "staff.audit_write_failed",
                path=str(request.url.path),
                staff_user_id=str(staff_user.uuid),
                action=action,
            )
            if action in _MUTATING_ACTIONS:
                # Acción mutante sin audit ⇒ rechazar (ADR 0001).
                raise StaffAuditWriteError(action) from error
