"""Canepa tag: a 959 Canepa re-engineered or upgraded, not one it merely serviced or imported."""
import unittest

from app.utils.lot_extras import derive, parse_canepa


class TestCanepaTag(unittest.TestCase):
    def test_title(self):
        self.assertTrue(parse_canepa("1988 Porsche 959 SC Reimagined by Canepa", None, "959"))

    def test_upgrades(self):
        for t in ["Upgraded by 959 specialist Canepa Design to Phase II specification",
                  "While at Canepa Design, it was given a “Stage One” engine upgrade.",
                  "Federalized and upgraded to 959S specification by Canepa Design",
                  "Canepa “Gen. 3” engine enhancements and “Canepa S” suspension",
                  "Canepa Manually Adjustable Coilover Suspension"]:
            self.assertTrue(parse_canepa("1988 Porsche 959 Komfort", t, "959"), t)

    def test_mentions_only(self):
        for t in ["A 2021 service at Canepa in Scotts Valley, California, included a clutch slave cylinder.",
                  "The Show and Display law of 1999, championed by Bruce Canepa, finally allowed 959s to be legally imported.",
                  "According to 959 expert Bruce Canepa, Porsche completed more 959s.",
                  "Documented with Canepa service binders",
                  "Acquired from and fully serviced by Canepa Design"]:
            self.assertFalse(parse_canepa("1988 Porsche 959 Komfort", t, "959"), t)

    def test_959_only(self):
        self.assertFalse(parse_canepa("1973 Porsche 911 RS upgraded by Canepa", None, "911"))

    def test_lands_in_options(self):
        d = derive("1988 Porsche 959 SC Reimagined by Canepa", None, 1988, "959", "959", "base")
        self.assertIn("Canepa", (d["options"] or "").split(","))


if __name__ == "__main__":
    unittest.main()
