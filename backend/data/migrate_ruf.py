#!/usr/bin/env python3
"""
Give RUF its own model line.

RUF is a registered manufacturer that builds on 911 shells (CTR Yellowbird, Rt12,
BTR, Turbo R). Its cars were filed on the donor cards — 11 on the G-Body 930
Turbo, 10 on the 993 Turbo, the rest across the 964, 996 and 997 — where six-
and seven-figure RUFs dragged every average up. Same treatment as Singer,
Gunther Werks and Emory: their own model line, 'RUF', matched by
COACHBUILT_LINES in app/utils/model_lines.py (so future imports follow it).

Usage (from backend/ directory):
    python data/migrate_ruf.py            # dry run, lists every lot
    python data/migrate_ruf.py --apply    # writes the changes

Safe to re-run.
"""
import asyncio
import os
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.model_lines import match_coachbuilt_line
from sqlalchemy import select
from migrate_ruf_dealer_kits import RUF_KIT_ELSEWHERE


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line != "RUF")
        )
        plan: Counter = Counter()
        rows = []
        for rec in result.scalars().all():
            if match_coachbuilt_line(rec.lot_title or "") != "RUF":
                continue
            if rec.auction_url in RUF_KIT_ELSEWHERE:
                # RUF parts fitted by a dealer — kept on the donor card.
                continue
            plan[(rec.model_line, rec.generation, rec.variant)] += 1
            rows.append(rec)
            rec.model_line, rec.generation, rec.variant = "RUF", "RUF", "base"

        for (line, gen, var), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {line} / {gen} / {var}")
        print()
        for rec in sorted(rows, key=lambda r: -(r.sold_price or 0)):
            print(f"    #{rec.id} {rec.year} ${rec.sold_price}  {rec.lot_title[:80]}")

        if apply:
            await session.commit()
            print(f"\nUpdated {len(rows)} record(s).")
        else:
            print(f"\nDRY RUN — {len(rows)} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
