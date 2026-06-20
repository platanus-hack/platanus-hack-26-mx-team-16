class CommandAlreadyExistError(Exception):
    pass


class CommandHandlerDoesNotExistError(Exception):
    pass


class QueryAlreadyExistError(Exception):
    pass


class QueryHandlerDoesNotExistError(Exception):
    pass


class EventHandlerDoesNotExistError(Exception):
    pass
