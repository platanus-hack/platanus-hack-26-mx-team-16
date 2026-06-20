from abc import ABC, abstractmethod


class CodeGenerator(ABC):
    """Abstract base class for code generation"""

    @abstractmethod
    async def generate_code(self) -> str:
        """Generate a unique code"""
        raise NotImplementedError
