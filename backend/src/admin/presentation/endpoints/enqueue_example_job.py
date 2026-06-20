"""Reference endpoint for the example background job (boilerplate D3).

POST /v1/jobs/example enqueues an :class:`ExampleJobCommand` onto the SAQ
queue and returns 202 Accepted. The job runs later in the SAQ worker process
(`saq config.tasks.worker_settings`). This is the canonical, copy-me example
of the async-command pattern — mirror it for any new background job.
"""

from fastapi import status

from src.common.application.commands.common import ExampleJobCommand
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import BusContextDep
from src.common.infrastructure.dependencies.session import AuthenticatedUserDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class ExampleJobRequest(CamelCaseRequest):
    message: str = "hello from the example job"


async def enqueue_example_job(
    request: ExampleJobRequest,
    bus_context: BusContextDep,
    current_user: AuthenticatedUserDep,
) -> ApiJSONResponse:
    # run_async=True hands the command to the SaqCommandEnqueuer instead of
    # executing it inline, so the request returns immediately.
    _: User = current_user
    await bus_context.command_bus.dispatch(
        ExampleJobCommand(message=request.message),
        run_async=True,
    )

    return ApiJSONResponse(
        content={"accepted": True},
        status_code=status.HTTP_202_ACCEPTED,
    )
