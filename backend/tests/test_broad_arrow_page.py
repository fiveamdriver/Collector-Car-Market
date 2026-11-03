"""
Tests for app.services.enrichment.parse_broad_arrow_page — Broad Arrow lot
pages as archived by archive.org. The markup mirrors the real pages; the text
is shortened.

Run from the backend/ directory:
    python -m unittest tests.test_broad_arrow_page -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enrichment import parse_broad_arrow_page
from app.utils.lot_details import PROSE_SEPARATOR, extract
from app.utils.lot_extras import derive

LD = """<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Car", "name": "1975 Porsche 911 Carrera MFI Coupe ",
 "color": "", "vehicleIdentificationNumber": "9115600415", "vehicleInteriorColor": "",
 "vehicleTransmission": "", "manufacturer": "Porsche", "model": "911 Carrera MFI Coupe"}
</script>"""

META = ("<meta content='Chassis No. 9115600415 &#x000A;&#x000A;According to its Certificate of "
        "Authenticity, this 1975 911 Carrera Coupe was completed in...' name='description'>")

PRE_SALE = f"""<html><head>{META}{LD}</head><body>
<div class='highlights-section white-bg'>
<div class='highlights-content'>
<h2></h2>
<div class='vehicle-highlights'>
<ul class='options-list'>
<li>Rare mechanically fuel-injected RoW Carrera Coupe, one of 508 built for 1975 </li>
<li>Finished in its original shade of era-evoking Light Yellow over a black interior with Shetland cloth seat inserts </li>
<li>Offered with a Porsche CoA, Porsche Classic toolkit, and recent engine rebuild invoices</li>
</ul>
</div>
</div>
</div>

<div class='about-vehicle-section vdp-info-section'>
<div class='description'>
<p>Chassis No. 9115600415 </p>

<p>According to its Certificate of Authenticity, this Rest of World 1975 911 Carrera Coupe was completed in Light Yellow over a leatherette interior. Additional options ordered when new included a limited slip differential, forged Fuchs wheels, and Bilstein shock absorbers among others.</p>

<p>Please note this vehicle is titled as Model Year 1974</p>
</div>
</div>
</body></html>"""

# The same lot after the sale: catalogue gone, only the head survives.
POST_SALE = f"<html><head>{META}{LD}</head><body><div class='vdp-header'>Sold</div></body></html>"


class BroadArrowPageTests(unittest.TestCase):
    def test_pre_sale_keeps_highlights_and_essay(self):
        text, is_catalogue = parse_broad_arrow_page(PRE_SALE)
        self.assertTrue(is_catalogue)
        head, _, prose = text.partition(PROSE_SEPARATOR)
        self.assertIn("Light Yellow over a black interior", head)
        self.assertIn("Chassis No. 9115600415", head)          # short paragraph → spec line
        self.assertIn("limited slip differential", prose)      # the essay is kept
        self.assertEqual(extract(text)["exterior_color"], "Light Yellow")
        extras = derive("1975 Porsche 911 Carrera MFI Coupe", text, 1975, "911")
        self.assertEqual(extras["chassis"], "9115600415")
        self.assertEqual(extras["interior"], "black")
        self.assertEqual(extras["provenance"], "Porsche COA")

    def test_post_sale_page_is_not_a_catalogue(self):
        text, is_catalogue = parse_broad_arrow_page(POST_SALE)
        self.assertFalse(is_catalogue)
        self.assertIn("Chassis: 9115600415", text)
        # The cut-off meta description must not invent a color.
        self.assertIsNone(extract(text)["exterior_color"])


if __name__ == "__main__":
    unittest.main()


class SnapshotChoiceTests(unittest.TestCase):
    """fetch_broad_arrow picks the archived copy with the most catalogue text."""

    URL = "https://www.broadarrowauctions.com/vehicles/am26_r0138/1975-porsche-911-carrera-mfi-coupe"
    PATH = "https://www.broadarrowauctions.com/vehicles/am26_r0138/1975-porsche-911-carrera-mfi-coupe"

    def run_with(self, snapshots: dict[str, str]):
        from unittest import mock
        from app.services import enrichment as E
        fetched = []

        def fake_get(url):
            ts = url.split("/web/")[1].split("id_")[0]
            fetched.append(ts)
            return snapshots[ts]

        rows = [(ts, self.PATH) for ts in snapshots]
        with mock.patch.object(E, "_lot_snapshots", return_value=rows), \
             mock.patch.object(E, "_wayback_get", side_effect=fake_get):
            return E.fetch_broad_arrow(self.URL), fetched

    def test_pre_sale_copy_wins(self):
        # Sale 2026-03-06: the 03-03 copy has the catalogue, later ones are stripped.
        text, fetched = self.run_with({"20260303141339": PRE_SALE, "20260601000000": POST_SALE})
        self.assertIn("limited slip differential", text)
        self.assertEqual(fetched, ["20260303141339"])

    def test_post_sale_tries_oldest_first_and_stops_on_stripped(self):
        text, fetched = self.run_with({"20260311000000": POST_SALE, "20260601000000": PRE_SALE})
        self.assertEqual(fetched, ["20260311000000"])   # stripped: later copies won't be better
        self.assertIn("Chassis: 9115600415", text)


class PresaleStoreTests(unittest.TestCase):
    def test_local_catalogue_is_used_before_archive_org(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from app.services import enrichment as E
        url = "https://www.broadarrowauctions.com/vehicles/dg26_r0083/2025-porsche-911-gt3-rs"
        details, _ = parse_broad_arrow_page(PRE_SALE)
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(E, "BA_PRESALE_DIR", Path(d)), \
             mock.patch.object(E, "_wayback_get", side_effect=AssertionError("network used")):
            E.save_presale(url, details, "20261103000000")
            self.assertEqual(E.fetch_broad_arrow(url), details)
