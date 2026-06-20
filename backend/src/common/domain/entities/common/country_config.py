from dataclasses import dataclass

from src.common.constants import DEFAULT_LANGUAGE
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.enums.locales import Language, TimeZone


@dataclass(frozen=True)
class CountryConfig:
    name: str
    iso_code: CountryIsoCode
    currency_code: CurrencyCode
    dial_code: int
    time_zone: TimeZone
    emoji: str
    lang: Language = DEFAULT_LANGUAGE
    dial_prefix: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "CountryConfig":
        return cls(
            name=data["name"],
            iso_code=CountryIsoCode(data["iso_code"]),
            currency_code=CurrencyCode(data["currency_code"]),
            time_zone=TimeZone(data["time_zone"]),
            dial_code=int(data["dial_code"]),
            emoji=data["emoji"],
            lang=Language(data["lang"]) if data.get("lang") else DEFAULT_LANGUAGE,
            dial_prefix=data.get("dial_prefix"),
        )
