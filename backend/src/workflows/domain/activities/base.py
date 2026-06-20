from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from src.workflows.domain.exceptions import ResponseParserNotSetError

T = TypeVar("T", bound=BaseModel)


class BaseActivity(ABC, Generic[T]):
    response_parser: type[T] | None = None

    @abstractmethod
    async def invoke_activity(self, payload: dict, function_name: str, *args, **kwargs) -> dict:
        raise NotImplementedError

    def parse_response(self, data: dict) -> T:
        if self.response_parser is None:
            raise ResponseParserNotSetError
        return self.response_parser.model_validate(data)
