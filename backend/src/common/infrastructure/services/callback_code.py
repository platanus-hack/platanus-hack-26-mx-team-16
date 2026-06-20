import random
import string
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src.common.domain.services.code import CodeGenerator


@dataclass
class CallbackCodeGenerator(CodeGenerator):
    check_exists: Callable[[str], Awaitable[bool]]

    async def generate_code(self) -> str:
        max_attempts = 1000
        attempts = 0

        while attempts < max_attempts:
            code = self._generate_code()
            exists = await self.check_exists(code)
            if not exists:
                return code
            attempts += 1

        raise ValueError("Could not generate a unique code after maximum attempts")

    @classmethod
    def _generate_code(cls) -> str:
        characters = string.ascii_uppercase + string.digits
        code = "".join(random.choice(characters) for _ in range(6))
        return code
