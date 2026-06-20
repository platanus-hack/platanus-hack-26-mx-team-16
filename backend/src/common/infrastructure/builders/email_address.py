from src.common.database.models.email_address import EmailAddressORM
from src.common.domain.models.email_address import EmailAddress


def build_email_address(
    orm_instance: EmailAddressORM,
) -> EmailAddress:
    return EmailAddress(
        uuid=orm_instance.uuid,
        email=orm_instance.email,
        is_verified=orm_instance.is_verified,
    )
