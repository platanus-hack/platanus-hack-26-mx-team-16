"""Errores del plano staff (ADR 0001). Importan ``DomainError`` del base."""

from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class StaffAccessRequiredError(DomainError):
    """Claim ausente O fila staff no activa: ambas paredes son la misma 403
    (no filtrar cuál falló — el claim solo gatea, nunca autoriza)."""

    def __init__(self, context: dict | None = None):
        super().__init__(
            code="staff.access_required",
            message="Staff access required",
            status_code=status.HTTP_403_FORBIDDEN,
            context=context,
        )


class StaffAdminRequiredError(DomainError):
    def __init__(self, context: dict | None = None):
        super().__init__(
            code="staff.admin_required",
            message="Staff admin role required",
            status_code=status.HTTP_403_FORBIDDEN,
            context=context,
        )


class StaffTenantHeaderError(DomainError):
    """`X-Tenant` no aplica en `/staff/v1/*` (ADR 0001 · aislamiento)."""

    def __init__(self):
        super().__init__(
            code="staff.x_tenant_forbidden",
            message="X-Tenant header is not allowed on the staff surface",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class StaffTaskNotFoundError(DomainError):
    """No existe O no es una tarea del alcance staff (stage review_l1 +
    INTERNAL_QUEUE): mismo 404 — el alcance no se enumera."""

    def __init__(self, task_id: str):
        super().__init__(
            code="staff.task_not_found",
            message="Human task not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context={"task_id": task_id},
        )


class StaffCaseNotFoundError(DomainError):
    def __init__(self, case_id: str):
        super().__init__(
            code="staff.case_not_found",
            message="Case not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context={"case_id": case_id},
        )


class StaffTaskClaimConflictError(DomainError):
    """Lock pesimista (diseño §3.2): la tarea está reclamada por otro actor."""

    def __init__(self, task_id: str, holder: str | None = None):
        super().__init__(
            code="human_task.already_claimed",
            message="The task is claimed by another actor",
            status_code=status.HTTP_409_CONFLICT,
            context={"task_id": task_id, "holder": holder},
        )


class StaffAuditWriteError(DomainError):
    """El audit de una acción mutante (claim/resolve) no se pudo escribir.

    El ADR 0001 exige cobertura 100 % del audit: una acción mutante que no
    deja rastro NO puede confirmarse ⇒ la request falla (las lecturas, en
    cambio, degradan con warning)."""

    def __init__(self, action: str | None = None):
        super().__init__(
            code="staff.audit_write_failed",
            message="The staff action could not be audited and was rejected",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context={"action": action},
        )


class StaffTaskNotClaimableError(DomainError):
    """La tarea ya no está pendiente (resuelta/expirada): no se puede reclamar."""

    def __init__(self, task_id: str, task_status: str):
        super().__init__(
            code="human_task.not_claimable",
            message="The task is no longer pending",
            status_code=status.HTTP_409_CONFLICT,
            context={"task_id": task_id, "status": task_status},
        )
