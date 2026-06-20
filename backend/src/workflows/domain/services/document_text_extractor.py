from abc import ABC, abstractmethod


class DocumentTextExtractor(ABC):
    @abstractmethod
    async def extract(self, s3_key: str, **kwargs) -> str:
        raise NotImplementedError
