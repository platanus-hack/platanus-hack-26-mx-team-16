"""Matriz rol×acción por workflow (E5 · diseño §5).

Permission-based (decisión Vic): el código chequea LA ACCIÓN, jamás el nombre
del rol — cambiar qué rol puede aprobar = editar esta matriz, no el código.

Acciones:
- ``view``    — ver el workflow y sus casos.
- ``operate`` — docs, ready, clarificaciones, editar campos, correr análisis.
- ``approve`` — resolver APPROVAL L2 / cierre.
- ``manage``  — members, pipelines, reglas, destinos, policies.

SIN bypass ``PERMISSIONS_ENABLED`` (ese flag solo cubre el catálogo tenant
legacy; esta matriz se aplica siempre).
"""

from __future__ import annotations

from typing import Literal

from src.common.domain.exceptions._base import DomainError

WorkflowAction = Literal["view", "operate", "approve", "manage"]

WORKFLOW_ROLE_ACTIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"view"}),
    "member": frozenset({"view", "operate"}),
    "admin": frozenset({"view", "operate", "approve", "manage"}),
}


def workflow_role_allows(role: str | None, action: WorkflowAction) -> bool:
    """``role`` None = sin acceso (private sin fila): toda acción denegada."""
    if role is None:
        return False
    return action in WORKFLOW_ROLE_ACTIONS.get(role, frozenset())


class WorkflowActionForbiddenError(DomainError):
    def __init__(self, action: str, workflow_id: str = "", role: str | None = None):
        super().__init__(
            code="workflow.action_forbidden",
            message=f"Your workflow role does not allow '{action}' on this workflow.",
            status_code=403,
            context={"action": action, "workflow_id": workflow_id, "role": role},
        )
