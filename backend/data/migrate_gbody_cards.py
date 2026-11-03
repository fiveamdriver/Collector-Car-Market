#!/usr/bin/env python3
"""
Apply the 2026-11-02 G-Body card decisions to stored rows:
  * every Targa on the Targa card whatever its engine (BaT had never used it),
  * new cards: Carrera 3.2 Club Sport (MY1987–89) and SC RS (1984),
  * factory Cabriolets (MY1983+) on the Cabriolet card.
Only rows whose title names Targa / Club Sport / SC RS / Cabriolet are
re-derived, with app.utils.variants.gbody_variant + cabriolet_variant.
M491 is an options tag (lot_extras.parse_m491), applied by migrate_lot_extras.

Usage (from backend/ directory):
    python data/migrate_gbody_cards.py            # dry run
    python data/migrate_gbody_cards.py --apply
"""
import argparse
import asyncio
import os
import re
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.utils.variants import cabriolet_variant, gbody_variant, strip_turbo_impostor  # noqa: E402

WORDS = re.compile(r'\btarga\b|\bclub\s?sport\b|\bSC\s*/?\s*RS\b|\bcabriolet\b|\bconvertible\b'
                   r'|\bslant[-\s]?nose\b|\bflat[-\s]?nose\b|\bflachbau\b', re.IGNORECASE)


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, year, lot_title, variant FROM auction_results "
            "WHERE model_line = '911' AND generation = 'G-Body'"))).fetchall()
        changes = []
        for row_id, year, title, variant in rows:
            if not WORDS.search(title or "") or "group c" in (title or "").lower():
                continue
            new = gbody_variant(strip_turbo_impostor(title), year)
            new = cabriolet_variant("G-Body", new, title, year)
            if new != variant:
                changes.append((row_id, variant, new, year, title))
        print(f"{len(changes)} to re-file: {dict(Counter((c[1], c[2]) for c in changes))}")
        for _, old, new, year, title in sorted(changes, key=lambda c: (c[2], c[1], c[3])):
            if (old, new) not in {("Carrera 3.2", "Targa"), ("SC", "Targa"), ("911", "Targa"), ("911S", "Targa")}:
                print(f"  {old:22} -> {new:22} {year} {title[:58]}")
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
