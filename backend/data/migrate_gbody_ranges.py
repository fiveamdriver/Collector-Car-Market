#!/usr/bin/env python3
"""
Re-file G-Body 911s whose model year is outside their card's factory years.

Found 2026-11-02: "SC" matched inside capitalised "PORSCHE" (1974–75 Carreras
on the SC card), plain "1980 Porsche 911" titles fell through to the 1974–77
base-911 card, and conversions sat on body-style cards (a 1978 "SC Cabriolet
Conversion" on the Cabriolet card, which starts in 1983). Rows inside their
card's years are left alone, so earlier deliberate filings are not undone.
New filings come from app.utils.variants.gbody_variant, which every ingest
script now uses.

Usage (from backend/ directory):
    python data/migrate_gbody_ranges.py            # dry run
    python data/migrate_gbody_ranges.py --apply
"""
import argparse
import asyncio
import os
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.utils.variants import cabriolet_variant, gbody_variant  # noqa: E402

# Factory model years per G-Body card. 1976 is allowed on the 2.7 MFI card for
# the documented special orders (Belgian Gendarmerie cars).
RANGES = {
    "911": (1974, 1977), "911S": (1974, 1977), "Carrera 2.7": (1974, 1975),
    "Carrera 2.7 MFI": (1974, 1976), "Carrera RS 3.0": (1974, 1975), "Carrera 3.0": (1976, 1977),
    "SC": (1978, 1983), "Carrera 3.2": (1984, 1989), "930 Turbo": (1975, 1989),
    "Speedster": (1988, 1989), "Cabriolet": (1983, 1989), "Turbo 3.3 Slant Nose": (1981, 1989),
}


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, year, lot_title, variant, auction_source FROM auction_results "
            "WHERE model_line = '911' AND generation = 'G-Body'"))).fetchall()
        changes = []
        for row_id, year, title, variant, source in rows:
            lo, hi = RANGES.get(variant, (0, 9999))
            if year is None or lo <= year <= hi:
                continue
            if "group c" in (title or "").lower():
                continue  # a race prototype, not a 911 — handled separately
            new = gbody_variant(title, year, targa_card=source != "BaT")
            new = cabriolet_variant("G-Body", new, title, year)
            if new != variant:
                changes.append((row_id, variant, new, year, title))
        print(f"{len(changes)} to re-file: {dict(Counter((c[1], c[2]) for c in changes))}")
        for _, old, new, year, title in sorted(changes, key=lambda c: (c[1], c[3])):
            print(f"  {old:16} -> {new:16} {year} {title[:62]}")
        if apply and changes:
            await s.execute(text("UPDATE auction_results SET variant = :v WHERE id = :id"),
                            [{"v": c[2], "id": c[0]} for c in changes])
            await s.commit()
            print("applied.")
        elif changes:
            print("dry run — re-run with --apply to write.")
    await engine.dispose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    asyncio.run(main(p.parse_args().apply))
