from dataclasses import dataclass

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.industry import Industry
from src.industries.domain.repositories.industry_repository import IndustryRepository


@dataclass
class ListIndustries(UseCase):
    industry_repository: IndustryRepository

    async def execute(self) -> list[Industry]:
        return await self.industry_repository.list_all()
