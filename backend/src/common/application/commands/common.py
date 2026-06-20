from dataclasses import asdict, dataclass
from typing import Any

from src.common.domain.buses.commands import Command
from src.common.domain.entities.common.stream_event import StreamEvent


@dataclass
class SendEmailCommand(Command):
    to_emails: list[str]
    template_name: str
    context: dict[str, Any] | None = None
    from_email: str | None = None
    subject: str | None = None

    @property
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict) -> "SendEmailCommand":
        return cls(**kwargs)


@dataclass
class ExampleJobCommand(Command):
    """Reference async job (boilerplate D3).

    Demonstrates the full SAQ background-job pattern end-to-end:
    endpoint -> command_bus.dispatch(run_async=True) -> SaqCommandEnqueuer
    -> SAQ queue -> worker handle_command -> AsyncTaskResolver
    -> async_tasks_mapping -> command_bus.dispatch (sync) -> ExampleJobHandler.

    Keep this tiny; it exists only as the copy-me template for new jobs.
    """

    message: str

    @property
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict) -> "ExampleJobCommand":
        return cls(**kwargs)


@dataclass
class PublishStreamEventCommand(Command):
    channel_id: str
    stream_event: StreamEvent

    @property
    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "stream_event": self.stream_event.to_dict,
        }

    @classmethod
    def from_dict(cls, kwargs: dict) -> "PublishStreamEventCommand":
        return cls(
            channel_id=kwargs["channel_id"],
            stream_event=StreamEvent.from_dict(kwargs["stream_event"]),
        )
