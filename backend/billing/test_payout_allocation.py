from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase
from .payout_allocation import allocate_received


class PayoutAllocationTests(SimpleTestCase):
    def test_methods_are_distinct_and_preserve_cents(self):
        start, end = date(2026, 1, 1), date(2026, 2, 28)
        daily = allocate_received(Decimal('100.00'), start, end, 'calendar_days')
        monthly = allocate_received(Decimal('100.00'), start, end, 'equal_months')
        self.assertEqual(list(daily.values()), [Decimal('52.54'), Decimal('47.46')])
        self.assertEqual(list(monthly.values()), [Decimal('50.00'), Decimal('50.00')])
        self.assertEqual(sum(daily.values()), Decimal('100.00'))
        self.assertEqual(sum(monthly.values()), Decimal('100.00'))

    def test_clamped_dates_do_not_lose_or_create_cents(self):
        result = allocate_received(Decimal('101.01'), date(2026, 1, 31), date(2026, 4, 29), 'equal_months')
        self.assertEqual(sum(result.values()), Decimal('101.01'))
        self.assertEqual(list(result), [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)])

    def test_invalid_amount_and_range_are_rejected(self):
        with self.assertRaises(ValueError):
            allocate_received(Decimal('-1.00'), date(2026, 1, 1), date(2026, 1, 31), 'calendar_days')
        with self.assertRaises(ValueError):
            allocate_received(Decimal('1.001'), date(2026, 1, 1), date(2026, 1, 31), 'calendar_days')
