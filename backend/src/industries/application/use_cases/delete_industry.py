from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.industries.domain.repositories.industry_repository import IndustryRepository


@dataclass
class DeleteIndustry(UseCase):
    industry_id: UUID
    industry_repository: IndustryRepository

    async def execute(self) -> None:
        await self.industry_repository.delete(self.industry_id)
