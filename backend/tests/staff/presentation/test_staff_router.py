"""E5 · W4: router /staff/v1 — aislamiento bidireccional (criterio ADR 0001),
revocación inmediata, X-Tenant ⇒ 400 y cobertura 100 % del audit.

App ASGI real (httpx) con las dependencias VIVAS (sin overrides): la pared es
la dependencia, no el mock.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from expects import be_none, equal, expect
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.common.database.config import get_database_config
from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.staff_access_event import StaffAccessEventORM
from src.common.database.models.staff_user import StaffUserORM
from src.common.database.models.workspace import WorkflowORM
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.exceptions._base import DomainError
from src.common.infrastructure.error_handlers import domain_error_handler
from src.common.infrastructure.services.jwt_token_builder import JwtTokenBuilder
from src.staff.presentation.dependencies import ROUTE_ACTIONS, action_for_route
from src.staff.presentation.router import staff_router
from tests.staff.conftest import make_l1_task_orm

EXPECTED_ACTIONS = {action for _, _, action in ROUTE_ACTIONS}


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(staff_router, prefix="/staff/v1")

    # Sonda tenant-scoped: la pared del plano tenant ES esta dependencia.
    from src.common.infrastructure.dependencies.tenant import get_required_tenant_user

    async def tenant_probe(tenant_user=Depends(get_required_tenant_user)):
        return {"ok": True}

    app.add_api_route("/v1/tenant-probe", tenant_probe, methods=["GET"])

    app.state.database_config = get_database_config()
    app.state.task_queue = object()
    app.state.temporal_client = object()  # las tareas del test no señalan
    return app


def _token(user_id, *, is_staff: bool = False) -> str:
    extra = {"is_staff": True} if is_staff else None
    return JwtTokenBuilder().create_token(
        sub=str(user_id),
        scope=JwtTokenScope.ACCESS,
        exp_delta=timedelta(minutes=10),
        namespace="USER",
        extra_claims=extra,
    )


def _auth(token: str, **extra_headers) -> dict:
    return {"Authorization": f"Bearer {token}", **extra_headers}


@pytest.fixture
async def app():
    return _build_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def committed(async_session, user_orm, tenant_orm, staff_user_orm):
    """Los requests del app ASGI usan sesiones nuevas: los rows deben estar
    commiteados, no solo flusheados."""
    await async_session.commit()
    return True


def test_every_staff_route_has_an_audit_action():
    for route in staff_router.routes:
        for method in route.methods - {"HEAD", "OPTIONS"}:
            expect(action_for_route(method, route.path)).not_to(be_none)


async def test_tenant_token_without_claim__staff_surface_is_403(
    client, committed, user_orm
):
    # user_orm TIENE fila staff activa, pero el token NO lleva el claim:
    # el gate barato rechaza sin tocar la tabla (doble muro).
    response = await client.get("/staff/v1/tasks", headers=_auth(_token(user_orm.uuid)))

    expect(response.status_code).to(equal(403))
    expect(response.json()["errors"][0]["code"]).to(equal("staff.access_required"))


async def test_revoked_row_with_valid_token__is_403(client, async_session, committed):
    # Token vigente CON claim, fila revocada ⇒ 403 (revocación inmediata).
    from src.common.database.models.user import UserORM

    revoked_user = UserORM(uuid=uuid4(), username=f"revoked-{uuid4().hex[:8]}", password="x")
    async_session.add(revoked_user)
    await async_session.flush()
    async_session.add(
        StaffUserORM(
            uuid=uuid4(), user_id=revoked_user.uuid, role="staff_analyst_l1", status="revoked"
        )
    )
    await async_session.commit()

    response = await client.get(
        "/staff/v1/tasks", headers=_auth(_token(revoked_user.uuid, is_staff=True))
    )

    expect(response.status_code).to(equal(403))
    expect(response.json()["errors"][0]["code"]).to(equal("staff.access_required"))


async def test_x_tenant_header_on_staff_surface__is_400(client, committed, user_orm, tenant_orm):
    response = await client.get(
        "/staff/v1/tasks",
        headers=_auth(_token(user_orm.uuid, is_staff=True), **{"X-Tenant": tenant_orm.slug}),
    )

    expect(response.status_code).to(equal(400))
    expect(response.json()["errors"][0]["code"]).to(equal("staff.x_tenant_forbidden"))


async def test_staff_token_without_tenant_user__tenant_endpoint_is_403(
    client, committed, user_orm, tenant_orm
):
    # Sentido inverso del doble muro: identidad staff NO satisface el plano
    # tenant (no hay TenantUser) ⇒ 403, aunque el token sea válido.
    response = await client.get(
        "/v1/tenant-probe",
        headers=_auth(_token(user_orm.uuid, is_staff=True), **{"X-Tenant": tenant_orm.slug}),
    )

    expect(response.status_code).to(equal(403))


async def test_full_surface__works_and_audits_every_route(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm
):
    # Datos: una tarea L1 y un caso del tenant A (cross-tenant para staff).
    # La tarea L1 DEBE estar ligada al caso (gate de PII cross-tenant C6):
    # el staff solo puede leer un caso con una tarea L1 servible asociada.
    case_id = uuid4()
    task = make_l1_task_orm(tenant_orm.uuid, case_id=case_id)
    workflow = WorkflowORM(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, name="WF"
    )
    async_session.add_all([task, workflow])
    await async_session.flush()  # el caso necesita el workflow ya insertado (FK)
    case = WorkflowCaseORM(
        uuid=case_id, tenant_id=tenant_orm.uuid, workflow_id=workflow.uuid, name="Caso 1"
    )
    async_session.add(case)
    await async_session.commit()

    headers = _auth(_token(user_orm.uuid, is_staff=True))

    # 1) Cola unificada (con contexto de tenant en cada item).
    listed = await client.get("/staff/v1/tasks", headers=headers)
    expect(listed.status_code).to(equal(200))
    items = listed.json()["data"]
    mine = next(i for i in items if i["uuid"] == str(task.uuid))
    expect(mine["tenantName"]).to(equal(tenant_orm.name))
    expect(mine["stage"]).to(equal("review_l1"))

    # 2) Claim → claimed_by=staff:<uuid>; claim rival ⇒ 409 con holder.
    claimed = await client.post(f"/staff/v1/tasks/{task.uuid}/claim", headers=headers, json={})
    expect(claimed.status_code).to(equal(200))
    expect(claimed.json()["data"]["claimedBy"]).to(equal(f"staff:{staff_user_orm.uuid}"))

    # 3) Resolve (auto re-claim del mismo holder) ⇒ resolved + resolvedBy.
    resolved = await client.post(
        f"/staff/v1/tasks/{task.uuid}/resolve",
        headers=headers,
        json={"resolution": {"approved": True}},
    )
    expect(resolved.status_code).to(equal(200))
    expect(resolved.json()["data"]["status"]).to(equal("resolved"))

    # 4) Caso read-only cross-tenant (tenant del recurso, no de un header).
    case_view = await client.get(f"/staff/v1/cases/{case.uuid}", headers=headers)
    expect(case_view.status_code).to(equal(200))
    expect(case_view.json()["data"]["tenantName"]).to(equal(tenant_orm.name))
    expect(case_view.json()["data"]["readOnly"]).to(equal(True))

    # 5) Audit: analista ⇒ 403 (igual queda auditado); el caso 200 se prueba aparte.
    audit_denied = await client.get("/staff/v1/audit", headers=headers)
    expect(audit_denied.status_code).to(equal(403))
    expect(audit_denied.json()["errors"][0]["code"]).to(equal("staff.admin_required"))

    # 6) E6 §3.5: métricas QA ⇒ 403 para analista (staff_admin only) pero
    # igual queda auditado (metrics.view).
    metrics_denied = await client.get("/staff/v1/metrics", headers=headers)
    expect(metrics_denied.status_code).to(equal(403))
    expect(metrics_denied.json()["errors"][0]["code"]).to(equal("staff.admin_required"))

    # Cobertura del audit: TODAS las rutas produjeron su acción (100 %).
    rows = (
        (
            await async_session.execute(
                select(StaffAccessEventORM).where(
                    StaffAccessEventORM.staff_user_id == staff_user_orm.uuid
                )
            )
        )
        .scalars()
        .all()
    )
    actions = {row.action for row in rows}
    expect(actions.issuperset(EXPECTED_ACTIONS)).to(equal(True))
    # Y las acciones con recurso quedaron atribuidas al tenant del recurso.
    claim_events = [r for r in rows if r.action == "tasks.claim"]
    expect(claim_events[0].tenant_id).to(equal(tenant_orm.uuid))
    expect(claim_events[0].task_id).to(equal(task.uuid))


async def test_case_view__without_linked_l1_task_is_404(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm
):
    # C6 [CRÍTICO]: un caso de OTRO tenant SIN tarea L1 ligada ⇒ 404.
    # Es la fuga de PII cross-tenant que el gate cierra: existir no basta,
    # debe haber una tarea L1 servible asociada.
    workflow = WorkflowORM(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, name="WF"
    )
    async_session.add(workflow)
    await async_session.flush()
    orphan_case = WorkflowCaseORM(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, workflow_id=workflow.uuid, name="Sin tarea L1"
    )
    async_session.add(orphan_case)
    await async_session.commit()

    headers = _auth(_token(user_orm.uuid, is_staff=True))
    response = await client.get(f"/staff/v1/cases/{orphan_case.uuid}", headers=headers)

    expect(response.status_code).to(equal(404))
    expect(response.json()["errors"][0]["code"]).to(equal("staff.case_not_found"))


async def test_case_view__with_linked_l1_task_is_200(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm
):
    # Contrapartida del aislamiento: con tarea L1 ligada ⇒ 200 (lectura legítima).
    case_id = uuid4()
    task = make_l1_task_orm(tenant_orm.uuid, case_id=case_id)
    workflow = WorkflowORM(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, name="WF"
    )
    async_session.add_all([task, workflow])
    await async_session.flush()
    case = WorkflowCaseORM(
        uuid=case_id, tenant_id=tenant_orm.uuid, workflow_id=workflow.uuid, name="Con tarea L1"
    )
    async_session.add(case)
    await async_session.commit()

    headers = _auth(_token(user_orm.uuid, is_staff=True))
    response = await client.get(f"/staff/v1/cases/{case.uuid}", headers=headers)

    expect(response.status_code).to(equal(200))
    expect(response.json()["data"]["tenantName"]).to(equal(tenant_orm.name))


async def test_claim__audit_write_failure_fails_the_request(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm, monkeypatch
):
    # Menor (dependencies.py:127): el audit de una acción MUTANTE no puede
    # fallar en silencio — claim sin rastro ⇒ la request falla (ADR 0001).
    case_id = uuid4()
    task = make_l1_task_orm(tenant_orm.uuid, case_id=case_id)
    async_session.add(task)
    await async_session.commit()

    async def _boom(self, event):  # noqa: ANN001
        raise RuntimeError("audit DB down")

    monkeypatch.setattr(
        "src.staff.infrastructure.repositories.sql_staff_access_event."
        "SQLStaffAccessEventRepository.append",
        _boom,
    )

    headers = _auth(_token(user_orm.uuid, is_staff=True))
    response = await client.post(f"/staff/v1/tasks/{task.uuid}/claim", headers=headers, json={})

    expect(response.status_code).to(equal(500))
    expect(response.json()["errors"][0]["code"]).to(equal("staff.audit_write_failed"))


async def test_list__audit_write_failure_degrades_gracefully(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm, monkeypatch
):
    # Contrapartida: una LECTURA (tasks.list) degrada con warning — la
    # respuesta ya producida no se rompe por un fallo de audit.
    async def _boom(self, event):  # noqa: ANN001
        raise RuntimeError("audit DB down")

    monkeypatch.setattr(
        "src.staff.infrastructure.repositories.sql_staff_access_event."
        "SQLStaffAccessEventRepository.append",
        _boom,
    )

    headers = _auth(_token(user_orm.uuid, is_staff=True))
    response = await client.get("/staff/v1/tasks", headers=headers)

    expect(response.status_code).to(equal(200))


async def test_audit__records_x_forwarded_for_first_hop(
    client, async_session, committed, user_orm, tenant_orm, staff_user_orm
):
    # Menor (dependencies.py:106): tras un proxy, la IP real es el PRIMER hop
    # de X-Forwarded-For, no request.client.host.
    headers = _auth(
        _token(user_orm.uuid, is_staff=True),
        **{"X-Forwarded-For": "203.0.113.7, 10.0.0.1, 127.0.0.1"},
    )
    response = await client.get("/staff/v1/tasks", headers=headers)
    expect(response.status_code).to(equal(200))

    rows = (
        (
            await async_session.execute(
                select(StaffAccessEventORM).where(
                    StaffAccessEventORM.staff_user_id == staff_user_orm.uuid,
                    StaffAccessEventORM.action == "tasks.list",
                )
            )
        )
        .scalars()
        .all()
    )
    expect(rows[0].ip).to(equal("203.0.113.7"))


async def test_audit_endpoint__staff_admin_reads_events(
    client, async_session, committed
):
    from src.common.database.models.user import UserORM

    admin_user = UserORM(uuid=uuid4(), username=f"admin-{uuid4().hex[:8]}", password="x")
    async_session.add(admin_user)
    await async_session.flush()
    admin_staff = StaffUserORM(
        uuid=uuid4(), user_id=admin_user.uuid, role="staff_admin", status="active"
    )
    async_session.add(admin_staff)
    await async_session.commit()

    headers = _auth(_token(admin_user.uuid, is_staff=True))
    listing = await client.get("/staff/v1/tasks", headers=headers)  # genera un evento propio
    expect(listing.status_code).to(equal(200))

    audit = await client.get(f"/staff/v1/audit?staff_user_id={admin_staff.uuid}", headers=headers)

    expect(audit.status_code).to(equal(200))
    events = audit.json()["data"]
    expect({e["action"] for e in events}.issuperset({"tasks.list"})).to(equal(True))
    expect(events[0]["staffUserId"]).to(equal(str(admin_staff.uuid)))


async def test_metrics_endpoint__staff_admin_reads_qa_metrics(client, async_session, committed):
    # E6 §3.5: el dashboard QA es staff_admin only y devuelve el shape de cortes.
    from src.common.database.models.user import UserORM

    admin_user = UserORM(uuid=uuid4(), username=f"admin-{uuid4().hex[:8]}", password="x")
    async_session.add(admin_user)
    await async_session.flush()
    admin_staff = StaffUserORM(
        uuid=uuid4(), user_id=admin_user.uuid, role="staff_admin", status="active"
    )
    async_session.add(admin_staff)
    await async_session.commit()

    headers = _auth(_token(admin_user.uuid, is_staff=True))
    metrics = await client.get("/staff/v1/metrics", headers=headers)

    expect(metrics.status_code).to(equal(200))
    body = metrics.json()["data"]
    # camelCase en el wire + cortes presentes (vacíos si no hay eventos).
    expect("totals" in body).to(equal(True))
    expect("byTenant" in body).to(equal(True))
    expect("byActor" in body).to(equal(True))
