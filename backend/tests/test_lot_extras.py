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
    parse_pts,
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

    def test_interior_after_over(self):
        # Broad Arrow / RM / Gooding highlight phrasing.
        self.assertEqual(parse_interior(bullets(
            "Finished in its original shade of era-evoking Light Yellow over a black interior "
            "with Shetland cloth seat inserts")), "black")
        self.assertEqual(parse_interior(bullets(
            "Finished in Sport Classic Grey over a beautiful Espresso leather interior")),
            "Espresso leather")
        self.assertEqual(parse_interior(bullets(
            "Finished in GT Silver Metallic over an Ascot Brown hide interior")), "Ascot Brown hide")
        self.assertIsNone(parse_interior(bullets(
            "Finished in White over an uncommon black leather Weissach Package interior")))
        self.assertIsNone(parse_interior(bullets(
            "Finished in Silver Metallic over a Black Competition-Focused Interior")))
        self.assertIsNone(parse_interior(bullets(
            "Finished in Paint to Sample Signal Yellow over a leather interior in Black")))


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

    def test_parts_named_clubsport_are_not_a_clubsport(self):
        for line in ("964 Clubsport Steering Wheel",
                     "Finished in Carrara White over a Black fabric and Alcantara Clubsport interior"):
            self.assertNotIn("Clubsport", parse_options("1991 Porsche 911", bullets(line)), line)
        self.assertIn("Clubsport", parse_options("1988 Porsche 911 Carrera Club Sport", None))

    def test_m471_style_conversion_is_not_lightweight(self):
        self.assertNotIn("Lightweight", parse_options(
            "1973 Porsche 911", bullets('*Detailed conversion to M471-style "Lightweight" Specs')))

    def test_interior_color_only_and_over(self):
        for line, want in (("Tan Upholstery", "Tan"), ("Cork Interior", "Cork"),
                           ("Gray, Blue, & Black Upholstery", "Gray, Blue, & Black"),
                           ("Finished in Dolomite Grey over a Black leather interior", "Black leather")):
            self.assertEqual(parse_interior(bullets(line)), want, line)

    def test_interior_needs_a_material(self):
        for line in ("Wonderfully Preserved Original Interior", "Upgraded brakes, electricals, and interior",
                     "Unique checkerboard interior"):
            self.assertIsNone(parse_interior(bullets(line)), line)

    def test_owners_manual_is_not_one_owner(self):
        self.assertEqual(parse_provenance("x", bullets(
            "Offered with Original Owner’s Manual, Maintenance Book, and Tool Kit")), [])
        self.assertEqual(parse_provenance("Original-Owner 1974 Porsche 914", None), ["One Owner"])

    def test_provenance(self):
        text = bullets("One-Owner", "Porsche Certificate of Authenticity", "Original Window Sticker")
        self.assertEqual(parse_provenance("x", text), ["One Owner", "Porsche COA", "Window Sticker"])
        self.assertEqual(parse_provenance("x", bullets("Non-matching numbers engine")), [])



class PaintToSampleTests(unittest.TestCase):
    """Real listings. PTS must be about this car's paint, or it isn't PTS."""

    def test_title_and_bullets(self):
        self.assertTrue(parse_pts("2019 Porsche 911 GT3 RS PTS", None))
        self.assertTrue(parse_pts("x", bullets("Paint-to-Sample Gulf Blue")))
        self.assertTrue(parse_pts("x", bullets("Custom-Order Metallic Purple Paint")))

    def test_prose_statements_about_this_car(self):
        for line in (
            "This 2023 Porsche 911 GT3 Touring was specified in paint-to-sample Gulf Blue with orange graphics.",
            "Finished in rare, special order non-metallic Club Blue over Alcantara.",
            "Finished in the sophisticated, rarely seen Paint to Sample shade of Macadamia Metallic.",
            "According to production records, this 'Paint-to-Sample' Metallic Night Blue over Midnight Blue.",
            "Offered here is a rare, single-owner paint-to-sample RSA, one of just four in Ferrari Yellow.",
            "L999 – Paint-to-sample finish YY – Burgundy leather upholstery.",
        ):
            self.assertTrue(parse_pts("x", bullets(prose=line)), line)

    def test_not_pts(self):
        for line in (
            "Offered by Wob Cars as part of the PTS Porsche Collection with a clean title.",
            "Porsche was always amenable to applying other colors under its pricey paint-to-sample program.",
            "Car was manufactured for the Sonderwunsch Programm, now called Exclusive.",
            "a well-specified example of Porsche's 1980s Sonderwunsch programme.",
        ):
            self.assertIsNone(parse_pts("x", bullets(prose=line)), line)
        self.assertIsNone(parse_pts("x", bullets("Special Order Black Leather Interior")))
        for line in ("Finished in Carrara White over black leather with custom-ordered Guards Red deviated stitching.",
                     "The car is finished in silver with Porsche Exclusive custom-ordered Viper Green center and side stripes.",
                     "It is today in Black over a full leather interior in special-order Natural Brown.",
                     "It was specified in Amazon Green Metallic over special-ordered Petrol Green full leather.",
                     "Speedline RS wheels decorated in the special-order shade of Amethyst Metallic."):
            self.assertIsNone(parse_pts("x", bullets(prose=line)), line)

    def test_more_pts_statements(self):
        for line in ("It was specified from the factory in paint-to-sample Platinum Metallic over Cork leather.",
                     "Additionally, the tag displays paint-to-sample code 98.",
                     "The base colour, Piet Boon Grey (now called PTS Alex Grey), is a warm-toned non-metallic."):
            self.assertTrue(parse_pts("x", bullets(prose=line)), line)
        self.assertIsNone(parse_pts("x", bullets("PTS Porsche Collection")))

    def test_leichtbau_is_lightweight(self):
        self.assertIn("Lightweight", parse_options("2023 Porsche 911 Turbo S Leichtbau", None))


