from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models import PhoneNumberORM
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.phone_number import PhoneNumber
from src.users.domain.repositories.phone_number import PhoneNumberRepository


@dataclass
class SQLPhoneNumberRepository(PhoneNumberRepository):
    session: AsyncSession

    async def get_or_create(self, phone_number: RawPhoneNumber) -> PhoneNumber:
        stmt = select(PhoneNumberORM).where(
            PhoneNumberORM.dial_code == phone_number.dial_code,
            PhoneNumberORM.phone_number == phone_number.phone_number,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            orm_instance = PhoneNumberORM(
                dial_code=phone_number.dial_code,
                phone_number=phone_number.phone_number,
                iso_code=str(phone_number.iso_code),
            )
            self.session.add(orm_instance)
            await self.session.flush()  # Flush to get the ID without committing

        return PhoneNumber.model_validate(orm_instance)
