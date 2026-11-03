"""
Tests for the calendar-driven schedule in data/run_ingest.py (due mode).

Run from the backend/ directory:
    python -m unittest tests.test_schedule -v
"""
import os
import sys
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import run_ingest as R

SALE = date(2026, 11, 7)


def due(today, state=None):
    state = dict(state or {})
    with mock.patch("data.broad_arrow_ingest.SALE_CALENDAR", [(SALE, "Zurich")]):
        return [(jid, mode, src) for jid, mode, src in R.due_jobs(today, state)]


class DueTests(unittest.TestCase):
    def ids(self, today, state=None):
        return [jid for jid, *_ in due(today, state)]

    def test_quiet_day(self):
        done = {"monthly 2026-10": "x"}
        self.assertEqual(self.ids(date(2026, 10, 20), done), [])

    def test_presale_window(self):
        done = {"monthly 2026-10": "x", "monthly 2026-11": "x"}
        self.assertEqual(self.ids(date(2026, 10, 28), done), ["presale 2026-11-07 -10"])
        self.assertEqual(self.ids(date(2026, 11, 5), done | {"presale 2026-11-07 -10": "x",
                                                            "presale 2026-11-07 -5": "x"}),
                         ["presale 2026-11-07 -2"])

    def test_no_presale_once_the_sale_has_started(self):
        # Asleep through the whole window: a capture on sale day is useless.
        done = {"monthly 2026-11": "x"}
        self.assertNotIn("presale", " ".join(self.ids(SALE, done)))

    def test_results_after_the_sale(self):
        done = {"monthly 2026-11": "x"}
        self.assertEqual(self.ids(date(2026, 11, 9), done), [])
        jobs = due(date(2026, 11, 10), done)
        self.assertEqual(jobs, [("broad-arrow results 2026-11-07 +3", "monthly", ["broad-arrow"])])

    def test_monthly_runs_once_and_never_includes_broad_arrow(self):
        jobs = due(date(2026, 12, 3), {"broad-arrow results 2026-11-07 +3": "x",
                                       "broad-arrow results 2026-11-07 +10": "x"})
        self.assertEqual(jobs[0][0], "monthly 2026-12")
        self.assertNotIn("broad-arrow", jobs[0][2])
        self.assertEqual(self.ids(date(2026, 12, 20), {"monthly 2026-12": "x",
                                                       "broad-arrow results 2026-11-07 +3": "x",
                                                       "broad-arrow results 2026-11-07 +10": "x"}), [])


if __name__ == "__main__":
    unittest.main()
