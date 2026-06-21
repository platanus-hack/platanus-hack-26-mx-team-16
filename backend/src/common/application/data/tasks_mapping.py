from src.common.application.commands.common import (
    ExampleJobCommand,
    SendEmailCommand,
)
from src.common.application.commands.tenants import SoftDeleteTenantCommand
from src.common.application.commands.users import MergeTenantsCommand
from src.common.domain.buses.commands import Command
from src.scans.application.commands.run_scan import RunScanCommand

# Commands that may be enqueued onto the SAQ queue and resolved by the worker
# (config/tasks.py -> AsyncTaskResolver). Each MUST have a handler subscribed on
# the command bus (see each module's infrastructure/bus_wiring.py), or the worker
# raises NotRegisteredCommand when it picks the job up.
async_tasks_mapping: dict[str, type[Command]] = {
    SendEmailCommand.__name__: SendEmailCommand,
    MergeTenantsCommand.__name__: MergeTenantsCommand,
    SoftDeleteTenantCommand.__name__: SoftDeleteTenantCommand,
    # Reference background job (boilerplate D3).
    ExampleJobCommand.__name__: ExampleJobCommand,
    # Pentest worker job (05-agent-team) — dispatched by POST /scans (12) and the
    # monitor cron (08); executed by RunScanHandler in the SAQ worker.
    RunScanCommand.__name__: RunScanCommand,
}
