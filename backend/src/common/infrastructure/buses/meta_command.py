from dataclasses import dataclass
from typing import Any

from src.common.domain.buses.commands import Command


@dataclass
class MetaCommand:
    command_name: str
    payload: dict[str:Any]

    @property
    def to_dict(self) -> dict:
        return {
            "command_name": self.command_name,
            "payload": self.payload,
        }

    @classmethod
    def from_command(cls, command: Command) -> "MetaCommand":
        return cls(
            command_name=command.__class__.__name__,
            payload=command.to_dict,
        )

    @classmethod
    def from_dict(cls, kwargs: dict) -> "MetaCommand":
        return cls(**kwargs)
