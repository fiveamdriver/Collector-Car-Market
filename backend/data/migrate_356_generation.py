#!/usr/bin/env python3
"""
Repair 356 records filed under generation '959'.

A June 2026 parser bug wrote the model year into the generation column for some
356s (e.g. "1959 Porsche 356 A Cabriolet" -> generation "959"), so they matched
no card on the site. This re-derives the generation from the model year using
the same ladder every ingest script uses, and re-derives the variant from the
title with the same word list (so "356 A Coupe by Reutter" lands on Coupe, not
'base').

Usage (from backend/ directory):
    python data/migrate_356_generation.py            # dry run, prints the plan
    python data/migrate_356_generation.py --apply    # writes the changes

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
from sqlalchemy import select

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]


def get_356_generation(year: int) -> str:
    if year <= 1955: return "Pre-A"
    if year <= 1959: return "356 A"
    if year <= 1963: return "356 B"
    return "356 C"


def parse_356_variant(text: str) -> str:
    for pat in _356_VARIANTS:
        if pat in text:
            return pat
    return "base"


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "356",
                AuctionResult.generation == "959",
            )
        )
        records = result.scalars().all()

        counts: dict[tuple[str, str], int] = {}
        skipped = 0
        for rec in records:
            if rec.year is None:
                skipped += 1
                continue
            gen = get_356_generation(rec.year)
            var = parse_356_variant(rec.lot_title or "")
            print(f"  #{rec.id}: {rec.year} 959/{rec.variant} -> {gen}/{var} | {(rec.lot_title or '')[:60]}")
            rec.generation = gen
            rec.variant = var
            counts[(gen, var)] = counts.get((gen, var), 0) + 1

        total = sum(counts.values())
        print()
        for (gen, var), n in sorted(counts.items()):
            print(f"  {gen} / {var}: {n} record(s)")
        if skipped:
            print(f"  skipped (no year): {skipped}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
