from abc import ABC, abstractmethod


class FieldSuggester(ABC):
    @abstractmethod
    async def suggest(
        self,
        extracted_text: str,
        doctype_name: str,
        prompt: str | None,
    ) -> dict:
        """Returns a JSON Schema dict (Draft-7, type=object)."""
        raise NotImplementedError
