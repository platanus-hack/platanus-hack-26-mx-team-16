from unittest.mock import MagicMock

from src.common.application.helpers.singleton import SingletonMeta
from src.common.domain.contexts.bus import BusContext


class MockBusSingleton(metaclass=SingletonMeta):
    instance: BusContext = MagicMock()
