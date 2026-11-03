"""
Tests for app.utils.ptsrs — PTSRS caption parsing. Captions are the real
opening sentences seen on @ptsrs (trimmed).

Run from the backend/ directory:
    python -m unittest tests.test_ptsrs -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.ptsrs import parse_caption


class PtsrsCaptionTests(unittest.TestCase):
    def test_full_format_with_year(self):
        e = parse_caption("🇺🇸 Presenting this Paint to Sample Alex Grey (alexgrau; non-metallic UNI; Z58) "
                          "2026 Porsche 911 (992.2) GT3 Touring. Delivered to @championporsche in Pompano Beach")
        self.assertEqual((e.colour, e.german_name, e.finish, e.paint_code), ("Alex Grey", "alexgrau", "non-metallic UNI", "Z58"))
        self.assertEqual((e.model_year, e.model, e.generation, e.variant), (2026, "911", "992.2", "GT3 Touring"))
        self.assertEqual(e.tier, "Paint to Sample")

    def test_package_is_not_part_of_the_variant(self):
        e = parse_caption("🇨🇦 Presenting this Paint to Sample Malachite Green Metallic (malachitgrünmetallic; 2B5) "
                          "Porsche 911 (992.1) GT3 RS with Weissach Package. Delivered to @porschecentrevaughan")
        self.assertEqual((e.colour, e.german_name, e.paint_code), ("Malachite Green Metallic", "malachitgrünmetallic", "2B5"))
        self.assertIsNone(e.finish)
        self.assertEqual((e.generation, e.variant, e.extra), ("992.1", "GT3 RS", "with Weissach Package"))

    def test_brand_new_and_comma(self):
        e = parse_caption("🇺🇸 Presenting this brand new Paint to Sample Nato Olive (natooliv; non-metallic UNI; L6H) "
                          "Porsche 911 (992.2) GT3, delivered to @porschemobileal in Mobile")
        self.assertEqual((e.colour, e.paint_code, e.generation, e.variant), ("Nato Olive", "L6H", "992.2", "GT3"))

    def test_adjectives_interior_and_no_generation(self):
        e = parse_caption("🇺🇸 Presenting this very special Paint to Sample Gulf Blue (gulfblau; non-metallic UNI; 328) "
                          "over Ascot Brown 2005 Porsche Carrera GT. Very excited to announce")
        self.assertEqual((e.colour, e.paint_code, e.interior, e.model_year), ("Gulf Blue", "328", "Ascot Brown", 2005))
        self.assertEqual((e.model, e.generation, e.variant), ("Carrera GT", None, None))

    def test_anniversary_post_is_not_a_car(self):
        self.assertIsNone(parse_caption("🎂 Today marks 10 years of PTSRS. A decade of documenting my fascination "
                                        "for colorful Porsches. 10 years ago today, I started @ptsrs to document "
                                        "as many Paint to Sample Porsche 991 as I could"))

    def test_2022_short_format(self):
        e = parse_caption("Presenting this brand new PTS Signal Yellow (signalgelb; non-metallic UNI; 1YH, formerly 114) "
                          "992 GT3, delivered to @porschenaples in Naples, Florida.")
        self.assertEqual((e.colour, e.german_name, e.paint_code, e.former_code), ("Signal Yellow", "signalgelb", "1YH", "114"))
        self.assertEqual((e.model, e.generation, e.variant), ("911", "992", "GT3"))
        e = parse_caption("Here is a PTS Bahama Yellow (bahamagelb; non-metallic UNI; Z14) 992 Targa 4 shared with us by @samuel")
        self.assertEqual((e.colour, e.paint_code, e.generation, e.variant), ("Bahama Yellow", "Z14", "992", "Targa 4"))
        e = parse_caption("Presenting this stunning PTS Oslo Blue (osloblau; non-metallic UNI; Z77) 992 GT3 with Touring Package, "
                          "delivered to @centroporschebolzano")
        self.assertEqual((e.variant, e.extra), ("GT3", "with Touring Package"))
        e = parse_caption("Reader Deliveries: Congratulations to Eric on the arrival of his brand new PTS Gulf Orange "
                          "(non-metallic UNI; 2G0, formerly 019) 992 GT3, delivered to @circleporsche")
        self.assertEqual((e.colour, e.german_name, e.paint_code, e.former_code), ("Gulf Orange", None, "2G0", "019"))

    def test_not_a_pts_porsche(self):
        self.assertIsNone(parse_caption("🇯🇵 Best @luftgekuhlt ever. Over a decade in the works."))
        # A Porsche colour on another brand is not evidence about a Porsche.
        self.assertIsNone(parse_caption("🇧🇪 A BMW M3 Touring in a Porsche color. Presenting this stunning BMW "
                                        "Individual Macadamia Metallic (U80) BMW M3 Competition xDrive (G81) Touring"))
        self.assertIsNone(parse_caption(None))


if __name__ == "__main__":
    unittest.main()
