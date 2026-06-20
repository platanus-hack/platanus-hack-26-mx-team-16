from src.common.database.models.phone_number import PhoneNumberORM
from src.common.domain.models.phone_number import PhoneNumber
from src.common.domain.enums.countries import CountryIsoCode


def build_phone_number(
    orm_instance: PhoneNumberORM,
) -> PhoneNumber:
    return PhoneNumber(
        uuid=orm_instance.uuid,
        dial_code=orm_instance.dial_code,
        phone_number=orm_instance.phone_number,
        iso_code=CountryIsoCode.from_value(orm_instance.iso_code),
        prefix=orm_instance.prefix,
        is_verified=orm_instance.is_verified,
    )
