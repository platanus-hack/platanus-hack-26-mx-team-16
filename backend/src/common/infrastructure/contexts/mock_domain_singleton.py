from unittest.mock import MagicMock

from src.common.application.helpers.singleton import SingletonMeta
from src.common.domain.contexts.domain import DomainContext


class MockDomainSingleton(metaclass=SingletonMeta):
    instance: DomainContext = MagicMock()
