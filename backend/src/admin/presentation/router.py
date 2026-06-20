from fastapi import APIRouter

from src.admin.presentation.endpoints.enqueue_example_job import enqueue_example_job
from src.admin.presentation.endpoints.set_user_password import set_user_password

tasks_router = router = APIRouter(tags=["tasks"])


tasks_router.add_api_route(
    path="/admin/users/set-password",
    endpoint=set_user_password,
    methods=["POST"],
)

# Reference background job (boilerplate D3): enqueues an ExampleJobCommand.
tasks_router.add_api_route(
    path="/jobs/example",
    endpoint=enqueue_example_job,
    methods=["POST"],
)
