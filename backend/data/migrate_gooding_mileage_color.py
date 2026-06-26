#!/usr/bin/env python3
"""
Backfill mileage and exterior_color for existing Gooding & Company records.

Fetches the Gatsby page-data.json for each lot (derived from auction_url slug)
and parses mileage + color from the highlights array.

Usage (from backend/ directory):
    python data/migrate_gooding_mileage_color.py

Rate-limited to ~1 req/sec to avoid hammering goodingco.com.
"""
import json
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
from app.utils.color_parser import parse_color_from_phrase

SSL_CTX       = ssl.create_default_context(cafile=certifi.where())
PAGE_DATA_URL = "https://www.goodingco.com/page-data/lot/"

_SUBTITLE_MILEAGE_RE = re.compile(
    r'([\d][\d,\.]*)\s*(k)?\s*(miles?|kilometers?|km|mi)\b',
    re.IGNORECASE
)
_FINISHED_IN_RE = re.compile(
    r'\bfinished in\b\s+(?:very rare\s+|original colou?rs?\s+of\s+)?(.+?)(?:\s+over\b|\s+with\b|,|$)',
    re.IGNORECASE
)


def slug_from_url(url: str) -> str | None:
    """Extract lot slug from 'https://www.goodingco.com/lot/{slug}/'."""
    url = url.rstrip("/")
    parts = url.split("/")
    return parts[-1] if parts else None


def fetch_highlights(slug: str) -> list[str] | None:
    url = f"{PAGE_DATA_URL}{slug}/page-data.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        item = data["result"]["data"]["contentfulLot"]["item"]
        return item.get("highlights") or []
    except Exception:
        return None


def parse_mileage(highlights: list[str]) -> int | None:
    for h in highlights:
        m = _SUBTITLE_MILEAGE_RE.search(h)
        if not m:
            continue
        num_str, k_suffix, unit = m.group(1), m.group(2), m.group(3)
        if '.' in num_str and ',' not in num_str:
            parts = num_str.split('.')
            if len(parts) == 2 and len(parts[1]) == 3:
                num_str = num_str.replace('.', '')
        num_str = num_str.replace(',', '')
        try:
            value = float(num_str)
        except ValueError:
            continue
        if k_suffix:
            value *= 1000
        if unit.lower() in ('km', 'kilometer', 'kilometers'):
            value /= 1.609
        result = round(value)
        if result >= 100:
            return result
    return None


def parse_color(highlights: list[str]) -> str | None:
    for h in highlights:
        fm = _FINISHED_IN_RE.search(h)
        if fm:
            return parse_color_from_phrase(fm.group(1).strip())
    return None


def main() -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, auction_url FROM auction_results "
        "WHERE auction_source = 'Gooding & Company' AND auction_url IS NOT NULL"
    )
    rows = cur.fetchall()
    print(f"Gooding records to process: {len(rows)}")

    updates: list[tuple] = []
    errors = 0

    for i, (id_, url) in enumerate(rows):
        slug = slug_from_url(url)
        if not slug:
            continue

        highlights = fetch_highlights(slug)
        if highlights is None:
            errors += 1
            continue

        mileage = parse_mileage(highlights)
        color   = parse_color(highlights)

        if mileage is not None or color is not None:
            updates.append((mileage, color, id_))

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(rows)} processed — {len(updates)} updates, {errors} errors")

        time.sleep(0.8)

    if updates:
        cur.executemany(
            "UPDATE auction_results SET mileage = COALESCE(mileage, ?), "
            "exterior_color = COALESCE(exterior_color, ?) WHERE id = ?",
            updates,
        )
        conn.commit()
        mileage_count = sum(1 for m, _, _ in updates if m is not None)
        color_count   = sum(1 for _, c, _ in updates if c is not None)
        print(f"\nUpdated {len(updates)}/{len(rows)} records — {mileage_count} mileage, {color_count} color")
    else:
        print("\nNo updates found")

    if errors:
        print(f"Fetch errors (lot not found / network): {errors}")

    conn.close()
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
