from src.common.domain.buses.queries import Query, QueryBus, QueryHandler
from src.common.infrastructure.buses._exceptions import (
    QueryAlreadyExistError,
    QueryHandlerDoesNotExistError,
)


class MemoryQueryBus(QueryBus):
    def __init__(self) -> None:
        self._queries: dict[type[Query], QueryHandler[Query, object]] = {}

    def subscribe(self, query: type[Query], handler: QueryHandler[Query, object]) -> None:
        if query in self._queries:
            raise QueryAlreadyExistError
        self._queries[query] = handler

    async def ask(self, query: Query) -> object | None:
        if query.__class__ not in self._queries:
            raise QueryHandlerDoesNotExistError(query.__class__)
        return await self._queries[query.__class__].execute(query)
