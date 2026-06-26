#!/usr/bin/env python3
"""
Backfill exterior_color and paint_to_sample for Broad Arrow records.

Loads each lot page via Playwright (required to bypass AWS WAF), extracts
bullet-point highlight text, and runs the standard Porsche color pipeline.

Usage (from backend/ directory):
    python data/migrate_broad_arrow_color.py
    python data/migrate_broad_arrow_color.py --limit 20   # test run

~2 s/lot; expect ~80 min for a full initial backfill of ~2,400 records.
Re-running is safe — only records missing both fields are processed.
"""
import argparse
import asyncio
import os
import re
import sqlite3
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.config import DATABASE_PATH
from app.utils.color_parser import parse_color_from_phrase, scan_for_color
from playwright.async_api import async_playwright

# RM-style "Finished in X over Y" — also catches Broad Arrow's bullet format:
#   "Paint to Sample Gulf Blue over Ascot Brown interior"
_FINISHED_IN_RE = re.compile(
    r'(?:finished\s+in|paint\s+to\s+sample)\s+'
    r'(?:rare[\s,]+)?(?:special[-\s]order[\s,]+)?(?:non-metallic\s+|metallic\s+)?'
    r'(.+?)\s+over\b',
    re.IGNORECASE,
)

_PTS_RE = re.compile(r'paint[-\s]to[-\s]sample|\bPTS\b', re.IGNORECASE)


def extract_color_pts(bullets: list[str]) -> tuple[str | None, bool | None]:
    color = None
    pts   = None

    for b in bullets:
        if _PTS_RE.search(b):
            pts = True
            break

    # "Finished in X over Y" / "Paint to Sample X over Y" — exterior is before "over"
    for b in bullets:
        m = _FINISHED_IN_RE.search(b)
        if m:
            color = parse_color_from_phrase(m.group(1).strip())
            if color:
                break

    # Fallback: scan each bullet for any known color name
    if not color:
        for b in bullets:
            color = scan_for_color(b)
            if color:
                break

    return color, pts


async def scrape_lot(page, url: str) -> tuple[str | None, bool | None]:
    try:
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        bullets = await page.evaluate("""() =>
            Array.from(document.querySelectorAll('li'))
                .map(li => li.innerText.trim())
                .filter(t => t.length > 10)
        """)
        return extract_color_pts(bullets or [])
    except Exception:
        return None, None


async def run(limit: int | None) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, auction_url FROM auction_results "
        "WHERE auction_source = 'Broad Arrow' "
        "AND auction_url IS NOT NULL "
        "AND exterior_color IS NULL "
        "AND paint_to_sample IS NULL"
    )
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]
    print(f"Records to process: {len(rows)}")

    updates: list[tuple] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for i, (id_, url) in enumerate(rows):
            color, pts = await scrape_lot(page, url)
            if color is not None or pts is not None:
                updates.append((color, pts, id_))

            if (i + 1) % 25 == 0 or (i + 1) == len(rows):
                print(f"  {i + 1}/{len(rows)} — {len(updates)} updates")

            await asyncio.sleep(1.5)

        await browser.close()

    if updates:
        cur.executemany(
            "UPDATE auction_results "
            "SET exterior_color = COALESCE(exterior_color, ?), "
            "    paint_to_sample = COALESCE(paint_to_sample, ?) "
            "WHERE id = ?",
            updates,
        )
        conn.commit()
        color_count = sum(1 for c, _, _ in updates if c is not None)
        pts_count   = sum(1 for _, p, _ in updates if p is not None)
        print(f"\nUpdated {len(updates)} records — {color_count} color, {pts_count} PTS")
    else:
        print("\nNo updates found")

    conn.close()
    print(f"Database: {DATABASE_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N records (for testing)")
    args = parser.parse_args()
    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()
