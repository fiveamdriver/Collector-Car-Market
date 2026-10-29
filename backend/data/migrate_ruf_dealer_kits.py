#!/usr/bin/env python3
"""
Move RUF-kit cars that RUF did not build back to their donor generation.

The RUF line is for cars built or converted by RUF itself — W09 cars from
Pfaffenhausen, and customer Porsches converted there (or at RUF Automobile
Canada). Its matcher is the bare word "RUF", which also catches cars that only
carry RUF parts fitted by a dealer elsewhere. Those trade like their donor car,
not like a RUF, so they belong on the donor's card.

The titles can't tell the two apart (BaT writes "RUF-Modified" for both), so
these were identified one by one from the lot descriptions:

  1998 911 Carrera Targa  — BTR 2 kit fitted by Weissach of Vancouver
  2001 911 Turbo          — RTurbo kit fitted by RUF Auto Centre, Dallas
  2007 Boxster S          — supercharger fitted by RUF of Texas

Keyed by auction_url so migrate_ruf.py can skip them on a re-run.

Usage (from backend/ directory):
    python data/migrate_ruf_dealer_kits.py            # dry run
    python data/migrate_ruf_dealer_kits.py --apply    # writes the changes

Safe to re-run.
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

# auction_url -> (model_line, generation, variant)
RUF_KIT_ELSEWHERE = {
    "https://bringatrailer.com/listing/1998-porsche-911-carrera-targa-3/": ("911", "993", "Targa"),
    "https://bringatrailer.com/listing/2001-porsche-911-turbo-124/":       ("911", "996.1", "Turbo"),
    "https://bringatrailer.com/listing/2007-porsche-boxster-s-44/":        ("Boxster", "987.1", "S"),
}


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.auction_url.in_(RUF_KIT_ELSEWHERE))
        )
        changed = 0
        for rec in result.scalars().all():
            target = RUF_KIT_ELSEWHERE[rec.auction_url]
            if (rec.model_line, rec.generation, rec.variant) == target:
                continue
            print(f"  #{rec.id} {rec.lot_title[:60]}")
            print(f"      {rec.model_line} / {rec.generation} / {rec.variant}  ->  {' / '.join(target)}")
            rec.model_line, rec.generation, rec.variant = target
            changed += 1

        if apply:
            await session.commit()
            print(f"\nUpdated {changed} record(s).")
        else:
            print(f"\nDRY RUN — {changed} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
