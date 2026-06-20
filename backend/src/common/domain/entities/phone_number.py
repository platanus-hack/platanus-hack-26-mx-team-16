from pydantic import BaseModel

from src.common.domain.enums.countries import CountryIsoCode


class RawPhoneNumber(BaseModel):
    dial_code: int
    phone_number: str
    iso_code: CountryIsoCode
    prefix: str | None = None
