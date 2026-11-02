"""
Tests for app.utils.lot_extras — transmission, chassis, interior, options and
provenance from a lot's title and bullets. Cases are real phrasings.

Run from the backend/ directory:
    python -m unittest tests.test_lot_extras -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.lot_details import join_details
from app.utils.lot_extras import (
    parse_chassis, parse_interior, parse_options, parse_provenance, parse_transmission,
)


def bullets(*lines, prose=None):
    return join_details(list(lines), prose)


class TransmissionTests(unittest.TestCase):
    def t(self, title, text=None, year=None, line="911"):
        return parse_transmission(title, text, year, line)

    def test_bullets(self):
        self.assertEqual(self.t("2018 Porsche 911 GT3", bullets("Six-Speed Manual Transaxle")), "Manual")
        self.assertEqual(self.t("2018 Porsche 911 GT3", bullets("Seven-Speed PDK Gearbox")), "PDK")
        self.assertEqual(self.t("2004 Porsche Cayenne", bullets("Six-Speed Tiptronic S Automatic Transaxle"),
                                line="Cayenne"), "Automatic")
        # BaT's misspellings.
        self.assertEqual(self.t("x", bullets("6-Speed Manual Tansaxle")), "Manual")

    def test_pdk_described_as_automatic_is_pdk(self):
        self.assertEqual(self.t("2016 Porsche 911 GT3 RS",
                                bullets("7-Speed PDK Dual-Clutch Automatic Transaxle")), "PDK")
        self.assertEqual(self.t("2021 Porsche 911 Turbo S Coupe",
                                bullets("Eight-Speed Dual-Clutch Automatic Transaxle")), "PDK")

    def test_title_speed_is_manual_including_991_seven_speed(self):
        # The old BaT title parser called every "7-Speed" a PDK.
        self.assertEqual(self.t("2017 Porsche 911 Targa 4S 7-Speed"), "Manual")
        self.assertEqual(self.t("1995 Porsche 911 Carrera Coupe 6-Speed"), "Manual")
        self.assertEqual(self.t("2009 Porsche 911 Carrera S 7-Speed PDK"), "PDK")

    def test_noise_is_not_a_gearbox(self):
        text = bullets("Dual-Zone Automatic Climate Control",
                       "Offered with Owner's Manual, Warranty Book, COA, and Tools")
        self.assertIsNone(self.t("2005 Porsche 911 Carrera", text, 2005))

    def test_prose_is_ignored(self):
        text = bullets(prose="Unlike the PDK cars that followed, the earlier ones...")
        self.assertIsNone(self.t("2010 Porsche 911 Carrera", text, 2010))

    def test_unknown_is_none_not_manual(self):
        self.assertIsNone(self.t("2019 Porsche 911 GT3 RS", None, 2019))

    def test_conflict_is_none(self):
        self.assertIsNone(self.t("x", bullets("Six-Speed Manual Transaxle", "Seven-Speed PDK Gearbox")))

    def test_mecum_spec_block(self):
        text = bullets("SPECIFICATIONS", "TRANSMISSION", "5-Speed", "EXTERIOR COLOR", "White")
        self.assertEqual(self.t("1986 Porsche 911 Slant Nose Cabriolet", text, 1986), "Manual")
        # A bare "4-Speed" on a 928 may be its automatic.
        text = bullets("TRANSMISSION", "4-Speed")
        self.assertIsNone(self.t("1985 Porsche 928", text, 1985, "928"))

    def test_automatic_in_the_pdk_era_is_pdk(self):
        # Mecum's field says "Automatic" for a 2019 GT3 RS, which is PDK-only.
        self.assertEqual(parse_transmission("2019 Porsche 911 GT3 RS", bullets("Automatic"), 2019, "911"), "PDK")
        self.assertEqual(parse_transmission("2004 Porsche 911 Carrera", bullets("Automatic"), 2004, "911"),
                         "Automatic")
        self.assertEqual(parse_transmission("2016 Porsche Cayenne", bullets("Automatic"), 2016, "Cayenne"),
                         "Automatic")

    def test_single_gearbox_cars(self):
        self.assertEqual(self.t("1964 Porsche 356C", None, 1964, "356"), "Manual")
        self.assertEqual(self.t("1966 Porsche 911", None, 1966), "Manual")
        self.assertEqual(self.t("2005 Porsche Carrera GT", None, 2005, "Carrera GT"), "Manual")
        self.assertEqual(self.t("2015 Porsche 918 Spyder", None, 2015, "918 Spyder"), "PDK")
        self.assertIsNone(self.t("1972 Porsche 911T", None, 1972))   # Sportomatic existed


class ChassisInteriorTests(unittest.TestCase):
    def test_chassis(self):
        self.assertEqual(parse_chassis(bullets("Chassis: WP0BB2A92FS133089")), "WP0BB2A92FS133089")
        self.assertEqual(parse_chassis(bullets("Chassis no. 911 720 1892")), "911 720 1892")
        # RM pages keep the labels but not the values.
        self.assertIsNone(parse_chassis(bullets("Chassis No. Engine No")))

    def test_interior(self):
        self.assertEqual(parse_interior(bullets("Black Leather & Race-Tex Upholstery")),
                         "Black Leather & Race-Tex")
        self.assertEqual(parse_interior(bullets("INTERIOR COLOR", "Tan", "MAKE", "Porsche")), "Tan")
        self.assertEqual(parse_interior(bullets("Interior: Black")), "Black")
        self.assertIsNone(parse_interior(bullets("Refreshed Interior")))
        self.assertIsNone(parse_interior(bullets("New Black sport interior including headliner")))


class OptionsProvenanceTests(unittest.TestCase):
    def test_options(self):
        text = bullets("Ceramic Composite Brakes", "Sport Chrono Package", "Front-Axle Lift System")
        self.assertEqual(parse_options("2019 Porsche 911 GT3 RS Weissach", text),
                         ["Weissach", "PCCB", "Sport Chrono", "Front-Axle Lift"])

    def test_weissach_the_place_is_not_the_package(self):
        for line in ("Weissach award at the 2014 Monterey Porsche Parade",
                     "Includes a personal tour of the Weissach facilities in Germany",
                     "4.5-liter water-cooled V-8 with a Weissach five-speed transaxle",
                     "One of 39 hand built Weissach racecars"):
            self.assertNotIn("Weissach", parse_options("1979 Porsche 928", bullets(line)), line)
        self.assertIn("Weissach", parse_options("1980 Porsche 911 SC",
                                                bullets("One of 408 Weissach Special Edition cars")))

    def test_gt3_touring_title(self):
        self.assertIn("Touring Package", parse_options("2018 Porsche 911 GT3 Touring 6-Speed", None))

    def test_provenance(self):
        text = bullets("One-Owner", "Porsche Certificate of Authenticity", "Original Window Sticker")
        self.assertEqual(parse_provenance("x", text), ["One Owner", "Porsche COA", "Window Sticker"])
        self.assertEqual(parse_provenance("x", bullets("Non-matching numbers engine")), [])


if __name__ == "__main__":
    unittest.main()
