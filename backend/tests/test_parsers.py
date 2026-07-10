"""
Unit tests for the pure classification functions the dataset depends on.

Run from the backend/ directory:
    python -m unittest discover tests -v

These functions were previously copy-pasted into every ingest script and had
silently drifted (ocd_ingest filed every pre-1995 911 as a 964). The ladders
now live in app.utils.generations; these tests pin the boundaries so future
edits can't drift unnoticed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.generations import (
    get_911_generation,
    get_boxster_generation,
    get_cayman_generation,
)
from app.utils.transaxle import classify, match_model_line


class Test911Generation(unittest.TestCase):
    # (year, expected) — one case either side of every boundary.
    CASES = [
        (1964, "F-Body"), (1973, "F-Body"),
        (1974, "G-Body"), (1989, "G-Body"),
        (1990, "964"),    (1994, "964"),
        (1995, "993"),    (1998, "993"),
        (1999, "996.1"),  (2001, "996.1"),
        (2002, "996.2"),  (2005, "996.2"),
        (2006, "997.1"),  (2008, "997.1"),
        (2009, "997.2"),  (2012, "997.2"),
        (2013, "991.1"),  (2016, "991.1"),
        (2017, "991.2"),  (2019, "991.2"),
        (2020, "992"),    (2026, "992"),
    ]

    def test_boundaries(self):
        for year, expected in self.CASES:
            with self.subTest(year=year):
                self.assertEqual(get_911_generation(year), expected)


class TestCaymanGeneration(unittest.TestCase):
    CASES = [
        (2006, "987.1"), (2008, "987.1"),
        (2009, "987.2"), (2012, "987.2"),
        (2013, "981"),   (2016, "981"),
        (2017, "718"),   (2026, "718"),
    ]

    def test_boundaries(self):
        for year, expected in self.CASES:
            with self.subTest(year=year):
                self.assertEqual(get_cayman_generation(year), expected)


class TestBoxsterGeneration(unittest.TestCase):
    CASES = [
        (1997, "986"),   (2004, "986"),
        (2005, "987.1"), (2008, "987.1"),
        (2009, "987.2"), (2012, "987.2"),
        (2013, "981"),   (2016, "981"),
        (2017, "718"),   (2026, "718"),
    ]

    def test_boundaries(self):
        for year, expected in self.CASES:
            with self.subTest(year=year):
                self.assertEqual(get_boxster_generation(year), expected)


class TestTransmissionNormalizers(unittest.TestCase):
    """PDK (dual-clutch) and Tiptronic/Sportomatic (torque-converter) are
    distinct transmissions and must not be conflated."""

    def test_ocd_normalize(self):
        from data.ocd_ingest import normalize_transmission
        self.assertEqual(normalize_transmission("7-Speed PDK"), "PDK")
        self.assertEqual(normalize_transmission("Doppelkupplung"), "PDK")
        self.assertEqual(normalize_transmission("Tiptronic"), "Automatic")
        self.assertEqual(normalize_transmission("5-Speed Automatic"), "Automatic")
        self.assertEqual(normalize_transmission("6-Speed Manual"), "Manual")
        self.assertEqual(normalize_transmission(None), "Manual")

    def test_mecum_parse(self):
        from data.mecum_ingest import parse_transmission
        self.assertEqual(parse_transmission("7-Speed PDK"), "PDK")
        self.assertEqual(parse_transmission("Tiptronic Automatic"), "Automatic")
        self.assertEqual(parse_transmission("6-Speed Manual"), "Manual")
        self.assertEqual(parse_transmission(None), "Manual")


class TestTransaxle(unittest.TestCase):
    def test_model_line_match(self):
        self.assertEqual(match_model_line("1987 Porsche 944 Turbo"), "944")
        self.assertEqual(match_model_line("1979 Porsche 928"), "928")
        self.assertIsNone(match_model_line("1995 Porsche 993 Carrera"))

    def test_classify_returns_line_and_variant(self):
        line, variant = classify("944", "1987 Porsche 944 Turbo")
        self.assertEqual(line, "944")
        self.assertEqual(variant, "Turbo")


if __name__ == "__main__":
    unittest.main()
