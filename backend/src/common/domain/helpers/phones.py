from src.common.constants import PHONE_NUMBER_PREFIXES_MAP
from src.common.domain.entities.common.country_config import CountryConfig


def calculate_phone_number_prefix(country_config: CountryConfig) -> int | None:
    return PHONE_NUMBER_PREFIXES_MAP.get(country_config.iso_code)
