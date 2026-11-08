"""Dated FX in the RM / Bonhams ingests and the backfill's per-row decision."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))

from app.utils import fx  # noqa: E402
import backfill_original_price as B  # noqa: E402
import bonhams_ingest  # noqa: E402
import rms_ingest  # noqa: E402

D = date(2008, 7, 15)  # EUR/USD 1.5990


def row(**kw):
    base = {"id": 1, "auction_source": "RM Sotheby's", "auction_url": "u", "sold_date": D,
            "sold_price": 1_090_000, "original_price": None, "original_currency": None}
    return {**base, **kw}


class RmPriceParse(unittest.TestCase):
    def test_keeps_amount_and_currency(self):
        self.assertEqual(rms_ingest.parse_price("£3,492,500 GBP"), (3_492_500, "GBP"))
        self.assertEqual(rms_ingest.parse_price("€1,000,000 EUR"), (1_000_000, "EUR"))
        self.assertEqual(rms_ingest.parse_price("$1,250,000 USD"), (1_250_000, "USD"))
        self.assertEqual(rms_ingest.parse_price("CAD 90,000"), (90_000, "CAD"))

    def test_lot_url_accepts_path_or_full_url(self):
        full = "https://rmsothebys.com/auctions/am18/lots/r0015-1993-porsche-911-carrera-rs-38/"
        self.assertEqual(rms_ingest.lot_url_for(full), full)
        self.assertEqual(rms_ingest.lot_url_for("/auctions/am18/lots/r0015/"),
                         "https://rmsothebys.com/auctions/am18/lots/r0015/")
        self.assertIsNone(rms_ingest.lot_url_for(""))

    def test_rejects_estimate_range(self):
        self.assertIsNone(rms_ingest.parse_price("$1,000,000 - $1,200,000 USD"))

    def test_map_record_converts_at_sale_date(self):
        item = {"sold": True, "auctioned": True, "publicName": "1973 Porsche 911 Carrera RS 2.7",
                "value": "€1,000,000 EUR", "link": "/en/auctions/x/lots/r1/", "collection": ""}
        rec = rms_ingest.map_record(item, "2008-07-15")
        self.assertEqual(rec["sold_price"], 1_599_000)
        self.assertEqual((rec["original_price"], rec["original_currency"]), (1_000_000, "EUR"))


class BonhamsMap(unittest.TestCase):
    DOC = {"title": "1973 Porsche 911 Carrera RS 2.7 Lightweight", "auctionId": 1, "lotId": 2,
           "slug": "s", "price": {"hammerPremium": 500_000}, "currency": {"iso_code": "GBP"},
           "hammerTime": {"datetime": "2008-07-15T14:00:00Z"}}

    def test_converts_at_sale_date_and_keeps_original(self):
        rec = bonhams_ingest.map_lot(self.DOC)
        self.assertEqual(rec["sold_price"], fx.to_usd(500_000, "GBP", D))
        self.assertEqual((rec["original_price"], rec["original_currency"]), (500_000, "GBP"))

    def test_non_usd_without_date_is_skipped(self):
        self.assertIsNone(bonhams_ingest.map_lot({**self.DOC, "hammerTime": {}}))

    def test_unknown_currency_is_skipped(self):
        self.assertIsNone(bonhams_ingest.map_lot({**self.DOC, "currency": {"iso_code": "HKD"}}))


class PlanRow(unittest.TestCase):
    def test_eur_row_is_repriced(self):
        p = B.plan_row(row(), (1_000_000, "EUR"))
        self.assertEqual(p["action"], "update")
        self.assertEqual(p["new"], {"sold_price": 1_599_000, "original_price": 1_000_000,
                                    "original_currency": "EUR"})
        self.assertEqual(p["old"]["sold_price"], 1_090_000)

    def test_usd_row_only_records_original(self):
        p = B.plan_row(row(sold_price=250_000), (250_000, "USD"))
        self.assertEqual(p["action"], "unchanged")
        self.assertEqual(p["new"]["sold_price"], 250_000)

    def test_price_not_from_old_rule_is_left_alone(self):
        p = B.plan_row(row(sold_price=1_200_000), (1_000_000, "EUR"))
        self.assertEqual(p["action"], "skip")
        self.assertIn("edited since ingest", p["reason"])

    def test_fractional_source_amount_matches_old_rule(self):
        # Bonhams sends premium-inclusive amounts with pence; the old ingest
        # multiplied the unrounded value (34553.5 x 1.27 = 43882.945 -> 43883).
        p = B.plan_row(row(auction_source="Bonhams", sold_date=date(2004, 6, 25), sold_price=43_883),
                       (34_553.5, "GBP"))
        self.assertEqual(p["action"], "update")
        self.assertEqual(p["new"]["original_price"], 34_554)

    def test_missing_in_source_is_left_alone(self):
        self.assertEqual(B.plan_row(row(), None)["action"], "skip")

    def test_no_sale_date_is_left_alone(self):
        p = B.plan_row(row(sold_date=None), (1_000_000, "EUR"))
        self.assertEqual(p["action"], "skip")

    def test_second_run_is_a_no_op(self):
        done = row(sold_price=1_599_000, original_price=1_000_000, original_currency="EUR")
        p = B.plan_row(done, (1_000_000, "EUR"))
        self.assertEqual((p["action"], p["reason"]), ("skip", "already done"))


if __name__ == "__main__":
    unittest.main()
