from uuid import UUID

from pydantic import ConfigDict

from src.common.domain.entities.phone_number import RawPhoneNumber


class PhoneNumber(RawPhoneNumber):
    uuid: UUID
    is_verified: bool = False

    model_config = ConfigDict(
        from_attributes=True,
    )

    @property
    def to_raw(self) -> RawPhoneNumber:
        return RawPhoneNumber(
            dial_code=self.dial_code,
            phone_number=self.phone_number,
            iso_code=self.iso_code,
            prefix=self.prefix,
        )

    @property
    def international_phone_number(self) -> str:
        if self.prefix:
            return f"+{self.dial_code}{self.prefix}{self.phone_number}"
        return f"+{self.dial_code}{self.phone_number}"

    def __str__(self) -> str:
        return self.international_phone_number
