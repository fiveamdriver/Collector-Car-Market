#!/usr/bin/env python3
"""
Regenerate the AUCTION_EVENTS table in broad_arrow_ingest.py.

Usage (from backend/ directory):
    python data/broad_arrow_events.py            # print the table + a diff
    python data/broad_arrow_events.py --json     # machine-readable

Broad Arrow's lot URLs identify the sale only by a short code —
`/vehicles/ql26_r0165/...` — and nothing on the results page or in its
Schema.org payload says when that sale happened.  The date has to come from a
hand-maintained lookup, and a lookup that nobody regenerates goes stale: three
codes were listed while twenty-eight were in use, and every missing one was
silently stamped January 1.

This resolves the mapping from the site instead of by hand.  Each event page
carries the auction's name and date and links to its lots via a numeric
`branch_id`; loading that lot list reveals the code the same event uses in lot
URLs.  Joining the two gives code → date with no guessing.

Run this before each new auction season and paste the result into
broad_arrow_ingest.py.  Events with no cars (memorabilia and petroliana sales)
resolve to no code and are skipped — that is expected, not a failure.
"""
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright

BASE       = "https://www.broadarrowauctions.com"
INDEXES    = (f"{BASE}/past-auctions", f"{BASE}/events")
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/131.0.0.0 Safari/537.36")

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}

# Same shape as broad_arrow_ingest._EVENT_CODE_RE — the trailing letter matters
# (gi26e / gi26u / gi26v are three distinct Global Icons sales).
_CODE_RE = re.compile(r'/vehicles/([a-z]{2,4}\d{2}[a-z]?)_', re.IGNORECASE)

# "13 - 14 AUGUST 2026" / "1 JUNE 2023" / "23 JANUARY - 1 FEBRUARY 2026".
# Only the first day is wanted; a cross-month range carries the year on the
# second month, so the year is matched independently of the start month.
_DATE_RE = re.compile(
    r'(\d{1,2})\s*(?:[-–]\s*\d{1,2}\s*)?([A-Za-z]{3,})'
    r'\s*(?:[-–]\s*\d{1,2}\s+[A-Za-z]{3,}\s*)?(20\d{2})')

_EVENT_LINKS_JS = """() => Array.from(
    document.querySelectorAll('a[href*="/events/event/"]')
).map(a => a.getAttribute('href'))"""

# The name and date sit immediately above the "BACK TO AUCTIONS" control.
_HEADER_JS = """() => {
  const t = document.body.innerText.replace(/\\s+/g, ' ');
  const i = t.indexOf('BACK TO AUCTIONS');
  return i > 0 ? t.slice(Math.max(0, i - 170), i).trim() : '';
}"""

_BRANCH_JS = """() => {
  const a = document.querySelector('a[href*="branch_id_eq"]');
  return a ? a.getAttribute('href') : null;
}"""

_LOT_LINKS_JS = """() => Array.from(
    document.querySelectorAll('a[href*="/vehicles/"]')
).map(a => a.getAttribute('href'))"""


def parse_header(header: str) -> tuple[date | None, str]:
    """Split an event header into (start date, auction name)."""
    text = header.replace(" ", " ").replace(" ", " ")
    m = _DATE_RE.search(text)
    if not m:
        return None, text.strip()
    day, month, year = m.group(1), m.group(2).lower(), m.group(3)
    # Everything after the date line is the auction name and venue; the venue is
    # dropped by keeping only the part before the first comma.
    name = text[m.end():].strip().split(",")[0].strip()
    if month not in MONTHS:
        return None, name
    try:
        return date(int(year), MONTHS[month], int(day)), name
    except ValueError:
        return None, name


async def discover() -> dict[str, dict]:
    """Return {event_code: {"date": ISO date or None, "name": str}}."""
    found: dict[str, dict] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        # A default context advertises "HeadlessChrome", which the site's WAF
        # rejects with a 403.
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        links: list[str] = []
        for index_url in INDEXES:
            await page.goto(index_url, wait_until="networkidle", timeout=60_000)
            links += await page.evaluate(_EVENT_LINKS_JS)
        links = list(dict.fromkeys(h for h in links if h))
        print(f"{len(links)} event pages", file=sys.stderr)

        for i, href in enumerate(links, 1):
            try:
                await page.goto(BASE + href, wait_until="networkidle", timeout=60_000)
                sold_date, name = parse_header(await page.evaluate(_HEADER_JS))

                branch = await page.evaluate(_BRANCH_JS)
                if not branch:
                    print(f"  [{i}/{len(links)}] no lot list — {name[:50]}", file=sys.stderr)
                    continue

                await page.goto(branch if branch.startswith("http") else BASE + branch,
                                wait_until="networkidle", timeout=60_000)
                codes = [m.group(1).lower()
                         for h in await page.evaluate(_LOT_LINKS_JS)
                         if (m := _CODE_RE.search(h or ""))]
                if not codes:
                    print(f"  [{i}/{len(links)}] no car lots — {name[:50]}", file=sys.stderr)
                    continue

                # A results page can carry stray links to other sales; the sale
                # this page belongs to is the one that dominates.
                code = max(set(codes), key=codes.count)
                found[code] = {"date": sold_date.isoformat() if sold_date else None,
                               "name": name}
                print(f"  [{i}/{len(links)}] {code:<7} {str(sold_date):<12} {name[:50]}",
                      file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 — one bad page must not abort the sweep
                print(f"  [{i}/{len(links)}] ERROR {href[:48]}: "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)

        await browser.close()
    return found


def render_table(found: dict[str, dict]) -> str:
    """Render a paste-ready AUCTION_EVENTS literal, oldest event first."""
    dated = {c: v for c, v in found.items() if v["date"]}
    width = max((len(c) for c in dated), default=4) + 2
    lines = ["AUCTION_EVENTS: dict[str, date] = {"]
    for code, v in sorted(dated.items(), key=lambda kv: kv[1]["date"]):
        y, m, d = v["date"].split("-")
        key = f'"{code}":'
        lines.append(f'    {key:<{width + 3}} date({y}, {int(m):>2}, {int(d):>2}),'
                     f'  # {v["name"]}')
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a Python table")
    args = ap.parse_args()

    found = asyncio.run(discover())
    if args.json:
        print(json.dumps(found, indent=2, sort_keys=True))
        return

    print()
    print(render_table(found))

    # Compare against what the ingest script currently ships.
    from broad_arrow_ingest import AUCTION_EVENTS as current

    discovered = {c: v["date"] for c, v in found.items() if v["date"]}
    missing = {c: d for c, d in discovered.items() if c not in current}
    changed = {c: (current[c].isoformat(), d)
               for c, d in discovered.items()
               if c in current and current[c].isoformat() != d}
    stale = sorted(set(current) - set(discovered))

    print()
    if missing:
        print(f"NEW ({len(missing)}): " + ", ".join(f"{c}={d}" for c, d in sorted(missing.items())))
    if changed:
        print(f"CHANGED ({len(changed)}): "
              + ", ".join(f"{c} {a} -> {b}" for c, (a, b) in sorted(changed.items())))
    if stale:
        # Not necessarily wrong: an event can drop off the site's listings while
        # its lots remain in the results feed.
        print(f"IN SCRIPT BUT NOT DISCOVERED ({len(stale)}): {', '.join(stale)}")
    if not (missing or changed or stale):
        print("Table is up to date.")


if __name__ == "__main__":
    main()
