import json
from dataclasses import dataclass


@dataclass
class StreamEvent:
    event_name: str
    data: dict

    def __hash__(self):
        return hash((self.event_name, json.dumps(self.data, sort_keys=True)))

    @property
    def to_dict(self):
        return {
            "event_name": self.event_name,
            "data": self.data,
        }

    @property
    def data_raw(self) -> str:
        return json.dumps(self.data)

    @property
    def to_raw(self):
        return f"event: {self.event_name}\ndata: {self.data}\n\n"

    def __eq__(self, other: "StreamEvent") -> bool:
        return self.event_name == other.event_name and self.data == other.data

    @classmethod
    def from_dict(cls, data: dict) -> "StreamEvent":
        return cls(
            event_name=data["event_name"],
            data=data["data"],
        )
