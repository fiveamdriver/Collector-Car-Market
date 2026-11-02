"""
Tests for app.utils.lot_details — mileage/color extraction from lot text.

Run from the backend/ directory:
    python -m unittest discover tests -v

Cases are real phrasings from each auction house, plus the false positives the
prose rules exist to reject.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.lot_details import (
    extract,
    html_to_text,
    join_details,
    parse_color,
    parse_mileage,
    parse_odometer_value,
)


class TestBulletMileage(unittest.TestCase):
    CASES = [
        ("14k Miles Shown", 14000),                        # BaT
        ("~45k Indicated Miles", 45000),                   # BaT
        ("6,303 kilometres", 3917),                        # RM, British spelling
        ("As-New Condition with Less than 900 Total Miles", 900),  # Gooding
        ("37 Miles", 37),                                  # delivery mileage
        ("20.408 km from new", 12681),                     # European thousands
        # A service in an earlier clause doesn't disqualify the reading.
        ("Recent Service by DeMan Motorsport; Approximately 7,900 Km from New", 4909),
        ("1.5k Miles Shown", 1500),
        ("14k-Mile 1997 Porsche 911 Carrera Targa", 14000),
    ]

    def test_cases(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(parse_mileage([text]), expected)

    def test_rejects(self):
        for text in [
            "Engine rebuilt 2,000 miles ago",
            "Recent 30,000-mile service",
            "Class winner at the 1,000 Miles race",
            "TMU",
            "Odometer replaced in 1995",
            "Mileage Unknown",
            # Race distances (RM 718 RSK / 550 Wendler lot highlights)
            "1st in class wins at both the 12 Hours of Sebring and Nürburgring 1000 KM",
            "4th in class for the 1959 edition of the 500 Mile Road America",
            # Distance since work / over a period (Bonhams)
            "Fewer than 1,500 kilometres since professional restoration",
            "it remained garage stored for the next five years, covering fewer than 100 miles",
            "only about 2000 miles have been added to the total in the last four years",
            "16,000 miles since engine rebuild",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(parse_mileage([text]))


class TestProseMileage(unittest.TestCase):
    def test_needs_context(self):
        self.assertEqual(
            parse_mileage(["The odometer reads 23,456 miles."], prose=True), 23456)
        self.assertEqual(
            parse_mileage(["It shows 14k miles and has been registered in Texas."], prose=True), 14000)
        # A later clause about service history doesn't disqualify the reading.
        self.assertEqual(parse_mileage(
            ["this right-hand drive example has covered circa 107,000 miles from new and comes "
             "with full Porsche service history up to 80,000 miles"], prose=True), 107000)
        # A bare figure in prose is not trusted.
        self.assertIsNone(
            parse_mileage(["It was driven to the 500 miles of Riverside in 1966."], prose=True))
        self.assertIsNone(
            parse_mileage(["The car was trailered 1,200 miles to the show."], prose=True))


class TestOdometerValue(unittest.TestCase):
    def test_values(self):
        self.assertEqual(parse_odometer_value("37", "M"), 37)       # was dropped by the old >=100 floor
        self.assertEqual(parse_odometer_value("16,093", "K"), 10000)
        self.assertIsNone(parse_odometer_value("0", "M"))
        self.assertIsNone(parse_odometer_value("", "M"))
        self.assertIsNone(parse_odometer_value(None, None))


class TestColor(unittest.TestCase):
    CASES = [
        (["Black Paint"], "Black"),                                       # BaT
        (["Paint-To-Sample Mint Green Paint"], "Mint Green"),             # BaT PTS
        (["Finished in Guards Red over Black Leather"], "Guards Red"),    # RM / Gooding
        (["Paint to Sample Gulf Blue over Ascot Brown interior"], "Gulf Blue"),  # Broad Arrow
        (["This 1997 Porsche 911 Carrera is a black-over-Cashmere Targa"], "Black"),  # BaT excerpt
        # Specific names are kept, not reduced to the generic color inside them.
        (["Fluid Silver Paint"], "Fluid Silver"),
        (["One of 11 959 Sports finished in Grand Prix White over a Grey cloth interior"],
         "Grand Prix White"),
    ]

    def test_long_bullets(self):
        self.assertEqual(parse_color(["One of ~44 w/Fayence Yellow Paint"], bullets=True),
                         "Fayence Yellow")
        # Gooding GT1 highlight
        self.assertEqual(parse_color(
            ["Highly Original Example in Iconic Arctic Silver over Black Color Scheme"],
            bullets=True), "Arctic Silver")
        # BaT 918 Salzburg: the graphics color must not win
        self.assertEqual(parse_color(["Salzburg Livery", "White Paint w/Black Graphics"],
                                     bullets=True), "White")

    def test_specific_bullet_names(self):
        self.assertEqual(parse_color(["Paint-to-Sample Oryx White"], bullets=True), "Oryx White")
        self.assertEqual(parse_color(["Dark Blue Metallic"], bullets=True), "Dark Blue Metallic")

    def test_description_words_trimmed(self):
        self.assertEqual(parse_color(
            ["The car is finished in the signature 996 Turbo Arctic Silver with black leather"]),
            "Arctic Silver")
        self.assertEqual(parse_color(["Superb Pastel Blue colour scheme from new"], bullets=True),
                         "Pastel Blue")

    def test_gooding_highlight_phrasings(self):
        self.assertEqual(parse_color(
            ["Original Irish Green Paint and Numbers-Matching Engine per Porsche COA"],
            bullets=True), "Irish Green")
        self.assertEqual(parse_color(
            ["Fully Restored by Marque Specialists in Original Black over Black Color Scheme"],
            bullets=True), "Black")

    def test_current_color_over_original(self):
        # RM 356 Speedster: factory Signal Red, since re-finished in Sky Blue.
        self.assertEqual(parse_color([
            "It left the factory wearing Signal Red paint with a black leatherette interior.",
            "During its restoration, it was re-finished in the model-and-year-correct color "
            "scheme of 602 Speedster/Sky Blue with a light tan interior.",
        ]), "Sky Blue")

    def test_soft_top_is_not_the_paint(self):
        self.assertIsNone(parse_color(["The convertible soft top was finished in Dark Blue."]))
        # ...but a part named in an earlier clause doesn't block the paint.
        self.assertEqual(parse_color([
            "Delivered new in rare factory-correct Agua Blue over black upholstery, "
            "now presented in striking Ruby Red."]), "Ruby Red")
        self.assertEqual(parse_color([
            "Restored Fiberglass Body with 911E Steel Roof Section, Finished in Gulf Racing Blue"]),
            "Gulf Racing Blue")
        self.assertEqual(parse_color([
            "the car (and its Fuchs wheels) had been refinished in the period shade of Bahia Red"]),
            "Bahia Red")

    def test_surname_is_not_a_color(self):
        self.assertIsNone(parse_color(["210hp 2,500cc engine built by Porsche Specialist Dave Brown"],
                                      bullets=True))

    def test_finished_in_a_race_is_not_a_color(self):
        self.assertIsNone(parse_color(["The car finished in the Targa Florio that May"]))
        self.assertIsNone(parse_color(["The third car finished in 17th place"]))

    def test_cases(self):
        for frags, expected in self.CASES:
            with self.subTest(frags=frags):
                self.assertEqual(parse_color(frags), expected)

    def test_interior_bullet_is_not_paint(self):
        self.assertIsNone(parse_color(["Black Leather Upholstery"], bullets=True))
        self.assertIsNone(parse_color(["Silver Fuchs Wheels"], bullets=True))

    def test_loose_over_pattern_needs_known_color(self):
        self.assertIsNone(parse_color(["Restored over three years by the marque specialist"]))


class TestExtract(unittest.TestCase):
    def test_bat_listing_details(self):
        text = join_details([
            "Chassis: WP0DA2991VS385432", "14k Miles Shown", "3.6-Liter Flat-Six",
            "Six-Speed Manual Transaxle", "Black Paint", "Cashmere Leather Upholstery",
        ])
        self.assertEqual(extract(text), {
            "mileage": 14000, "exterior_color": "Black", "paint_to_sample": None,
        })

    def test_bullets_win_over_prose(self):
        text = join_details(
            ["6,303 kilometres", "Paint-to-Sample Speed Yellow"],
            "Five years later it was acquired with only 1,750 kilometres showing.",
        )
        out = extract(text)
        self.assertEqual(out["mileage"], 3917)
        self.assertTrue(out["paint_to_sample"])

    def test_prose_only(self):
        text = join_details(None, html_to_text(
            "<p>Finished in Slate Grey over black.</p><p>The odometer shows 8,900 km.</p>"))
        out = extract(text)
        self.assertEqual(out["exterior_color"], "Slate Grey")
        self.assertEqual(out["mileage"], 5530)

    def test_empty(self):
        self.assertEqual(extract(None),
                         {"mileage": None, "exterior_color": None, "paint_to_sample": None})


if __name__ == "__main__":
    unittest.main()
