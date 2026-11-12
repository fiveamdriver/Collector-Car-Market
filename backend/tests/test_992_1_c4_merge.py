"""992.1 has no Carrera 4 card: C4 -> Carrera, a 4S title -> Carrera 4S; 992.2 unchanged."""
import unittest

from app.utils.cards_911 import target_variant
from app.utils.variants import cabriolet_variant


class Test9921CarreraFourMerge(unittest.TestCase):
    def test_c4_coupe_goes_to_carrera(self):
        self.assertEqual(cabriolet_variant(
            "992.1", "Carrera 4", "5k-Mile 2021 Porsche 911 Carrera 4 Coupe", 2021), "Carrera")

    def test_4s_title_stamped_c4_goes_to_4s(self):
        self.assertEqual(cabriolet_variant(
            "992.1", "Carrera 4", "2022 Porsche 911 Carrera 4S Coupe", 2022), "Carrera 4S")

    def test_c4_cabriolet_still_cabriolet(self):
        self.assertEqual(cabriolet_variant(
            "992.1", "Carrera 4", "2021 Porsche 911 Carrera 4 Cabriolet", 2021), "Cabriolet")

    def test_992_2_keeps_c4(self):
        self.assertEqual(cabriolet_variant(
            "992.2", "Carrera 4", "2025 Porsche 911 Carrera 4 Coupe", 2025), "Carrera 4")

    def test_refile_into_992_1(self):
        self.assertEqual(target_variant("Carrera 4", "992.1"), "Carrera")
        self.assertEqual(target_variant("Carrera 4", "992.2"), "Carrera 4")


if __name__ == "__main__":
    unittest.main()
