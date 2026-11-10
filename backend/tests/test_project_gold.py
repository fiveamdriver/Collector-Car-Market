"""Project Gold: a 2018 new-build 993 Turbo goes on the 993 Turbo S card."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))

from app.utils.generations import get_911_generation  # noqa: E402
import rms_ingest  # noqa: E402

TITLE = '2018 Porsche 911 Turbo Classic Series "Project Gold"'


class ProjectGold(unittest.TestCase):
    def test_generation_is_993(self):
        self.assertEqual(get_911_generation(2018, TITLE), "993")
        self.assertEqual(get_911_generation(2018, "2018 Porsche 911 Project Gold"), "993")

    def test_rm_files_it_on_993_turbo_s(self):
        self.assertEqual(rms_ingest.parse_generation("911", 2018, TITLE), "993")
        self.assertEqual(rms_ingest.parse_variant("911", 2018, TITLE), "Turbo S")

    def test_ordinary_991_turbo_untouched(self):
        self.assertEqual(get_911_generation(2018, "2018 Porsche 911 Turbo Cabriolet"), "991.2")
        self.assertEqual(rms_ingest.parse_variant("911", 2018, "2018 Porsche 911 Turbo"), "Turbo")


if __name__ == "__main__":
    unittest.main()
