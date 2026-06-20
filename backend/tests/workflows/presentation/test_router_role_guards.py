"""E5 · §5 — guards de roles por workflow a nivel router (cluster D del review).

Dos frentes:

1. **Matriz rol×acción** ejercitando el guard real ``require_workflow_action``
   contra repos autospec: viewer ⇒ 403 en operate/manage; member ⇒ 403 en
   manage; admin ⇒ 200. Incluye la resolución del workflow desde ``run_id`` y
   ``rule_id`` (cierra la fuga cross-workflow de los routers standalone).
2. **Introspección del router real**: cada ruta mutadora declara el
   ``require_workflow_*`` esperado en ``dependencies`` (regresión: si alguien
   añade una mutación sin gate, el test la atrapa).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec
from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.workflow_actions import WorkflowActionForbiddenError
from src.common.infrastructure.dependencies.workflow_access import require_workflow_action
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.presentation import router as router_module

WORKFLOW_ID = uuid4()
TENANT_ID = uuid4()
RULE_ID = uuid4()
RUN_ID = uuid4()


def _request(path_params: dict) -> MagicMock:
    req = MagicMock()
    req.path_params = path_params
    return req


def _tenant() -> SimpleNamespace:
    return SimpleNamespace(uuid=TENANT_ID)


def _tenant_user(role: str | None) -> MagicMock:
    """Tenant user cuyo rol efectivo sobre el workflow será ``role``.

    Modelamos al usuario como miembro explícito con ``role`` (no owner, sin rol
    tenant admin) salvo ``admin``, que resolvemos vía owner del tenant.
    """
    user = MagicMock(spec=TenantUser)
    user.user_id = uuid4()
    user.is_owner = role == "admin"
    user.tenant_role = None
    return user, role


def _member(role: str | None):
    if role in (None, "admin"):
        return None
    return SimpleNamespace(role=role)


def _app_context(*, workflow=None, member=None, rule=None, run=None) -> MagicMock:
    workflow_repo = create_autospec(spec=WorkflowRepository, spec_set=True, instance=True)
    member_repo = create_autospec(spec=WorkflowMemberRepository, spec_set=True, instance=True)
    rule_repo = create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)
    run_repo = create_autospec(spec=WorkflowAnalysisRunRepository, spec_set=True, instance=True)

    workflow_repo.find_by_id = AsyncMock(return_value=workflow)
    member_repo.find = AsyncMock(return_value=member)
    rule_repo.find_by_id = AsyncMock(return_value=rule)
    run_repo.find_by_id = AsyncMock(return_value=run)

    domain = SimpleNamespace(
        workflow_repository=workflow_repo,
        workflow_member_repository=member_repo,
        workflow_rule_repository=rule_repo,
        workflow_analysis_run_repository=run_repo,
    )
    return SimpleNamespace(domain=domain)


def _workflow(access_type: str = "organization", created_by=None) -> Workflow:
    return Workflow(
        uuid=WORKFLOW_ID,
        tenant_id=TENANT_ID,
        name="WF",
        access_type=access_type,
        created_by_id=created_by,
    )


async def _run_guard(action: str, *, path_params, **ctx_kwargs):
    user, _ = ctx_kwargs.pop("user")
    dep = require_workflow_action(action)
    ctx = _app_context(**ctx_kwargs)
    return await dep(
        request=_request(path_params),
        app_context=ctx,
        tenant=_tenant(),
        current_tenant_user=user,
    )


# --- 1. Matriz rol×acción (workflow_id en el path) ---------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "action", "forbidden"),
    [
        ("viewer", "view", False),
        ("viewer", "operate", True),
        ("viewer", "manage", True),
        ("member", "view", False),
        ("member", "operate", False),
        ("member", "manage", True),
        ("admin", "view", False),
        ("admin", "operate", False),
        ("admin", "approve", False),
        ("admin", "manage", False),
        (None, "view", True),
    ],
)
async def test_role_matrix_enforced(role, action, forbidden):
    user = _tenant_user(role)
    access_type = "private" if role is None else "organization"

    async def _call():
        return await _run_guard(
            action,
            path_params={"workflow_id": str(WORKFLOW_ID)},
            user=user,
            workflow=_workflow(access_type=access_type),
            member=_member(role),
        )

    if forbidden:
        with pytest.raises(WorkflowActionForbiddenError):
            await _call()
    else:
        expect(await _call()).to(be_none)


# --- 2. Resolución cross-workflow por run_id (router analysis-runs) -----------


@pytest.mark.asyncio
async def test_run_id_resolves_workflow_and_blocks_viewer():
    """Un viewer del workflow dueño del run ⇒ 403 en operate (cancel)."""
    user = _tenant_user("viewer")
    run = SimpleNamespace(workflow_id=WORKFLOW_ID)

    with pytest.raises(WorkflowActionForbiddenError):
        await _run_guard(
            "operate",
            path_params={"run_id": str(RUN_ID)},
            user=user,
            workflow=_workflow(),
            member=_member("viewer"),
            run=run,
        )


@pytest.mark.asyncio
async def test_run_id_resolves_workflow_and_allows_admin():
    user = _tenant_user("admin")
    run = SimpleNamespace(workflow_id=WORKFLOW_ID)
    result = await _run_guard(
        "operate",
        path_params={"run_id": str(RUN_ID)},
        user=user,
        workflow=_workflow(),
        member=None,
        run=run,
    )
    expect(result).to(be_none)


@pytest.mark.asyncio
async def test_unknown_run_id_defers_to_handler_404():
    """Run inexistente ⇒ no autoriza nada (el handler responde 404)."""
    user = _tenant_user("viewer")
    result = await _run_guard(
        "view",
        path_params={"run_id": str(RUN_ID)},
        user=user,
        workflow=_workflow(),
        run=None,
    )
    expect(result).to(be_none)


# --- 3. Resolución cross-workflow por rule_id (router workflow-rules) ---------


@pytest.mark.asyncio
async def test_rule_id_resolves_workflow_and_blocks_member_on_manage():
    user = _tenant_user("member")
    rule = SimpleNamespace(workflow_id=WORKFLOW_ID)

    with pytest.raises(WorkflowActionForbiddenError):
        await _run_guard(
            "manage",
            path_params={"rule_id": str(RULE_ID)},
            user=user,
            workflow=_workflow(),
            member=_member("member"),
            rule=rule,
        )


# --- 4. Sin contexto de workflow ⇒ exige tenant admin ------------------------


@pytest.mark.asyncio
async def test_no_workflow_context_requires_tenant_admin():
    non_admin = _tenant_user("member")
    with pytest.raises(WorkflowActionForbiddenError):
        await _run_guard("manage", path_params={}, user=non_admin)

    admin = _tenant_user("admin")
    expect(await _run_guard("manage", path_params={}, user=admin)).to(be_none)


# --- 5. Introspección: cada ruta mutadora declara su guard -------------------


def _guard_names(route) -> set[str]:
    names = set()
    for dep in getattr(route, "dependencies", []) or []:
        call = getattr(dep, "dependency", None)
        if call is not None and getattr(call, "__name__", "").startswith("require_workflow_"):
            names.add(call.__name__)
    return names


def _find_route(router, path: str, method: str):
    for route in router.routes:
        if route.path == path and method in getattr(route, "methods", set()):
            return route
    raise AssertionError(f"route not found: {method} {path}")


# (path, method, expected guard) — cubre C7/C8/C9 + menores.
_EXPECTED_GUARDS = [
    ("/workflows/{workflow_id}", "PUT", "require_workflow_manage"),
    ("/workflows/{workflow_id}", "DELETE", "require_workflow_manage"),
    ("/workflows/{workflow_id}/output-schema", "PUT", "require_workflow_manage"),
    ("/workflows/{workflow_id}/webhook-secret", "POST", "require_workflow_manage"),
    ("/workflows/{workflow_id}/documents", "POST", "require_workflow_operate"),
    ("/workflows/{workflow_id}/documents/{document_id}", "PUT", "require_workflow_operate"),
    ("/workflows/{workflow_id}/documents/{document_id}", "DELETE", "require_workflow_operate"),
    ("/workflows/{workflow_id}/cases/{case_id}/documents", "POST", "require_workflow_operate"),
    (
        "/workflows/{workflow_id}/cases/{case_id}/documents/{document_id}",
        "PUT",
        "require_workflow_operate",
    ),
    (
        "/workflows/{workflow_id}/cases/{case_id}/documents/{document_id}",
        "DELETE",
        "require_workflow_operate",
    ),
    ("/workflows/{workflow_id}/jobs", "POST", "require_workflow_operate"),
    ("/workflows/{workflow_id}/jobs/{processing_job_id}", "DELETE", "require_workflow_operate"),
    (
        "/workflows/{workflow_id}/cases/{case_id}/jobs/re-extract",
        "POST",
        "require_workflow_operate",
    ),
    (
        "/workflows/{workflow_id}/cases/{case_id}/workflow-analysis-runs",
        "POST",
        "require_workflow_operate",
    ),
]


@pytest.mark.parametrize(("path", "method", "guard"), _EXPECTED_GUARDS)
def test_workflows_router_route_has_guard(path, method, guard):
    route = _find_route(router_module.workflows_router, path, method)
    expect(_guard_names(route)).to(equal({guard}))


def test_case_extraction_router_start_extract_has_operate_guard():
    route = _find_route(
        router_module.case_extraction_router,
        "/workflows/{workflow_id}/cases/{case_id}/documents/{document_id}/extract",
        "POST",
    )
    expect(_guard_names(route)).to(equal({"require_workflow_operate"}))


_ANALYSIS_RUN_GUARDS = [
    ("/workflow-analysis-runs/{run_id}", "GET", "require_workflow_view"),
    ("/workflow-analysis-runs/{run_id}/cancel", "POST", "require_workflow_operate"),
    ("/workflow-analysis-runs/{run_id}/force-cancel", "POST", "require_workflow_operate"),
    ("/workflow-analysis-runs/{run_id}/summary/resynthesize", "POST", "require_workflow_operate"),
]


@pytest.mark.parametrize(("path", "method", "guard"), _ANALYSIS_RUN_GUARDS)
def test_analysis_runs_router_route_has_guard(path, method, guard):
    route = _find_route(router_module.workflow_analysis_runs_router, path, method)
    expect(_guard_names(route)).to(equal({guard}))
