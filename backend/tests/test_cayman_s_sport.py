"""2008 Cayman S Sport gets its own card; option packages and other years don't."""
import unittest

from app.utils.variants import is_cayman_s_sport


class TestCaymanSSport(unittest.TestCase):
    def test_titles(self):
        yes = ["31k-Mile 2008 Porsche Cayman S Sport 6-Speed",
               "27K-Mile 2008 Porsche Cayman S Sport Edition 6-Speed #191/700"]
        no = ["2008 Porsche Cayman S Sport Chrono", "2008 Porsche Cayman S Sport Design Package",
              "2008 Porsche Cayman S", "2008 Porsche Cayman S Sport Exhaust"]
        for t in yes:
            self.assertTrue(is_cayman_s_sport(t, 2008), t)
        for t in no:
            self.assertFalse(is_cayman_s_sport(t, 2008), t)

    def test_year_guard(self):
        self.assertFalse(is_cayman_s_sport("2010 Porsche Cayman S Sport", 2010))


if __name__ == "__main__":
    unittest.main()