if __name__ == "__main__":
    unittest.main()


class SonderwunschTests(unittest.TestCase):
    """Real phrasings from stored lots. Tag only statements about this car."""

    def test_title_and_bullets(self):
        from app.utils.lot_extras import parse_sonderwunsch as sw
        self.assertTrue(sw('1983 Porsche 911 Turbo WLS "Sonderwunsch" Slantnose Coupe', None))
        self.assertTrue(sw("Special Wishes 1987 Porsche 911 Turbo Slant Nose Coupe", None))
        self.assertTrue(sw("2022 Porsche 911 GT3", bullets("Sonderwunsch Factory Commissioning")))
        self.assertTrue(sw("2022 Porsche 911", bullets("~$49k in Sonderwunsch Options")))

    def test_prose_about_this_car(self):
        from app.utils.lot_extras import parse_sonderwunsch as sw
        for sentence in (
            "This 2018 Porsche 911 GT3 was ordered through the Sonderwunsch Factory Commissioning program.",
            "It was specified with $93k of Sonderwunsch (Special Wishes) commissioning.",
            "Finished in paint-to-sample Yachting Blue in addition to the $13k Sonderwunsch Factory Commissioning.",
            "Special Wishes options added over $30,000 to the build.",
            "This is a one owner “Special Wishes” car that was bought in Scotland.",
            "It was optioned from the factory with a Sonderwunsch interior trimmed in Saddle Brown "
            "leather with Houndstooth-style cloth inserts.",
            "Two Sonderwunsch 'Z' options were specified.",
        ):
            self.assertTrue(sw("1995 Porsche 911", join_details([], sentence)), sentence)

    def test_not_this_car(self):
        from app.utils.lot_extras import parse_sonderwunsch as sw
        for title, line in (
            ("1988 Porsche 911 Turbo", "Porsche’s Exclusive Manufaktur program—sometimes called “Sonderwunsch,” "
                                       "or “Special Wishes”—obliged with an option package."),
            ("1985 Porsche 911 Turbo", "Most were ordered from Porsche with numerous options from its Special "
                                       "Wishes department."),
            ("2015 Porsche 918 Spyder", "A “Special Wishes” extended-length external charging cable."),
            ("1993 Porsche 911 Carrera RSR 3.8", "A truly incredible car representing the physical "
                                                 "actualization of “special wishes”."),
            ("1986 Porsche 911 Turbo", "Black Interior w/ Sonderwunsch-Style Details"),
            ("1985 Porsche 930 Cabriolet", "Believed to be built as part of Porsche's Special Wishes Program"),
            ("1966 Porsche 911", "The owner also had some sonderwunsch (special request) options installed."),
            ("1990 Porsche 911 Reimagined by Singer", "Features Multiple Special Wish Options"),
            # Exclusive Custom Tailoring, described with the English translation
            ("2019 Porsche 911 Speedster", "Custom tailoring option?”special wishes"),
            ("2014 Porsche 911 Turbo S Cabriolet", "Porsche Special Wishes custom tailering option"),
            # One option code is one option, not a Sonderwunsch build
            ("1999 Porsche 911 Carrera", "09981 and 09991 option codes from the Porsche “Sonderwunsch” "
                                        "(Special Wishes) program listed on the factory options sticker"),
            ("1997 Porsche 911 Carrera S", "09991 – Car was manufactured for the Sonderwunsch Programm, "
                                           "now called Exclusive"),
        ):
            self.assertFalse(sw(title, join_details([line], line)), line)

    def test_exclusive_era_claims_are_not_sonderwunsch(self):
        from app.utils.lot_extras import parse_sonderwunsch as sw
        # Factory Commissioning began in 2021; earlier "Sonderwunsch" = Exclusive options.
        line = "This car was ordered through the Sonderwunsch factory commissioning program."
        self.assertFalse(sw("2016 Porsche 911 GT3 RS", join_details([], line), 2016))
        self.assertFalse(sw("2018 Porsche 911 GT3", join_details(["Sonderwunsch Factory Commissioning"]), 2018))
        self.assertTrue(sw("2022 Porsche 911 GT3", join_details(["Sonderwunsch Factory Commissioning"]), 2022))
        # The classic department's builds still count.
        self.assertTrue(sw('1983 Porsche 911 Turbo WLS "Sonderwunsch" Slantnose Coupe', None, 1983))
        # 1987-2020: Porsche Exclusive, even for full factory builds described as Sonderwunsch.
        self.assertFalse(sw("1988 Porsche 911 Turbo 'Flat-Nose' Coupe",
                            join_details(["Produced through Porsche’s Sonderwunsch (Special Request) program"]), 1988))
        self.assertFalse(sw('1999 Porsche 911 Classic Club Coupe "Sonderwunsch" Factory One-Off', None, 1999))
        # A special edition (Exclusive Manufaktur series) with its certificate is not a commission.
        self.assertFalse(sw("2021 Porsche 911 Targa 4S Heritage Design Edition",
                            join_details(["Accompanied by Special Wishes Certificate, build record"]), 2021))

    def test_is_an_option_label(self):
        self.assertEqual(parse_options("2022 Porsche 911 GT3",
                                       bullets("Sonderwunsch Factory Commissioning", "Burmester")),
                         ["Sonderwunsch", "Burmester"])


