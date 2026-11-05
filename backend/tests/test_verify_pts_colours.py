"""Regression tests for PTS colour handling (2026-11-04 incidents)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
import verify_pts as v  # noqa: E402


def row(text, colour=None, **kw):
    r = {"id": 0, "year": 2015, "model_line": "918 Spyder", "generation": "918 Spyder", "variant": "base",
         "exterior_color": colour, "lot_title": "", "details_text": text, "auction_url": ""}
    r.update(kw)
    return r


class StatedColour(unittest.TestCase):
    def test_full_name_after_pts(self):
        # colour field held only 'Orange'
        self.assertEqual(v.stated_pts_colours(row("The only 918 Spyder produced in Paint-to-Sample Pure Orange, $21,000 option")),
                         ["Pure Orange"])

    def test_name_before_pts(self):
        self.assertIn("Acid Green", v.stated_pts_colours(row("1 of 2 produced in Acid Green paint to sample")))

    def test_bat_bullets_do_not_bleed_into_interior(self):
        # BaT bullet lists: next line is the interior, line above is the gearbox
        st = v.stated_pts_colours(row("Seven-Speed Manual Transaxle\nPaint to Sample Green\nTruffle Brown Leather"))
        self.assertNotIn("Truffle Brown", st)
        self.assertFalse(any("Speed" in c for c in st))

    def test_interior_not_taken_as_paint(self):
        st = v.stated_pts_colours(row("finished in paint-to-sample Oslo Blue over Truffle Brown Club leather"))
        self.assertEqual(st, ["Oslo Blue"])

    def test_leather_to_sample_ignored(self):
        self.assertEqual(v.stated_pts_colours(row("Black over Color-to-Sample tan leather")), [])


class PaintChanged(unittest.TestCase):
    def test_respray_in_original_colour_keeps_factory_paint(self):
        # factory paint decides PTS (owner rule)
        self.assertFalse(v.paint_changed("The car was repainted in its original colour.", "", "Slate Grey"))

    def test_colour_change_blocks(self):
        self.assertTrue(v.paint_changed("the car was repainted in Guards Red in 1990", "", "Slate Grey"))

    def test_partial_refinish_is_not_a_colour_change(self):
        self.assertFalse(v.paint_changed("The brake calipers were refinished in February 2022.", "", "Forest Green Metallic"))
        self.assertFalse(v.paint_changed("singer Dean Martin's son", "", "Slate Gray"))

    def test_colour_wrap(self):
        self.assertTrue(v.paint_changed("It wears a satin black wrap."))

    def test_ppf_is_not_a_colour_change(self):
        self.assertFalse(v.paint_changed("Following a full clear-bra wrap, the car remains flawless."))

    def test_interior_wrap_ignored(self):
        self.assertFalse(v.paint_changed("The Alcantara-wrapped steering wheel frames the gauges."))

    def test_engine_modification_is_not_paint(self):
        self.assertFalse(v.paint_changed("A modified version of the Le Mans engine."))


class FactoryBasis(unittest.TestCase):
    def test_918_off_range_colour_is_pts(self):
        self.assertTrue(v.factory_basis(row("Paint to Sample Arrow Blue.", "Arrow Blue")))

    def test_918_range_colour_is_not(self):
        self.assertIsNone(v.factory_basis(row("Paint to sample Guards Red.", "Guards Red")))

    def test_partial_range_never_proves_pts(self):
        # 959 sheet is a parts paint sheet, not a complete range
        self.assertIsNone(v.factory_basis(row("x", "Viper Green", year=1988, model_line="959", generation="959")))


class PaletteMatching(unittest.TestCase):
    def test_same_prefix_different_hue(self):
        from verify_pts import factory
        pal = {factory.norm("Jet Black Metallic"): {"met"}}
        self.assertFalse(factory.on_list(factory.norm("Jet Green Metallic"), pal))
        self.assertTrue(factory.on_list(factory.norm("Jet Black"), pal))


class CatalogueRules(unittest.TestCase):
    def g(self, colour, text, year=1994, variant="Turbo", gen="964"):
        return row(text, colour, year=year, model_line="911", generation=gen, variant=variant)

    def test_finish_matters(self):
        # 964 range has Slate Grey METALLIC only -> non-metallic Slate Grey is PTS
        self.assertTrue(v.factory_basis(self.g("Slate Gray", "Paint-To-Sample Non-Metallic Slate Gray Paint")))

    def test_finish_only_from_words_next_to_colour(self):
        self.assertIsNone(v._finish_next_to("Pure White", "paint-to-sample Pure White over Graphite Blue with Gold Metallic detailing"))
        self.assertEqual(v._finish_next_to("Slate Gray", "Paint-To-Sample Non-Metallic Slate Gray Paint"), "uni")

    def test_process_word_is_not_a_colour(self):
        self.assertIsNone(v.factory_basis(self.g("Two-Stage Black", "Paint-to-Sample, Two-Stage Black", 1988, "930 Turbo", "G-Body")))

    def test_build_date_sets_model_year(self):
        self.assertEqual(v.build_model_year("a production completion date of September 22, 1993"), 1994)
        self.assertEqual(v.build_model_year("built in March 1993"), 1993)

    def test_no_colour_word_inside_other_words(self):
        self.assertIsNone(v._proper_colour("Porsche Custom-Ordered"))


if __name__ == "__main__":
    unittest.main()
