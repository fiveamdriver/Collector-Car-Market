#!/usr/bin/env python3
"""
Re-file coachbuilt Singer cars out of the donor car's trim and into 'Singer'.

Variant lists are scanned in order, so "911 Carrera 2 Coupe by Singer" matched
"Carrera" long before it reached "Singer". Twenty-five seven-figure restomods were
therefore filed under Carrera, Targa, Turbo, Turbo S, Carrera 4 and Carrera 2,
inflating the average on every one of those cards. One of them — a Singer
"Turbo Study" — also matched "Turbo S" as a plain substring.

app/utils/variants.py now tests for a coachbuilder before the trim list; this
backfills the rows written before that fix.

Singer records are not currently rendered anywhere (Modified/Singer are held back
pending a restomod section), so the effect here is to *remove* restomods from the
trim cards rather than to surface them.

Usage (from backend/ directory):
    python data/migrate_singer_variants.py            # dry run
    python data/migrate_singer_variants.py --apply    # writes the changes

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.variants import coachbuilder_variant
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuctionResult))
        records = result.scalars().all()

        moved: dict[str, int] = {}
        for rec in records:
            builder = coachbuilder_variant(rec.lot_title or "")
            if builder is None or rec.variant == builder:
                continue
            print(f"  #{rec.id}: {rec.generation} {rec.variant!r} -> {builder!r} | {(rec.lot_title or '')[:56]}")
            moved[rec.variant] = moved.get(rec.variant, 0) + 1
            rec.variant = builder

        total = sum(moved.values())
        print()
        for variant in sorted(moved, key=lambda v: -moved[v]):
            print(f"  out of {variant!r}: {moved[variant]} record(s)")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
