"""Regression tests for exact-colour extraction (2026-11-04)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
import refine_colours as rc  # noqa: E402


class ExteriorNames(unittest.TestCase):
    def t(self, line, want):
        self.assertEqual(rc.exterior_names(line), want, line)

    def test_mecum_highlight(self):
        self.t("Basalt Black Metallic paint with leather Onyx Black interior with Acid Green piping",
               ["Basalt Black Metallic"])

    def test_sentence_start_finished(self):
        self.t("Finished in Cream White over black", ["Cream White"])

    def test_bat_capitalised_paint_bullet(self):
        self.t("Rubystone Paint", ["Rubystone Red"])          # never adds 'Metallic' (G4 is solid)

    def test_german_name(self):
        self.t("Indischrot Paint", ["Guards Red"])

    def test_misspelling(self):
        self.t("Azurro California Paint", ["Azzurro California"])

    def test_family_word_never_grows(self):
        self.t("Red Paint", [])                               # not 'Red Orange'

    def test_descriptions_are_not_names(self):
        self.t("the red-orange paint", [])

    def test_interior_ignored(self):
        self.t("Black leather interior with Red piping", [])


class Truncations(unittest.TestCase):
    def test_partial_name_rejected(self):
        self.assertEqual(rc.exterior_names("Paint-to-Sample Urban Bamboo ChromaFlair"), [])

    def test_interior_onyx_rejected(self):
        self.assertIsNone(rc.decide(None, "Onyx Black interior with Acid Green trim")[1])

    def test_model_word_names_rejected(self):
        self.assertIsNone(rc.decide("Orange", "2007 GT3 RS Orange")[1])

    def test_model_after_colour_ok(self):
        self.assertEqual(rc.decide("Red", "One owner Guards Red Speedster")[1], "Guards Red")

    def test_family_line_scan(self):
        self.assertEqual(rc.decide("Red", "One of 10 produced in special order Coral Red Metallic")[1], "Coral Red Metallic")
        self.assertIsNone(rc.decide("Red", "Front and rear bumper guards\nRed seat belts")[1])


class Decide(unittest.TestCase):
    def test_refine_keeps_family(self):
        self.assertEqual(rc.decide("Black", "Basalt Black Metallic paint")[1], "Basalt Black Metallic")

    def test_refine_never_changes_family(self):
        self.assertIsNone(rc.decide("Black", "Guards Red paint")[1])


if __name__ == "__main__":
    unittest.main()
