from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import ENCODERS_BY_TYPE, jsonable_encoder
from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class RawJson:
    """Marker that disables camelCase key conversion for the wrapped value.

    Wrap JSONB-style fields whose keys are domain data (slugs, user-defined
    field names, LLM output, schema definitions). The wrapped value is
    embedded verbatim in the JSON response — keys are not transformed.

    Example:
        return {"output_schema": RawJson(self.instance.output_schema)}
    """

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value


# Tell FastAPI's jsonable_encoder to leave RawJson alone when it walks a
# response payload. Without this entry it falls through to vars(obj), which
# raises on __slots__-only classes. convert_to_camel_case strips the wrapper
# at render time.
ENCODERS_BY_TYPE[RawJson] = lambda raw: raw


def convert_to_camel_case(data: Any) -> Any:
    """Recursively convert dictionary keys to camelCase and normalize values
    to JSON-compatible primitives.

    The single source of truth for response serialization:
    - dict keys → camelCase, recursing into values.
    - list items → recursed.
    - BaseModel → model_dump(by_alias=True) and recursed.
    - RawJson → unwrapped, value embedded as-is (no key transform).
    - UUID / datetime / date → ISO/str string.
    - Decimal → float.
    - Primitives → as-is.
    - Anything else → delegate to FastAPI's jsonable_encoder (covers Enum,
      non-Pydantic dataclasses, PurePath, set/tuple/frozenset, etc.) and
      recurse on the result.
    """
    if isinstance(data, RawJson):
        return data.value
    if isinstance(data, dict):
        return {to_camel(key): convert_to_camel_case(value) for key, value in data.items()}
    if isinstance(data, list):
        return [convert_to_camel_case(item) for item in data]
    if isinstance(data, BaseModel):
        return convert_to_camel_case(data.model_dump(by_alias=True))
    if isinstance(data, str | int | float | bool | type(None)):
        return data
    if isinstance(data, datetime | date):
        return data.isoformat()
    if isinstance(data, UUID):
        return str(data)
    if isinstance(data, Decimal):
        return float(data)
    return convert_to_camel_case(jsonable_encoder(data))
