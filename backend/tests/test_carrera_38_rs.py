"""'Carrera 3.8 RS' word order (Gooding's 993 titles) - 2026-11-08 misfiles."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.variants import is_964_rs_38, match_variant  # noqa: E402

PATTERNS_993 = ["Carrera RS", "Carrera 4S", "Carrera S", "Carrera 4", "Turbo S", "Turbo", "GT2", "Carrera"]


class Carrera38RS(unittest.TestCase):
    def test_993_carrera_38_rs_is_the_rs(self):
        self.assertEqual(match_variant(PATTERNS_993, "1996 Porsche 993 Carrera 3.8 RS"), "Carrera RS")
        self.assertEqual(match_variant(PATTERNS_993, "1995 Porsche 993 Carrera 3.8 RS"), "Carrera RS")

    def test_usual_word_order_unchanged(self):
        self.assertEqual(match_variant(PATTERNS_993, "1995 Porsche 911 Carrera RS"), "Carrera RS")
        self.assertEqual(match_variant(PATTERNS_993, "1996 Porsche 993 Carrera"), "Carrera")

    def test_tribute_is_not_promoted(self):
        self.assertEqual(match_variant(PATTERNS_993, "1996 Porsche 911 Carrera 3.8 RS Tribute"), "Carrera")
        self.assertEqual(match_variant(PATTERNS_993, "RS-Style 1995 Porsche 911 Carrera Coupe 3.8L"), "Carrera")

    def test_964_word_order_is_the_rs_38(self):
        self.assertTrue(is_964_rs_38("1992 Porsche 964 Carrera 3.8 RS"))
        self.assertTrue(is_964_rs_38("1993 Porsche 911 Carrera RS 3.8"))
        self.assertFalse(is_964_rs_38("1992 Porsche 964 Carrera 3.8 RS Conversion"))


if __name__ == "__main__":
    unittest.main()
