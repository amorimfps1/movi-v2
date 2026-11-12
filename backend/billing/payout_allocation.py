"""Distribuição de recebimentos em meses de prestação, em centavos exatos."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction


def _add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, min(day.day, monthrange(year, month + 1)[1]))


def allocate_received(amount, start, end, method):
    if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError('Valor deve ser não negativo e expresso em centavos.')
    if end < start or method not in ('calendar_days', 'equal_months'):
        raise ValueError('Período ou critério de rateio inválido.')
    periods = []
    index = 0
    while True:
        begin = _add_months(start, index)
        if begin > end:
            break
        try:
            following = _add_months(start, index + 1)
        except (ValueError, OverflowError):
            raise ValueError('Período fora do calendário suportado.') from None
        periods.append((begin, min(end, following - timedelta(days=1))))
        index += 1
        if index > 120:
            raise ValueError('A duração máxima suportada é de 120 meses.')
    total_days = (end - start).days + 1
    weights = {}
    for begin, finish in periods:
        period_days = (finish - begin).days + 1
        day = begin
        while day <= finish:
            month = day.replace(day=1)
            weight = Fraction(1, total_days) if method == 'calendar_days' else Fraction(1, len(periods) * period_days)
            weights[month] = weights.get(month, Fraction()) + weight
            if day == finish:
                break
            day += timedelta(days=1)
    cents = int(amount * 100)
    raw = {month: weight * cents for month, weight in weights.items()}
    allocated = {month: value.numerator // value.denominator for month, value in raw.items()}
    remainder = cents - sum(allocated.values())
    order = sorted(raw, key=lambda month: (-(raw[month] - allocated[month]), month))
    for month in order[:remainder]:
        allocated[month] += 1
    return {month: Decimal(value) / 100 for month, value in sorted(allocated.items())}
