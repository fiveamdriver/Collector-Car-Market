"""
Exterior colour must never be the interior (or calipers, piping, a wrap...).
Each case is a real lot that was stored wrong before 2026-11-03.

Run from backend/:  ../venv/bin/python -m unittest tests.test_exterior_colour -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.color_parser import parse_exterior_color
from app.utils.lot_details import extract, parse_color


class TestNeverTheInterior(unittest.TestCase):
    def test_mecum_labelled_exterior_beats_interior(self):
        text = "SPECIFICATIONS\nEXTERIOR COLOR\nBurgundy\nINTERIOR COLOR\nBrown\nHIGHLIGHTS\nLeather interior"
        self.assertEqual(extract(text)["exterior_color"], "Burgundy")

    def test_mecum_labelled_exterior_with_interior_highlight(self):
        text = ("SPECIFICATIONS\nEXTERIOR COLOR\nCarrara White\nINTERIOR COLOR\nRed\n"
                "Carrara White Metallic with Garnet Red natural leather interior")
        self.assertEqual(extract(text)["exterior_color"], "Carrara White")

    def test_rm_subtitle_interior_is_not_paint(self):
        # RM subtitles name the cabin, calipers and wraps; none of them is the paint.
        self.assertIsNone(parse_color(["Factory Matte Black wrap and Martini livery"], bullets=True))
        self.assertIsNone(parse_color(["Rare black-painted brake calipers"], bullets=True))

    def test_paint_over_interior(self):
        self.assertEqual(parse_color(["Clad in an ideal Guards Red exterior over a Graphite Grey cabin"]), "Guards Red")
        self.assertEqual(parse_color(["Titanium Metallic over Black Leather"]), "Titanium Metallic")


class TestNotAColour(unittest.TestCase):
    def test_title_descriptors_stripped(self):
        self.assertEqual(parse_exterior_color("Original-Owner Silver Metallic 1995 Porsche 911 Carrera 4 Coupe"), "Silver Metallic")
        self.assertEqual(parse_exterior_color("Repainted Black 1990 Porsche 911 Carrera 2"), "Black")
        self.assertEqual(parse_exterior_color("Speed Yellow 2024 Porsche 911 GT3 RS"), "Speed Yellow")

    def test_marketing_adjectives_stripped(self):
        self.assertEqual(parse_color(["Finished in Striking Zanzibar Red Metallic"], bullets=True), "Zanzibar Red Metallic")
        self.assertEqual(parse_color(["Finished in Definitive Speed Yellow"], bullets=True), "Speed Yellow")

    def test_no_colour_named(self):
        for f in ("Finished in Original Color Scheme", "Finished in Rare Color Combination",
                  "One of Only Three 904s Originally Painted Orange"):
            with self.subTest(f=f):
                self.assertIsNone(parse_color([f], bullets=True))


if __name__ == "__main__":
    unittest.main()
