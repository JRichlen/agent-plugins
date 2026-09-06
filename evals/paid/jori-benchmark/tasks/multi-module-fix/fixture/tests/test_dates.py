import unittest
from datetime import date
from calc.dates import days_between, is_weekend, parse_iso


class DateTests(unittest.TestCase):
    def test_days_between_forward(self):
        self.assertEqual(days_between(date(2026, 1, 1), date(2026, 1, 11)), 10)

    def test_days_between_is_order_independent(self):
        self.assertEqual(days_between(date(2026, 1, 11), date(2026, 1, 1)), 10)

    def test_weekend(self):
        self.assertTrue(is_weekend(date(2026, 9, 6)))   # a Sunday
        self.assertFalse(is_weekend(date(2026, 9, 7)))  # a Monday

    def test_parse_iso(self):
        self.assertEqual(parse_iso("2026-09-06"), date(2026, 9, 6))
