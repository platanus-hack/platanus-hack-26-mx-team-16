from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.enums.locales import Language, TimeZone

DEFAULT_LANGUAGE = Language.ES
DEFAULT_TIMEZONE = TimeZone.MEXICO_CITY
DEFAULT_CURRENCY_CODE = CurrencyCode.MXN
DEFAULT_COUNTRY_ISO_CODE = CountryIsoCode.MEXICO
DEFAULT_MEXICO_PREFIX = 1

TENANTS_LIMIT: int = 3
MAX_PAGES: int = 20
MAX_CONCURRENT_EMAILS = 25

PERMISSIONS_ENABLED = False

AWS_LAMBDA_MAX_TIMEOUT = 900  # seconds — AWS Lambda hard limit

PHONE_NUMBER_PREFIXES_MAP: dict[CountryIsoCode, int] = {
    CountryIsoCode.MEXICO: DEFAULT_MEXICO_PREFIX,
    CountryIsoCode.BRAZIL: 9,
}
