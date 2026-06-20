from typing import Any, Protocol, TypeVar

TItem = TypeVar("TItem", covariant=True)


class Presenter(Protocol[TItem]):
    def __init__(self, instance: TItem): ...

    @property
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError
