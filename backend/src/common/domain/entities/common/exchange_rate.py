from dataclasses import dataclass
from decimal import Decimal

from src.common.domain.enums.currencies import CurrencyCode


@dataclass
class ExchangeRate:
    currency_code: CurrencyCode
    rate: Decimal

    @property
    def to_dict(self):
        return {
            "currency_code": str(self.currency_code),
            "rate": str(self.rate),
        }


exchange_rate_set = {
    CurrencyCode.BOB: [
        ExchangeRate(
            currency_code=CurrencyCode.USD,
            rate=Decimal("6.97"),
        ),
        # CurrencyRate(
        #     currency_code=CurrencyCode.EUR,
        #     rate=Decimal("8.18"),
        # ),
    ],
    CurrencyCode.USD: [
        ExchangeRate(
            currency_code=CurrencyCode.BOB,
            rate=Decimal("0.014"),
        ),
    ],
}


def get_exchange_rate_set(currency_code: CurrencyCode) -> list[ExchangeRate]:
    return exchange_rate_set.get(currency_code, [])
