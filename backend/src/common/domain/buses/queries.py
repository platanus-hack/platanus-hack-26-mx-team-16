from abc import ABC, abstractmethod
from dataclasses import dataclass


class Query:
    pass


@dataclass
class QueryHandler[TQuery: Query, TResult](ABC):
    @abstractmethod
    async def execute(self, query: TQuery) -> TResult | None:
        raise NotImplementedError


@dataclass
class QueryBus(ABC):
    @abstractmethod
    def subscribe(self, query: type[Query], handler: QueryHandler[Query, object]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def ask(self, query: Query) -> object | None:
        raise NotImplementedError
