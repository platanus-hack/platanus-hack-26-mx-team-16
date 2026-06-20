from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.common.domain.buses.commands import Command


@dataclass
class CommandEnqueuer(ABC):
    @abstractmethod
    async def enqueue(self, command: Command):
        raise NotImplementedError
