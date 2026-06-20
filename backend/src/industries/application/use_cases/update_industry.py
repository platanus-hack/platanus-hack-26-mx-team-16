from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.industry import Industry
from src.common.domain.exceptions.industries import IndustryNotFoundError
from src.industries.domain.repositories.industry_repository import IndustryRepository


@dataclass
class UpdateIndustry(UseCase):
    industry_id: UUID
    industry_repository: IndustryRepository
    name: str | None = None
    new_slug: str | None = None
    icon: str | None = None
    description: str | None = None

    async def execute(self) -> Industry:
        industry = await self.industry_repository.find_by_id(self.industry_id)
        if not industry:
            raise IndustryNotFoundError(str(self.industry_id))

        if self.name is not None:
            industry.name = self.name
        if self.new_slug is not None:
            industry.slug = self.new_slug
        if self.icon is not None:
            industry.icon = self.icon
        if self.description is not None:
            industry.description = self.description

        return await self.industry_repository.update(industry)
