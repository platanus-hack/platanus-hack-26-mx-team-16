"""Generic Temporal activity that publishes a ProcessingJobEvent to Redis Pub/Sub.

Lives in `common` so any workflow in the project can register the same
class. The activity wraps :class:`RedisEventPublisher` and exists as an
activity (not a workflow-side function) for two reasons:

1. Activities can run real I/O. The workflow code itself runs in the
   deterministic sandbox and cannot do network calls.
2. Temporal retries failed activities transparently — if Redis blips for
   a couple of seconds the publish recovers automatically without
   poisoning the workflow.
"""

from __future__ import annotations

from temporalio import activity

from src.common.infrastructure.event_publisher import RedisEventPublisher
from src.workflows.domain.events import ProcessingJobEvent


class PublishProcessingJobEventActivity:
    def __init__(self, event_publisher: RedisEventPublisher) -> None:
        self._event_publisher = event_publisher

    @activity.defn(name="publish_processing_job_event")
    async def publish_processing_job_event(self, event: ProcessingJobEvent) -> None:
        # Temporal's `pydantic_data_converter` already validates the activity
        # input as `ProcessingJobEvent` on deserialization — no need to revalidate.
        await self._event_publisher.publish(event)
