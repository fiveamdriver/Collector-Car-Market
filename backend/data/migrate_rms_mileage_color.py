#!/usr/bin/env python3
"""
Backfill mileage and exterior_color for existing RM Sotheby's records.

Fetches each lot's HTML page and extracts mileage from bullet point text
(e.g. "20,408 km from new") and exterior color from known Porsche color names.

Usage (from backend/ directory):
    python data/migrate_rms_mileage_color.py

~1 req/sec; expect ~25 min for 1,424 records.
Run with --limit N to process only the first N records for testing.
"""
import argparse
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.request

import certifi

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.config import DATABASE_PATH
from app.utils.color_parser import scan_for_color, parse_color_from_phrase

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# More targeted than the general subtitle regex — anchored to "from new" context.
_FROM_NEW_RE = re.compile(
    r'([\d][\d,\.]*)\s*(k)?\s*(miles?|kilometers?|km|mi)\s+from\s+new',
    re.IGNORECASE
)
# Fallback: general mileage number + unit anywhere in a bullet
_GENERAL_MILEAGE_RE = re.compile(
    r'([\d][\d,\.]*)\s*(k)?\s*(miles?|kilometers?|km|mi)\b',
    re.IGNORECASE
)
_LI_RE  = re.compile(r'<li[^>]*>(.*?)</li>', re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')

# RM listings always describe exterior color with "Finished in X over Y interior"
# Capture everything between "Finished in" and "over" to get the exterior color phrase.
_FINISHED_IN_RE = re.compile(
    r'[Ff]inished\s+in\s+'
    r'(?:rare[\s,]+)?(?:special[-\s]order[\s,]+)?(?:non-metallic\s+|metallic\s+)?'
    r'(.+?)\s+over\b',
    re.IGNORECASE
)


def _parse_num(num_str: str, k_suffix: str | None, unit: str) -> int | None:
    # European period-as-thousands: "20.408" → 20408
    if '.' in num_str and ',' not in num_str:
        parts = num_str.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            num_str = num_str.replace('.', '')
    num_str = num_str.replace(',', '')
    try:
        value = float(num_str)
    except ValueError:
        return None
    if k_suffix:
        value *= 1000
    if unit.lower() in ('km', 'kilometer', 'kilometers'):
        value /= 1.609
    result = round(value)
    return result if result >= 100 else None


def scrape_lot(url: str) -> tuple[int | None, str | None]:
    """Return (mileage_miles, exterior_color) from a lot page, or (None, None)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None, None

    bullets = [_TAG_RE.sub("", li).strip() for li in _LI_RE.findall(html)]

    mileage = None
    for b in bullets:
        m = _FROM_NEW_RE.search(b)
        if m:
            mileage = _parse_num(m.group(1), m.group(2), m.group(3))
            if mileage:
                break
    if mileage is None:
        for b in bullets:
            m = _GENERAL_MILEAGE_RE.search(b)
            if m:
                candidate = _parse_num(m.group(1), m.group(2), m.group(3))
                if candidate and candidate < 500_000:
                    mileage = candidate
                    break

    # Prefer "Finished in X over Y" pattern — always exterior color on RM listings.
    # This avoids matching interior colors (e.g. "interior in Black").
    color = None
    for b in bullets:
        m = _FINISHED_IN_RE.search(b)
        if m:
            color = parse_color_from_phrase(m.group(1).strip())
            if color:
                break
    if not color:
        for b in bullets:
            color = scan_for_color(b)
            if color:
                break

    return mileage, color


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = sqlite3.connect(DATABASE_PATH)
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, auction_url FROM auction_results "
        "WHERE auction_source = 'RM Sotheby''s' "
        "AND auction_url IS NOT NULL "
        "AND (mileage IS NULL OR exterior_color IS NULL)"
    )
    rows = cur.fetchall()
    if args.limit:
        rows = rows[: args.limit]
    print(f"Records to process: {len(rows)}")

    updates: list[tuple] = []
    errors = 0

    for i, (id_, url) in enumerate(rows):
        mileage, color = scrape_lot(url)
        if mileage is not None or color is not None:
            updates.append((mileage, color, id_))

        if (i + 1) % 25 == 0 or (i + 1) == len(rows):
            print(f"  {i + 1}/{len(rows)} — {len(updates)} updates, {errors} errors")

        time.sleep(0.8)

    if updates:
        cur.executemany(
            "UPDATE auction_results SET "
            "mileage = COALESCE(mileage, ?), "
            "exterior_color = COALESCE(exterior_color, ?) "
            "WHERE id = ?",
            updates,
        )
        conn.commit()
        mileage_count = sum(1 for m, _, _ in updates if m is not None)
        color_count   = sum(1 for _, c, _ in updates if c is not None)
        print(f"\nUpdated {len(updates)} records — {mileage_count} mileage, {color_count} color")
    else:
        print("\nNo updates found")

    conn.close()
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
