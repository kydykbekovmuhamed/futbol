from decimal import ROUND_HALF_UP, Decimal


def percentage_of(amount: Decimal, percent) -> Decimal:
    """Общий расчёт процента от суммы с округлением до тыйына — задаток, комиссии и т.п."""
    return (amount * Decimal(percent) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
