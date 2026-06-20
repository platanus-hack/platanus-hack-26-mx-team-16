from decimal import ROUND_HALF_UP, Decimal


def amount_decimal_to_int(amount: Decimal) -> int:
    return int((amount * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))


def amount_int_to_decimal(amount: int) -> Decimal:
    return Decimal(amount) / Decimal(100)


def decimal_with_default(amount: Decimal | None) -> Decimal:
    if amount is None:
        return Decimal("0")
    return amount


def round_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
