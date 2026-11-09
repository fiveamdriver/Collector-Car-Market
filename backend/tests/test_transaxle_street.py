"""Owner rule 2026-11-08: if it is street legal, it is not a race car."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.transaxle import classify  # noqa: E402


class StreetNotRace(unittest.TestCase):
    def test_registered_prototypes_stay_on_the_street_line(self):
        self.assertEqual(classify("928", "1987 Porsche 928 S4 Club Sport 'Prototype'"), ("928", "Club Sport"))
        self.assertEqual(classify("968", "1992 Porsche 968 Turbo S Prototype"), ("968", "Turbo S"))

    def test_restoration_challenge_is_not_a_race_series(self):
        self.assertEqual(classify("944", "Porsche Classic Restoration Challenge 1988 Porsche 944 Turbo S"),
                         ("944", "Turbo S"))

    def test_race_cars_still_go_to_the_race_line(self):
        self.assertEqual(classify("944", "1986 Porsche 944 Turbo Cup"), ("944 Race", "Turbo Cup"))
        self.assertEqual(classify("924", "1981 Porsche 924 Carrera GTR"), ("924 Race", "Carrera GTR"))
        self.assertEqual(classify("944", "1990 Porsche 944 S2 Challenge Race Car")[0], "944 Race")
        self.assertEqual(classify("968", "1993 Porsche 968 Turbo RS"), ("968 Race", "Turbo RS"))


if __name__ == "__main__":
    unittest.main()
