from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class LambdaSuccessResponse(BaseModel):
    status: Literal["success"]
    data: dict
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class LambdaErrorResponse(BaseModel):
    status: Literal["error"]
    error_code: str
    message: str
    details: dict | None = None

    model_config = ConfigDict(from_attributes=True)


LambdaResponse = Annotated[
    LambdaSuccessResponse | LambdaErrorResponse,
    Field(discriminator="status"),
]
