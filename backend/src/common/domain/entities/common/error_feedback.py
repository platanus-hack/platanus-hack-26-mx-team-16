from pydantic import BaseModel


class ErrorItem(BaseModel):
    code: str
    message: str


class ErrorFeedback(BaseModel):
    errors: list[ErrorItem]
    validation: dict[str, list[ErrorItem]] | None = None

    class Config:
        extra = "ignore"
