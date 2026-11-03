import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.broad_arrow_ingest import lot_key  # noqa: E402


class TestLotKey(unittest.TestCase):
    def test_padding_variants_are_the_same_lot(self):
        a = "https://www.broadarrowauctions.com/vehicles/po25_r013/1996-porsche-911-turbo"
        b = "https://www.broadarrowauctions.com/vehicles/po25_r0013/1996-porsche-911-turbo"
        self.assertEqual(lot_key(a), lot_key(b))
        self.assertEqual(lot_key(a), ("po25", 13))

    def test_different_lots_and_sales_differ(self):
        self.assertNotEqual(lot_key("https://x/vehicles/po25_r0013/a"), lot_key("https://x/vehicles/po25_r0130/a"))
        self.assertNotEqual(lot_key("https://x/vehicles/po25_r0013/a"), lot_key("https://x/vehicles/po26_r0013/a"))

    def test_old_unprefixed_ids(self):
        self.assertEqual(lot_key("https://x/vehicles/jc23_166/1997-porsche"), ("jc23", 166))
        self.assertIsNone(lot_key("https://x/events/795"))


if __name__ == "__main__":
    unittest.main()
