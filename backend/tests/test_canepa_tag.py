"""Canepa tag: only the 959 SC Reimagined by Canepa, not 959s Canepa upgraded or serviced."""
import unittest

from app.utils.lot_extras import derive, parse_canepa


class TestCanepaTag(unittest.TestCase):
    def test_reimagined(self):
        self.assertTrue(parse_canepa("1988 Porsche 959 SC Reimagined by Canepa", None, "959"))

    def test_upgraded_is_not_tagged(self):
        self.assertFalse(parse_canepa("1987 Porsche 959 'Komfort'",
                                      "Upgraded by 959 specialist Canepa Design to Phase II specification", "959"))

    def test_959_only(self):
        self.assertFalse(parse_canepa("964 Reimagined by Canepa", None, "911"))

    def test_lands_in_options(self):
        d = derive("1988 Porsche 959 SC Reimagined by Canepa", None, 1988, "959", "959", "base")
        self.assertIn("Canepa", (d["options"] or "").split(","))


if __name__ == "__main__":
    unittest.main()
