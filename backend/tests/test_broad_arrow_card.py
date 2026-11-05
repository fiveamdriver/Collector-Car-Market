"""Broad Arrow results-card parsing (data/broad_arrow_ingest.parse_card /
map_schema_car). Card texts are the real 2026-11-05 formats, shortened.

Run from backend/:  python -m unittest tests.test_broad_arrow_card -v
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "data"))

from broad_arrow_ingest import map_schema_car, parse_card  # noqa: E402

HEAD = "LEARN MORE 2016 PORSCHE 911 R Lot 70 | The Quail Auction 2026 "


def schema(url="https://www.broadarrowauctions.com/vehicles/ql26_r0070/2016-porsche-911-r",
           price="62000", availability="https://schema.org/OutOfStock"):
    return {"url": url, "manufacturer": "Porsche", "model": "911 R", "vehicleModelDate": "2016",
            "offers": {"price": price, "availability": availability}}


class ParseCardTests(unittest.TestCase):
    def test_formats(self):
        cases = {
            "Sold Price: $620,000": ("sold", 620000, "USD"),
            "Sold Price: €135,000": ("sold", 135000, "EUR"),
            "Sold Price: CHF 1'393'000": ("sold", 1393000, "CHF"),
            "Sold Price: £212,750": ("sold", 212750, "GBP"),
            "Monterey Jet Center 2022 $1,930.000": ("sold", 1930000, "USD"),   # site typo
            "Monterey Jet Center 2023 $ 145,000": ("sold", 145000, "USD"),
            "Sold After Auction for $145,000": ("sold", 145000, "USD"),
            "Sold After Auction": ("sold", None, None),
            "Sold Price: €0": ("sold", None, None),
            "Not Sold": ("not_sold", None, None),
            "WITHDRAWN": ("withdrawn", None, None),
            "Now Asking: Estimate Available Upon Request": ("not_sold", None, None),
            "Estimate Available Upon Request": ("not_sold", None, None),
            "": ("unknown", None, None),
        }
        for tail, want in cases.items():
            with self.subTest(tail=tail):
                self.assertEqual(parse_card((HEAD + tail) if tail else ""), want)

    def test_price_from_card_not_schema(self):
        # JSON-LD said 62000 (1/10 of the real price) for this lot.
        rec = map_schema_car(schema(), HEAD + "Sold Price: $620,000")
        self.assertEqual(rec["sold_price"], 620000)
        self.assertIsNone(rec["sale_status"])

    def test_unsold_and_withdrawn_skipped(self):
        for tail in ("Not Sold", "WITHDRAWN", "Now Asking: Estimate Available Upon Request"):
            self.assertIsNone(map_schema_car(schema(availability="https://schema.org/InStock"), HEAD + tail))

    def test_no_card_text_skipped(self):
        self.assertIsNone(map_schema_car(schema(), ""))

    def test_sold_after_auction_has_no_price(self):
        rec = map_schema_car(schema(price="29500000"), HEAD + "Sold After Auction")
        self.assertIsNone(rec["sold_price"])
        self.assertEqual(rec["sale_status"], "sold_after_auction")

    def test_foreign_currency_converted(self):
        url = "https://www.broadarrowauctions.com/vehicles/zt26_r0020/1953-porsche-356"
        rec = map_schema_car(schema(url=url), HEAD + "Sold Price: €132,250")
        self.assertEqual(rec["sold_price"], round(132250 * 1.13))


if __name__ == "__main__":
    unittest.main()
