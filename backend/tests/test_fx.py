import unittest
from datetime import date

from app.utils import fx


class RateLookup(unittest.TestCase):
    def test_usd_is_identity_with_or_without_date(self):
        self.assertEqual(fx.to_usd(1_250_000, "USD", None), 1_250_000)
        self.assertEqual(fx.usd_per_unit("usd", date(2005, 1, 3)), 1.0)

    def test_eur_uses_the_ecb_usd_column(self):
        # ECB 2008-07-15: EUR/USD 1.5990 (the all-time high fixing).
        self.assertAlmostEqual(fx.usd_per_unit("EUR", date(2008, 7, 15)), 1.5990)

    def test_cross_rate_through_eur(self):
        # ECB 2026-11-06: USD 1.1165, GBP 0.83415 per EUR.
        self.assertAlmostEqual(fx.usd_per_unit("GBP", date(2026, 11, 6)), 1.1165 / 0.83415)

    def test_weekend_uses_previous_fixing(self):
        # 2026-11-07/08 are a Saturday and Sunday.
        self.assertEqual(fx.rate_date(date(2026, 11, 8)), date(2026, 11, 6))
        self.assertEqual(fx.usd_per_unit("EUR", date(2026, 11, 8)),
                         fx.usd_per_unit("EUR", date(2026, 11, 6)))

    def test_date_before_table_raises(self):
        with self.assertRaises(fx.FxDateOutOfRange):
            fx.to_usd(100, "EUR", date(1998, 12, 1))

    def test_date_far_after_table_raises(self):
        with self.assertRaises(fx.FxDateOutOfRange):
            fx.to_usd(100, "EUR", date(2030, 1, 1))

    def test_non_usd_without_date_raises(self):
        with self.assertRaises(fx.FxError):
            fx.to_usd(100, "GBP", None)

    def test_unknown_currency_raises(self):
        with self.assertRaises(fx.FxError):
            fx.usd_per_unit("JPY", date(2020, 1, 2))

    def test_same_amount_different_years_differ(self):
        # The bug this module fixes: one fixed rate for every year.
        a = fx.to_usd(1_000_000, "EUR", date(2008, 7, 15))
        b = fx.to_usd(1_000_000, "EUR", date(2015, 3, 16))
        self.assertGreater(a - b, 400_000)


if __name__ == "__main__":
    unittest.main()
