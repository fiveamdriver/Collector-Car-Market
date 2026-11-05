"""964 Turbo 3.3 vs 3.6 cards (app/utils/variants.split_964_turbo via fix_964_carrera).

Run from backend/:  python -m unittest tests.test_964_turbo_split -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.variants import fix_964_carrera  # noqa: E402


class Turbo964Tests(unittest.TestCase):
    def test_by_model_year(self):
        self.assertEqual(fix_964_carrera("Turbo", "1991 Porsche 911 Turbo", 1991), "Turbo 3.3")
        self.assertEqual(fix_964_carrera("Turbo", "1992 Porsche 911 Turbo 3.3", 1992), "Turbo 3.3")
        self.assertEqual(fix_964_carrera("Turbo", "1993 Porsche 911 Turbo 3.6", 1993), "Turbo 3.6")
        self.assertEqual(fix_964_carrera("Turbo", "1994 Porsche 911 Turbo", 1994), "Turbo 3.6")

    def test_3_6_wheels_on_a_3_3_do_not_move_it(self):
        self.assertEqual(fix_964_carrera("Turbo", "1992 Porsche 911 Turbo, Turbo 3.6 Speedline wheels", 1992), "Turbo 3.3")

    def test_base_promoted_then_split(self):
        self.assertEqual(fix_964_carrera("base", "1994 Porsche 911 Turbo Coupe", 1994), "Turbo 3.6")

    def test_turbo_s_untouched(self):
        self.assertEqual(fix_964_carrera("Turbo S", "1994 Porsche 911 Turbo S 3.6", 1994), "Turbo S")

    def test_without_year_unchanged(self):
        self.assertEqual(fix_964_carrera("Turbo", "1994 Porsche 911 Turbo"), "Turbo")


if __name__ == "__main__":
    unittest.main()
