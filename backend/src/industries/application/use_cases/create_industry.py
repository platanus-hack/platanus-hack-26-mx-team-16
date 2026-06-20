from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.industry import Industry
from src.common.domain.exceptions.industries import IndustryAlreadyExistsError
from src.industries.domain.repositories.industry_repository import IndustryRepository


@dataclass
class CreateIndustry(UseCase):
    slug: str
    name: str
    industry_repository: IndustryRepository
    icon: str | None = None
    description: str | None = None

    async def execute(self) -> Industry:
        existing = await self.industry_repository.find_by_slug(self.slug)
        if existing:
            raise IndustryAlreadyExistsError(self.slug)

        now = datetime.now(UTC)
        industry = Industry(
            uuid=uuid4(),
            slug=self.slug,
            name=self.name,
            icon=self.icon,
            description=self.description,
            created_at=now,
            updated_at=now,
        )
        return await self.industry_repository.create(industry)
