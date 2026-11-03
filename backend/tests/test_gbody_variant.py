"""
G-Body 911 filing (app.utils.variants.gbody_variant). Every case is a real
auction title that was misfiled before 2026-11-02.

Run from the backend/ directory:
    python -m unittest tests.test_gbody_variant -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.variants import cabriolet_variant, gbody_variant as g


class GBodyVariantTests(unittest.TestCase):
    def check(self, cases):
        for title, year, want in cases:
            self.assertEqual(g(title, year), want, title)

    def test_capitalised_titles(self):
        # "SC" inside "PORSCHE" used to file these as SCs.
        self.check([("1974 PORSCHE 911 CARRERA COUPE Chassis no. 9114400199", 1974, "Carrera 2.7"),
                    ("1974 PORSCHE CARRERA RS 3.0", 1974, "Carrera RS 3.0"),
                    ("1989 PORSCHE 911 CARRERA SPEEDSTERVIN. WP0EB0911KS173142", 1989, "Speedster")])

    def test_early_carreras(self):
        self.check([("1974 Porsche 911 Carrera 3.0 RS", 1974, "Carrera RS 3.0"),
                    ("RoW 1977 Porsche 911 Carrera 3.0 Targa", 1977, "Targa"),
                    ("1976 Porsche 911 Carrera 3.0", 1976, "Carrera 3.0"),
                    ("1975 Porsche 911 Carrera 3.0 'IROC Recreation'", 1975, "Carrera 2.7")])

    def test_plain_911_by_model_year(self):
        self.check([("1980 Porsche 911", 1980, "SC"), ("1985 Porsche 911 Coupe", 1985, "Carrera 3.2"),
                    ("1976 Porsche 911 Coupe", 1976, "911")])

    def test_sc_titles_stay_sc(self):
        self.check([("1984 Porsche 911 SC RS Gruppe B “Evolutionsserie”", 1984, "SC RS"),
                    ("1977 Porsche 911 SC 3.0-Litre Coupé", 1977, "SC"),
                    ("Turbocharged 1982 Porsche 911SC Cabriolet Slant Nose", 1982, "SC"),
                    ("1977 Porsche 911 SCCA Race Car", 1977, "911")])

    def test_user_decisions_2026_11_02(self):
        # Targas go on the Targa card whatever the engine; the 930 keeps its own.
        self.check([("1974 Porsche 911 Carrera 2.7 MFI Targa", 1974, "Targa"),
                    ("1980 Porsche 911SC Targa", 1980, "Targa"),
                    ("1989 Porsche 911 Carrera Targa", 1989, "Targa"),
                    ("1987 Porsche 911 Turbo Targa", 1987, "930 Turbo"),
                    # Club Sport and SC RS have their own cards; M491 stays on its trim card.
                    ("1988 Porsche 911 Carrera Club Sport", 1988, "Carrera 3.2 Club Sport"),
                    ("1987 Porsche 911 Carrera Clubsport-Style Coupe", 1987, "Carrera 3.2"),
                    ("1984 Porsche 911 SC/RS", 1984, "SC RS"),
                    ("1986 Porsche 911 Carrera M491 Turbo-Look Coupe", 1986, "Carrera 3.2"),
                    # Factory Flat-Nose Turbos (however it is spelled) vs. a converted Carrera
                    ("1989 PORSCHE 930 TURBO FLACHBAU CABRIOLET", 1989, "Turbo 3.3 Slant Nose"),
                    ("1988 Porsche 911 Turbo 'Flat-Nose' Cabriolet", 1988, "Turbo 3.3 Slant Nose"),
                    ("1984 Porsche 911 Carrera 3.2 Coupe 'Flat-Nose' conversion", 1984, "Carrera 3.2"),
                    ("1976 Porsche 911 Carrera 3.0 Targa Engine type 930/02", 1976, "Targa")])

    def test_conversions_go_to_their_chassis(self):
        self.check([("Strosek-Style RoW 1984 Porsche 911 Carrera Speedster Conversion", 1984, "Carrera 3.2"),
                    ("25-Years-Owned 993 Turbo-Powered 1987 Porsche 911", 1987, "Carrera 3.2"),
                    ("1974 Porsche 930 Slant Nose Cabriolet", 1974, "911")])
        # The factory G-Body Cabriolet starts with MY1983.
        self.assertEqual(cabriolet_variant("G-Body", "SC", "1979 Porsche 911SC Cabriolet Conversion", 1979), "SC")
        self.assertEqual(cabriolet_variant("G-Body", "SC", "1983 Porsche 911SC Cabriolet", 1983), "Cabriolet")


if __name__ == "__main__":
    unittest.main()
