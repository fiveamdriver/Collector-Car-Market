#!/usr/bin/env python3
"""
Split the G-Body "Carrera 2.7" card into the three cars it was holding.

The ingest scripts filed every G-Body "Carrera" up to MY1977 as Carrera 2.7, so
the card also held the 1976–77 Carrera 3.0 (a different, RoW-only car) and
1974–75 Carrera RS 3.0s titled "Carrera 3.0 RS" — the $0.6–1.0M spikes in its
price history. app.utils.variants.early_carrera_variant now decides; this
re-files the rows already stored. Modified cars stay on their chassis card, as
migrate_modified_to_chassis.py decided.

Usage (from backend/ directory):
    python data/migrate_early_carrera.py            # dry run
    python data/migrate_early_carrera.py --apply
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
from app.utils.variants import early_carrera_variant  # noqa: E402


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, year, lot_title, sold_price FROM auction_results "
            "WHERE model_line = '911' AND generation = 'G-Body' AND variant = 'Carrera 2.7'"))).fetchall()
        changes = [(r[0], early_carrera_variant(r[2], r[1]), r) for r in rows]
        changes = [c for c in changes if c[1] != "Carrera 2.7"]
        print(f"{len(rows)} Carrera 2.7 rows; {len(changes)} to re-file: {dict(Counter(c[1] for c in changes))}")
        for row_id, new, r in sorted(changes, key=lambda c: (c[1], c[2][1])):
            print(f"  {new:15} {r[1]} {r[2][:64]:64} ${r[3] or 0:,}")
        if apply and changes:
            await s.execute(text("UPDATE auction_results SET variant = :v WHERE id = :id"),
                            [{"v": new, "id": row_id} for row_id, new, _ in changes])
            await s.commit()
            print("applied.")
        elif changes:
            print("dry run — re-run with --apply to write.")
    await engine.dispose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    asyncio.run(main(p.parse_args().apply))
