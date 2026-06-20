import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.database.models import PhoneNumberORM
from src.common.database.models.email_address import EmailAddressORM
from src.common.database.models.user import UserORM
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.user import User
from src.common.infrastructure.builders.user import build_user
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.infrastructure.helpers.password import check_password, hash_password
from src.tenants.infrastructure.repositories.sql_tenant_user import SQLTenantUserRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class SQLUserRepository(UserRepository):
    session: AsyncSession

    async def find(self, user_id: UUID) -> User | None:
        stmt = (
            select(UserORM)
            .options(
                selectinload(UserORM.email_address),
                selectinload(UserORM.phone_number),
                selectinload(UserORM.current_tenant),
            )
            .where(UserORM.uuid == user_id)
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            return None

        user = build_user(orm_instance)
        user.role = await self._get_user_role(user)

        return user

    async def _get_user_role(self, user: User) -> TenantRole | None:
        if not user.current_tenant_id:
            return None

        tenant_user_repository = SQLTenantUserRepository(self.session)
        tenant_user = await tenant_user_repository.find_by_args(
            user_id=user.uuid,
            tenant_id=user.current_tenant_id,
        )
        if tenant_user:
            return tenant_user.tenant_role

        return None

    async def filter(self, **kwargs) -> list[User]:
        stmt = select(UserORM).options(
            selectinload(UserORM.email_address),
            selectinload(UserORM.current_tenant),
            selectinload(UserORM.phone_number),
        )

        # Apply filters dynamically
        for key, value in kwargs.items():
            stmt = stmt.where(getattr(UserORM, key) == value)

        result = await self.session.execute(stmt)
        orm_instances = result.scalars().all()

        users = []
        for orm_instance in orm_instances:
            user = build_user(orm_instance)
            users.append(user)
        return users

    async def find_by_phone_number(self, phone_number: RawPhoneNumber) -> User | None:
        stmt = (
            select(UserORM)
            .options(
                selectinload(UserORM.email_address),
                selectinload(UserORM.current_tenant),
                selectinload(UserORM.phone_number),
            )
            .where(UserORM.phone_number.has(dial_code=phone_number.dial_code, phone_number=phone_number.phone_number))
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            return None

        return build_user(orm_instance)

    async def find_by_email(self, email: str) -> User | None:
        stmt = (
            select(UserORM)
            .options(
                selectinload(UserORM.email_address),
                selectinload(UserORM.phone_number),
                selectinload(UserORM.current_tenant),
            )
            .where(UserORM.email_address.has(email=email))
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            return None

        return build_user(orm_instance)

    async def check_password(self, user_id: UUID, raw_password: str) -> bool:
        stmt = select(UserORM).where(UserORM.uuid == user_id)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance is None:
            return False

        if orm_instance.password is None:
            return False

        return check_password(raw_password, orm_instance.password)

    async def set_password(self, user_id: UUID, new_password: str) -> bool:
        async with atomic_transaction(self.session):
            orm_user = await self._find(user_id=user_id)
            if orm_user is None:
                return False
            orm_user.password = hash_password(new_password)
            await self.session.flush()
        return True

    async def persist(self, instance: User) -> User:
        async with atomic_transaction(self.session):
            user_orm = await self._find(instance.uuid)

            phone_number_orm = (
                await self._get_or_create_phone_number(instance.phone_number.to_raw) if instance.phone_number else None
            )
            email_address_orm = (
                await self._get_or_create_email(instance.email_address.email) if instance.email_address else None
            )

            if user_orm is None:
                user_orm = UserORM(**instance.persist_data)
                self.session.add(user_orm)
            else:
                for key, value in instance.persist_data.items():
                    setattr(user_orm, key, value)

            user_orm.phone_number_id = phone_number_orm.uuid if phone_number_orm else None
            user_orm.email_address_id = email_address_orm.uuid if email_address_orm else None

            await self.session.flush()

            user_orm = await self._find(user_orm.uuid)
            return build_user(user_orm)

    async def remove(self, user_id: UUID):
        stmt = select(UserORM).where(UserORM.uuid == user_id)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        if orm_instance:
            await self.session.delete(orm_instance)
            await self.session.flush()

    async def update_current_tenant(self, user_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = update(UserORM).where(UserORM.uuid == user_id).values(current_tenant_id=tenant_id)
            await self.session.execute(stmt)
            await self.session.flush()

    async def clear_current_tenant_for_users(self, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = update(UserORM).where(UserORM.current_tenant_id == tenant_id).values(current_tenant_id=None)
            await self.session.execute(stmt)
            await self.session.flush()

    async def create_user(self, user: User, password: str, is_superuser: bool = False) -> User:
        async with atomic_transaction(self.session):
            hashed_password = hash_password(password)
            email_address_orm = await self._get_or_create_email(user.email_address.email)

            user_data = user.persist_data
            user_data.update(
                {
                    "password": hashed_password,
                    "is_superuser": is_superuser,
                    "username": user.username,
                    "uuid": user.uuid,
                }
            )
            if email_address_orm:
                user_data["email_address_id"] = email_address_orm.uuid

            orm_instance = UserORM(**user_data)
            self.session.add(orm_instance)
            await self.session.flush()

            orm_instance = await self._find(user.uuid)
            return build_user(orm_instance)

    async def _find(self, user_id: UUID) -> UserORM | None:
        stmt = (
            select(UserORM)
            .options(
                selectinload(UserORM.email_address),
                selectinload(UserORM.phone_number),
                selectinload(UserORM.current_tenant),
            )
            .where(UserORM.uuid == user_id)
        )
        result = await self.session.execute(stmt)
        orm_instance: UserORM | None = result.scalar_one_or_none()
        return orm_instance

    async def _get_or_create_email(self, email: str) -> EmailAddressORM:
        async with atomic_transaction(self.session):
            stmt = select(EmailAddressORM).where(EmailAddressORM.email == email)
            result = await self.session.execute(stmt)
            email_orm: EmailAddressORM | None = result.scalar_one_or_none()

            if email_orm is None:
                email_orm = EmailAddressORM(
                    uuid=uuid.uuid4(),
                    email=email,
                    is_verified=False,
                )
                self.session.add(email_orm)
                await self.session.flush()

            return email_orm

    async def _get_or_create_phone_number(self, raw_phone_number: RawPhoneNumber) -> PhoneNumberORM:
        async with atomic_transaction(self.session):
            query = select(PhoneNumberORM).where(
                PhoneNumberORM.dial_code == raw_phone_number.dial_code,
                PhoneNumberORM.phone_number == raw_phone_number.phone_number,
            )
            result = await self.session.execute(query)
            phone_number_orm = result.scalar_one_or_none()

            if phone_number_orm is None:
                phone_number_orm = PhoneNumberORM(
                    uuid=uuid.uuid4(),
                    dial_code=raw_phone_number.dial_code,
                    phone_number=raw_phone_number.phone_number,
                    prefix=raw_phone_number.prefix,
                    iso_code=str(raw_phone_number.iso_code),
                    is_verified=False,
                )
                self.session.add(phone_number_orm)
                await self.session.flush()

            return phone_number_orm
