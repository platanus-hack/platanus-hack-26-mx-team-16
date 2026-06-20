from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models import EmailAddressORM
from src.common.domain.models.email_address import EmailAddress
from src.users.domain.repositories.email_address import EmailAddressRepository


@dataclass
class SQLEmailAddressRepository(EmailAddressRepository):
    session: AsyncSession

    async def get_or_create(self, email: str) -> EmailAddress:
        stmt = select(EmailAddressORM).where(EmailAddressORM.email == email)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            orm_instance = EmailAddressORM(email=email)
            self.session.add(orm_instance)
            await self.session.flush()  # Flush to get the ID without committing

        return EmailAddress.model_validate(orm_instance)
