"""Router-level guard enforcing per-workflow access (workflow permissions).

Attached to every router whose routes are nested under ``/workflows/{workflow_id}``.
Routes without a ``workflow_id`` path param (list / create) are a no-op. Private
workflows are restricted to the tenant owner, the creator and explicit members;
everyone else gets a 403 here before the endpoint runs.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.workflow_actions import (
    WorkflowAction,
    WorkflowActionForbiddenError,
    workflow_role_allows,
)
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.workflows.application.workflow_members.role_resolver import (
    ResolveWorkflowRole,
    is_tenant_admin,
)
from src.workflows.application.workflow_members.use_cases import EnsureWorkflowAccess


async def verify_workflow_access(
    request: Request,
    app_context: Annotated[AppContext, Depends(get_app_context)],
    tenant: Annotated[Tenant, Depends(get_required_tenant)],
    current_tenant_user: Annotated[TenantUser, Depends(get_required_tenant_user)],
) -> None:
    raw_workflow_id = request.path_params.get("workflow_id")
    if raw_workflow_id is None:
        return
    try:
        workflow_id = UUID(str(raw_workflow_id))
    except (ValueError, TypeError):
        return

    await EnsureWorkflowAccess(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        tenant_user=current_tenant_user,
        workflow_repository=app_context.domain.workflow_repository,
        member_repository=app_context.domain.workflow_member_repository,
    ).execute()


def require_workflow_action(action: WorkflowAction):
    """Guard por ruta de la matriz rol×acción (E5 · diseño §5).

    Resuelve el rol efectivo del usuario sobre el workflow del path y exige que
    la matriz ``WORKFLOW_ROLE_ACTIONS`` permita ``action``. SIN bypass
    ``PERMISSIONS_ENABLED``. Resolución del workflow:

    - ``workflow_id`` en el path ⇒ directo.
    - solo ``rule_id`` (router standalone ``/workflow-rules``) ⇒ se carga la
      regla para conocer su workflow (regla inexistente ⇒ el handler 404ea).
    - solo ``run_id`` (router standalone ``/workflow-analysis-runs``) ⇒ se carga
      el run para conocer su workflow (run inexistente ⇒ el handler 404ea); cierra
      la fuga cross-workflow de cancel/force-cancel/lecturas por ``run_id``.
    - sin contexto de workflow (p. ej. publish de ``/pipelines``, superficie
      tenant-level) ⇒ exige tenant owner/admin.
    """

    async def _dependency(
        request: Request,
        app_context: Annotated[AppContext, Depends(get_app_context)],
        tenant: Annotated[Tenant, Depends(get_required_tenant)],
        current_tenant_user: Annotated[TenantUser, Depends(get_required_tenant_user)],
    ) -> None:
        workflow_id = _path_uuid(request, "workflow_id")
        if workflow_id is None:
            rule_id = _path_uuid(request, "rule_id")
            run_id = _path_uuid(request, "run_id")
            if rule_id is not None:
                rule = await app_context.domain.workflow_rule_repository.find_by_id(
                    rule_id, tenant.uuid
                )
                if rule is None:
                    return  # el handler responde 404; nada que autorizar
                workflow_id = rule.workflow_id
            elif run_id is not None:
                run = await app_context.domain.workflow_analysis_run_repository.find_by_id(
                    run_id, tenant.uuid
                )
                if run is None:
                    return  # el handler responde 404; nada que autorizar
                workflow_id = run.workflow_id
            else:
                # Superficie tenant-level (pipelines publish): owner/admin.
                if is_tenant_admin(current_tenant_user):
                    return
                raise WorkflowActionForbiddenError(action)

        role = await ResolveWorkflowRole(
            workflow_id=workflow_id,
            tenant_id=tenant.uuid,
            tenant_user=current_tenant_user,
            workflow_repository=app_context.domain.workflow_repository,
            member_repository=app_context.domain.workflow_member_repository,
        ).execute()
        if not workflow_role_allows(role, action):
            raise WorkflowActionForbiddenError(action, str(workflow_id), role)

    _dependency.__name__ = f"require_workflow_{action}"
    return _dependency


def _path_uuid(request: Request, param: str) -> UUID | None:
    raw = request.path_params.get(param)
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None
