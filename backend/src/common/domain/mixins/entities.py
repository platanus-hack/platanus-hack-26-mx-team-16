from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_snake


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        validate_assignment=True,
    )


class SnakeModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,  # Accept both camelCase and snake_case
        validate_assignment=True,
    )
