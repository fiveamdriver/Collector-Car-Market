#!/usr/bin/env python3
"""
List 911s whose .1/.2 (or chassis) placement rests on an uncertain model year,
for manual review. Prints nothing to fix automatically; it never writes.

A car is flagged when ALL hold:
  * no 17-digit VIN anywhere (chassis column, title, lot text) — a VIN's 10th
    character is the true model year, so a car with one is never ambiguous;
  * its generation would change if the titled year were the production year
    and the model year one later (European houses title by production year);
  * the variant really existed in BOTH placements (a 2016 911 R or a 2019
    Speedster is never ambiguous: there is no 991.2 R or 992 Speedster);
plus, always: a MY2009 GT3 (non-RS), where Porsche Classic ("GT3 (2009-12)")
and US model-year sources (997.2 GT3 = MY2010) disagree; and any 996-992 car
with no variant parsed.

US-market lots (BaT, Mecum, and RM/Gooding/Broad Arrow US sales) are titled by
US model year, so the production-year check applies only to non-US sales.

Usage (from backend/):  python data/audit_generations.py
"""
import asyncio
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.cards_911 import built_in  # noqa: E402
from app.utils.generations import _clean_vin, _vin_in, get_911_generation  # noqa: E402

# Checked by hand: US sales, so the titled year is the US model year and the
# placement stands. id -> why.
REVIEWED = {
    16846: "Gooding Pebble Beach 2022, US MY2008 -> 997.1",
    16869: "Gooding Amelia 2022, US MY2008 -> 997.1",
    16765: "Gooding Pebble Beach 2024, US MY2009 Mezger Turbo -> 997.1",
    18295: "RM Fort Lauderdale 2016, US MY2001 -> 996.1",
    18531: "RM Fort Lauderdale 2013, US MY2001 -> 996.1",
    18594: "RM Auburn Fall 2011, US MY2004 -> 996.2",
    18629: "RM Monterey 2010, US MY2008 -> 997.1",
    19133: "Broad Arrow Porsche sale 2026 (US), MY2024 -> 992.1",
    19344: "Broad Arrow Chattanooga 2024, US MY2008 -> 997.1",
}

_VIN_TEXT = re.compile(r"\bWP[0O][A-HJ-NPR-Z0-9]{14}\b")
# Variants confined to one phase: never ambiguous whatever the year.
_ONE_PHASE = re.compile(
    r"\b911 R\b|Club Coupe|Rennsport|Speedster|GT2 RS|GT3 RS 4\.0|Sport Classic|"
    r"Turbo S Exclusive|50th|Black Edition|\bS/T\b|Dakar|Carrera T\b", re.I)
# Sales known to be outside the US (title year may be the production year).
# Houses that sell in Europe and title by production year. Their US sales are
# titled by model year, but the lot record doesn't say where the sale was.
_NON_US = ("Bonhams", "RM Sotheby's", "Broad Arrow", "Gooding & Company")


def _vin(r) -> str | None:
    hit = _VIN_TEXT.search(r["details_text"] or "")
    return (_clean_vin(r["chassis"]) or _clean_vin(_vin_in(r["lot_title"]))
            or _clean_vin(hit.group() if hit else None))


async def main() -> None:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, year, generation, variant, auction_source, auction_url, sold_price, "
            "lot_title, chassis, details_text FROM auction_results WHERE model_line = '911' "
            "AND generation ~ '^99[1267]'"))).mappings().fetchall()
    flagged = []
    for r in rows:
        if r["id"] in REVIEWED:
            continue
        t = r["lot_title"] or ""
        if r["variant"] in (None, "", "base"):
            flagged.append((r, "no variant parsed"))
            continue
        if _vin(r):
            continue
        if r["year"] == 2009 and re.search(r"\bGT3\b(?!\s*RS)", t, re.I):
            flagged.append((r, "MY2009 GT3: sources disagree on .1/.2"))
            continue
        if r["auction_source"] not in _NON_US or _ONE_PHASE.search(t):
            continue
        alt = get_911_generation(r["year"] + 1, t)
        if alt != r["generation"] and built_in(alt, r["variant"], r["year"] + 1):
            flagged.append((r, f"if model year is {r['year'] + 1}: {alt}"))
    for r, why in flagged:
        print(f"#{r['id']:<6} {r['year']} {r['auction_source']:<18} {r['generation']}/{r['variant']:<12} "
              f"{why:<40} {(r['lot_title'] or '')[:60]}")
    print(f"\n{len(flagged)} car(s) need manual review.")


if __name__ == "__main__":
    asyncio.run(main())
