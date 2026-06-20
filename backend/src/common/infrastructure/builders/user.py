from src.common.database.models.user import UserORM
from src.common.domain.models.user import User
from src.common.infrastructure.builders.email_address import build_email_address
from src.common.infrastructure.builders.phone_number import build_phone_number


def build_user(
    orm_instance: UserORM,
) -> User:
    return User(
        uuid=orm_instance.uuid,
        username=orm_instance.username,
        first_name=orm_instance.first_name,
        last_name=orm_instance.last_name,
        email_address=(build_email_address(orm_instance.email_address) if orm_instance.email_address else None),
        phone_number=(build_phone_number(orm_instance.phone_number) if orm_instance.phone_number else None),
        current_tenant_id=orm_instance.current_tenant_id,
        has_password=orm_instance.password is not None,
        is_superuser=orm_instance.is_superuser,
    )
