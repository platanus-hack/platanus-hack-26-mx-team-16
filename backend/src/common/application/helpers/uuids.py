from collections.abc import Callable
from typing import Any

from nanoid import generate
from pydantic import BaseModel
from uuid6 import UUID

from src.common.domain.entities.mixins.common import BaseModelMixin
from src.common.domain.enums.base_enum import BaseEnum


def optional_uuid_string(value: UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)


def optional_enum_string(value: BaseEnum | None) -> str | None:
    if value is None:
        return None
    return str(value)


def optional_string(value: Any | None) -> str | None:
    if value is None:
        return None
    return str(value)


def optional_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(value)


def fallback_string(value: str | None) -> str:
    return value or "---"


def optional_model_uuid(base_model: BaseModelMixin | None) -> UUID | None:
    if base_model is None:
        return None
    return base_model.uuid


def optional_property(base_model: BaseModel | None, property_name: str = "uuid") -> Any:
    if not base_model:
        return None
    return getattr(base_model, property_name, None)


def gen_nano_id(
    namespace: str | None = None,
    size: int = 6,
    validator: Callable[[str], bool] | None = None,
    max_attempts: int = 100,
) -> str:
    alphabet = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    attempts = 0

    while attempts < max_attempts:
        value = generate(alphabet, size=size)
        attempts += 1
        if validator and not validator(value):
            continue
        if namespace:
            return f"{namespace}#{value}"
        return value
    raise ValueError(f"gen_nano_id: MaxAttemptsReached Failed attempts={max_attempts}")
