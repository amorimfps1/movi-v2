"""Confirmed initial catalog; no persistence or unapproved financial automation."""
from decimal import Decimal

PRODUCTS = {
    "hour": {"name": "Hora avulsa", "price": Decimal("5.00"), "hours": 1, "months": 0, "max_installments": 1},
    "half_day": {"name": "Meia diária", "price": Decimal("15.00"), "hours": 4, "months": 0, "max_installments": 1},
    "day": {"name": "Diária", "price": Decimal("25.00"), "hours": 8, "months": 0, "max_installments": 1},
    "monthly": {"name": "Mensal", "price": Decimal("169.00"), "hours": None, "months": 1, "max_installments": 1},
    "semiannual": {"name": "Semestral", "price": Decimal("699.00"), "hours": None, "months": 6, "max_installments": 6},
    "annual": {"name": "Anual", "price": Decimal("969.00"), "hours": None, "months": 12, "max_installments": 12},
}
