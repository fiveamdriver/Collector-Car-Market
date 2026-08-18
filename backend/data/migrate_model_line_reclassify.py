#!/usr/bin/env python3
"""
Re-file records whose model line was misread from the lot title.

Every source carried its own copy of the model-line list and matcher, and they
had drifted apart. Because an unmatched title falls through to "911", the drift
never failed loudly — it quietly filed other cars as 911s:

  * "2015 Porsche 918 'Weissach' Spyder" — the nickname splits the words, so
    `\\b918 Spyder\\b` could not match. Eleven hypercars sat in the 911 line.
  * "1960 Porsche 718 RS 60 Spyder", "1959 Porsche 718 RSK Spyder" — sports-racers
    whose names were in no source's list at all.
  * "2005 PORSCHE CARRERA GT", "2010 PORSCHE PANAMERA TURBO" — uppercase titles
    defeated a case-sensitive substring test.
  * "2021 Porsche 718 Spyder" — a Boxster that never says "Boxster".

And once, in the other direction: a 911 Turbo S "Edition 918 Spyder" was filed as
a 918.

app/utils/model_lines.py now owns this for every source. This backfills the rows
written before that, re-deriving model line, generation and variant through the
same parsers a fresh ingest would use, so the result matches what re-ingesting
would produce.

Model lines that a title cannot reveal are left alone — the race lines and the
standalone racers are assigned by migrate_race_cars.py, not parsed from text.

Usage (from backend/ directory):
    python data/migrate_model_line_reclassify.py            # dry run
    python data/migrate_model_line_reclassify.py --apply    # writes the changes

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "data"))

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.model_lines import match_model_line
from app.utils.transaxle import match_model_line as match_transaxle_line
from rms_ingest import parse_generation, parse_variant
from sqlalchemy import select

# Assigned by migration, not derivable from the title — never re-derive these.
DELIBERATE_LINES = {
    "911 Race", "944 Race", "924 Race", "968 Race", "928 Race", "Other",
    "550", "911 GT1", "RS Spyder", "934", "935", "917", "956", "962",
    "908", "907", "906", "904", "912",
}


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        records = (await session.execute(select(AuctionResult))).scalars().all()

        moves: dict[tuple[str, str], int] = {}
        value = 0
        for rec in records:
            title = rec.lot_title or ""
            if not title or rec.model_line in DELIBERATE_LINES:
                continue

            line = match_model_line(title, match_transaxle_line)
            if line == rec.model_line or line in DELIBERATE_LINES:
                continue

            year = rec.year or 0
            generation = parse_generation(line, year, title)
            variant = parse_variant(line, year, title)

            print(f"  #{rec.id}: {rec.model_line}/{rec.generation}/{rec.variant}"
                  f"  ->  {line}/{generation}/{variant}")
            print(f"       ${rec.sold_price or 0:,} | {title[:64]}")

            moves[(rec.model_line, line)] = moves.get((rec.model_line, line), 0) + 1
            value += rec.sold_price or 0
            rec.model_line = line
            rec.generation = generation
            rec.variant = variant

        total = sum(moves.values())
        print()
        for (src, dst), n in sorted(moves.items(), key=lambda x: -x[1]):
            print(f"  {src} -> {dst}: {n} record(s)")
        print(f"  ${value:,} of sales moved out of the wrong line")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
