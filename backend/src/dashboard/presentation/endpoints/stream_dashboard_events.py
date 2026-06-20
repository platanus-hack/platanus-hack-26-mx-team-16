"""SSE endpoint: tenant-scoped dashboard invalidation bus.

This stream NEVER carries dashboard data — only "something changed"
signals. The frontend subscribes once per session and uses each event
to invalidate the TanStack Query cache, triggering a refetch of the
relevant REST endpoint (`/v1/dashboard/overview` or `/processing`).

Ownership is implicit: the authenticated tenant user can only
subscribe to their own tenant's channel (the channel name is built
from `tenant.uuid`); there is no cross-tenant leak risk from the
channel construction.

The stream is open-ended (no `close_after`) and replay-free (no
`since_seq`): on reconnect the frontend just invalidates queries and
gets the current state from REST, which is cheaper than maintaining a
durable event log.
"""

from fastapi import Depends, Request
from sse_starlette.sse import EventSourceResponse

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.dashboard import DashboardPermission
from src.common.infrastructure.dependencies.common import RedisClientDep
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.sse.streaming import stream_sse
from src.dashboard.domain.events import channel_for_dashboard


async def stream_dashboard_events(
    request: Request,
    redis_client: RedisClientDep,
    tenant: Tenant = Depends(get_required_tenant),
    tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> EventSourceResponse:
    # Tenant comes through its own dependency rather than `tenant_user.tenant`
    # to avoid relying on the relationship being eagerly loaded — matches the
    # pattern used by the REST endpoints and `stream_processing_job_events`.
    check_tenant_permission(tenant_user, permissions=[DashboardPermission.view])
    return stream_sse(
        channel=channel_for_dashboard(tenant.uuid),
        redis_client=redis_client,
        request=request,
    )