class PtsNotFactoryTests(unittest.TestCase):
    """PTS means a Porsche factory order. Real phrasings that are not one."""

    def test_other_builders(self):
        for title in ("1991 Porsche 911 Carrera 2 Coupe by Singer",
                      "1988 Porsche 959 SC Reimagined by Canepa",
                      "1996 Porsche 911 Remastered by Gunther Werks"):
            self.assertIsNone(parse_pts(title, join_details(["Paint-to-Sample Lunar Silver Paint"])), title)

    def test_respray_guess_and_current_colour(self):
        for line in (
            "This example was resprayed by the selling dealer in Slate Grey Metallic, a paint-to-sample color.",
            "From its color code tag it would seem that this was actually a non-standard 'paint to sample' car.",
            "Imported into the UK in 2002, the car is now in Bali Blue - a special order colour - with tan interior.",
            "Finished in Chelsea Grey, a not-so-distant cousin to Porsche’s own paint-to-sample color of China Grey.",
        ):
            self.assertIsNone(parse_pts("1996 Porsche 911", join_details([], line)), line)

    def test_still_factory(self):
        for line in (
            "The bumper holes were filled before the car was repainted in its original special-order color of Smyrna Green.",
            "The car came specified in paint-to-sample Braun and was repainted in Copper Brown Metallic.",
        ):
            self.assertTrue(parse_pts("1963 Porsche 356", join_details([], line)), line)


class SingleGearboxModelTests(unittest.TestCase):
    def d(self, title, text, year, gen, variant, line="911"):
        from app.utils.lot_extras import derive
        return derive(title, text, year, line, gen, variant)["transmission"]

    def test_model_settles_it(self):
        self.assertEqual(self.d("1987 Porsche 911 Turbo", None, 1987, "G-Body", "930 Turbo"), "Manual")
        self.assertEqual(self.d("2018 Porsche 911 GT2 RS", None, 2018, "991.2", "GT2 RS"), "PDK")
        self.assertEqual(self.d("2017 Porsche 911 Turbo S Automatic", None, 2017, "991.2", "Turbo S"), "PDK")

    def test_both_gearboxes_offered_is_not_guessed(self):
        self.assertIsNone(self.d("2018 Porsche 911 GT3", None, 2018, "991.2", "GT3"))
        self.assertIsNone(self.d("2008 Porsche 911 Turbo", None, 2008, "997.1", "Turbo"))

    def test_listing_that_contradicts_the_model_is_left_for_review(self):
        # A manual-converted 991 Turbo: the derive step says unknown, the stored value stays.
        self.assertIsNone(self.d("2013 Porsche 911 Turbo Cabriolet 6-Speed", None, 2013, "991.1", "Turbo"))


class M491Tests(unittest.TestCase):
    def test_factory_option_only(self):
        from app.utils.lot_extras import parse_m491 as m
        self.assertTrue(m("1986 Porsche 911 Carrera M491 Turbo-Look Coupe", None, 1986))
        self.assertTrue(m("1988 Porsche 911 Carrera Cabriolet", bullets("Factory M491 Turbo Look Package"), 1988))
        self.assertTrue(m("1987 Porsche 911 Carrera Supersport Coupe", None, 1987))
        self.assertFalse(m("1974 Porsche 911 Carrera Targa M491-Look", None, 1974))
        self.assertFalse(m("1983 Porsche 911SC Turbo-Look Conversion", None, 1983))
        self.assertFalse(m("1986 Porsche 911 Carrera Turbo-Look Conversion", None, 1986))
        self.assertFalse(m("1985 Porsche 911 Carrera 930-Style Widebody", None, 1985))
