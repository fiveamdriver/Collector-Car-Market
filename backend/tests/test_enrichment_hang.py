"""
Hang protection in app.services.enrichment.

A BaT retry once sat 18 hours with no writes: a request thread that never
returned kept the process alive after wait_for had given up on it, because
asyncio.to_thread's pool threads are joined at exit. These tests run enrich()
in a subprocess with a fetch that never returns and require the process to
exit promptly. No network or database: both are stubbed.

Run from the backend/ directory:
    python -m unittest tests.test_enrichment_hang -v
"""
import os
import subprocess
import sys
import textwrap
import time
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRELUDE = textwrap.dedent("""
    import asyncio, sys, threading
    sys.path.insert(0, {backend!r})
    from app.services import enrichment as e

    writes = []
    async def fake_select(source, urls, limit, include_complete, min_price):
        return [(i, f"https://example.test/lot/{{i}}") for i in range(4)]
    async def fake_write(batch):
        writes.extend(batch)
    e._select_rows = fake_select
    e._write = fake_write

    def stuck(url):
        threading.Event().wait()          # a request that never returns
    def ok(url):
        return "14,000 Miles Shown. Guards Red Paint."
""").format(backend=BACKEND_DIR)


def run(body: str, limit: float = 30) -> tuple[subprocess.CompletedProcess, float]:
    started = time.monotonic()
    proc = subprocess.run([sys.executable, "-c", PRELUDE + textwrap.dedent(body)],
                          capture_output=True, text=True, timeout=limit)
    return proc, time.monotonic() - started


class StuckFetchTests(unittest.TestCase):
    def test_stuck_fetch_does_not_keep_process_alive(self):
        proc, took = run("""
            calls = iter([stuck, ok, ok, ok])
            e.SOURCES["fake"] = e.Source("Fake", fetch=lambda u: next(calls)(u),
                                         workers=1, delay=0, deadline=1)
            stats = asyncio.run(e.enrich("fake", verbose=False))
            print(stats.errors, stats.fetched, len(writes))
        """)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # The stuck lot counts as one error; the other three still get written.
        self.assertEqual(proc.stdout.split(), ["1", "3", "3"])
        self.assertLess(took, 15)

    def test_watchdog_exits_with_stacks_when_nothing_completes(self):
        proc, took = run("""
            async def main():
                with e.Watchdog(1):
                    await asyncio.sleep(30)   # stalled: no kick ever comes
            asyncio.run(main())
            print("not reached")
        """)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("not reached", proc.stdout)
        self.assertIn("Timeout", proc.stderr)   # faulthandler's stack dump header
        self.assertLess(took, 15)


if __name__ == "__main__":
    unittest.main()
