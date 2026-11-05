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


from app.utils.variants import cabriolet_variant  # noqa: E402


class TargaCardTests(unittest.TestCase):
    def test_drivetrain_stamped_targas_move(self):
        self.assertEqual(cabriolet_variant("964", "Carrera 2", "1991 Porsche 911 Carrera 2 Targa 5-Speed", 1991), "Targa")
        self.assertEqual(cabriolet_variant("964", "Carrera 4", "1990 Porsche 911 Carrera 4 Targa", 1990), "Targa")
        self.assertEqual(cabriolet_variant("993", "Carrera", "1997 Porsche 911 Carrera Targa 6-Speed", 1997), "Targa")
        self.assertEqual(cabriolet_variant("997.1", "Carrera 4S", "2007 Porsche 911 Targa 4S 6-Speed", 2007), "Targa")

    def test_cards_without_targa_left_alone(self):
        self.assertEqual(cabriolet_variant("996.1", "Carrera", "2000 Porsche 911 Carrera Targa", 2000), "Carrera")
        self.assertEqual(cabriolet_variant("964", "Turbo 3.3", "1991 Porsche 911 Turbo Targa", 1991), "Turbo 3.3")

    def test_cabriolet_and_coupe_unchanged(self):
        self.assertEqual(cabriolet_variant("964", "Carrera 2", "1992 Porsche 911 Carrera 2 Cabriolet", 1992), "Cabriolet")
        self.assertEqual(cabriolet_variant("964", "Carrera 2", "1992 Porsche 911 Carrera 2 Coupe", 1992), "Carrera 2")


class C4LeichtbauTests(unittest.TestCase):
    def test_c4_leichtbau(self):
        self.assertEqual(fix_964_carrera("Carrera 4", "1991 Porsche 911 Carrera 4 Lightweight", 1991), "Carrera 4 Leichtbau")
        self.assertEqual(fix_964_carrera("Carrera 2", "1990 Porsche Carrera 4RS Lightweight Chassis no. 964019", 1990), "Carrera 4 Leichtbau")
        self.assertEqual(fix_964_carrera("Carrera 4", "1990 Porsche 964 Carrera 4 Leichtbau", 1990), "Carrera 4 Leichtbau")

    def test_not_c4_leichtbau(self):
        self.assertEqual(fix_964_carrera("Carrera 4", "1991 Porsche 911 Carrera 4 Coupe", 1991), "Carrera 4")
        self.assertEqual(fix_964_carrera("Carrera 4", "1991 Porsche 911 Carrera 4 Lightweight Tribute", 1991), "Carrera 4")
        self.assertEqual(fix_964_carrera("Turbo S", "1993 Porsche 964 Turbo S Leichtbau", 1993), "Turbo S")


class TurboSCardTests(unittest.TestCase):
    def test_turbo_s_titles(self):
        self.assertEqual(cabriolet_variant("996.2", "Turbo", "2005 Porsche 911 Turbo S Coupe 6-Speed", 2005), "Turbo S")
        self.assertEqual(cabriolet_variant("997.2", "Cabriolet", "2012 Porsche 911 Turbo S Cabriolet", 2012), "Turbo S")
        self.assertEqual(cabriolet_variant("993", "Turbo", "Last of the air-cooled Turbos, 1997 PORSCHE 911 TURBO", 1997), "Turbo")
        self.assertEqual(cabriolet_variant("997.1", "Turbo", "2008 Porsche 911 Turbo S-style wheels", 2008), "Turbo")
