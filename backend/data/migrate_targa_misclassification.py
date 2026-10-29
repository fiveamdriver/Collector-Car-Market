#!/usr/bin/env python3
"""
Re-classify 911 records wrongly filed as 'Carrera T'.

The variant lists were scanned with a plain substring test, and "Carrera T" is a
prefix of both "Carrera Targa" and the auction-house phrasing "Carrera Type 996".
Every such lot was therefore filed as a Carrera T — a variant Porsche did not
build until the 991.2. app/utils/variants.py now matches the ambiguous names on a
word boundary, and bat_ingest.py (which had no "Targa" pattern at all) now lists
one; this backfills the rows written before those fixes.

Each affected row is re-parsed with the corrected matcher rather than being
rewritten to a hardcoded value, so this stays consistent with what a fresh ingest
would now produce.

Genuine Carrera Ts — 991.2 and later — are left alone.

Usage (from backend/ directory):
    python data/migrate_targa_misclassification.py            # dry run
    python data/migrate_targa_misclassification.py --apply    # writes the changes

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
from app.utils.variants import match_variant
from rms_ingest import _911_VARIANTS
from sqlalchemy import select

# The Carrera T arrived with the 991.2; anything earlier is a mismatch.
GENUINE_CARRERA_T_GENS = {"991.2", "992.1", "992.2"}


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.variant == "Carrera T",
                AuctionResult.generation.not_in(GENUINE_CARRERA_T_GENS),
            )
        )
        records = result.scalars().all()

        counts: dict[str, int] = {}
        unchanged = 0
        for rec in records:
            title = rec.lot_title or ""
            corrected = match_variant(_911_VARIANTS, title)
            if corrected == "Carrera T":
                # Word-boundary match still says Carrera T — leave it be.
                unchanged += 1
                continue
            print(f"  #{rec.id}: {rec.generation} 'Carrera T' -> {corrected!r} | {title[:56]}")
            rec.variant = corrected
            counts[corrected] = counts.get(corrected, 0) + 1

        total = sum(counts.values())
        print()
        for variant in sorted(counts):
            print(f"  -> {variant}: {counts[variant]} record(s)")
        if unchanged:
            print(f"  left as Carrera T: {unchanged}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
