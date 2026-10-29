#!/usr/bin/env python3
"""
Race-car and originality cleanup for the 911 model line.

Phase 0 — delete memorabilia records (tool kits, manuals) that are not cars.
Phase 1 — move factory race cars misfiled in the street 911 line (and the
          RSR 3.8s misfiled under 911 Race / 993) into 911 Race:
            a) 964 Carrera RSR 3.8 (incl. Strassenversion)  -> 964 / RSR 3.8
            b) 993 GT2 R / GT2 race cars                    -> 993 / GT2 R
            c) Carrera Cup (964 & 993)                      -> gen / Carrera Cup
            d) GT3 Cup (996-992)                            -> flat gen / GT3 Cup
            e) GT3 RSR (996-997)                            -> flat gen / GT3 RSR
            f) vintage factory RSRs (explicit ids)          -> gen / RSR
Phase 2 — RETIRED. It used to park modified / tribute / replica street cars in
          a hidden 'Modified' variant. Modified cars now stay on the card of
          their chassis (see migrate_modified_to_chassis.py), so this phase is
          a no-op; re-running the script must not recreate the hidden bucket.

Usage (from backend/ directory):
    python data/migrate_race_cleanup.py

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import re
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from sqlalchemy import select, delete

# Not cars: BaT sold these as collectibles alongside real lots.
MEMORABILIA_IDS = {5804, 5806, 5808, 26228}

# Homebuilt race conversions whose titles lack an explicit modified keyword.
EXPLICIT_MODIFIED_IDS = {18206, 22601}  # '1971 911T RSR', '911T to RSR Specification'

# Real factory competition RSRs sold through Bonhams/BaT with narrative titles.
EXPLICIT_FACTORY_RSR_IDS = {20266, 22796, 22991, 23000, 23617}

# One-off reassignments to standalone race model lines.
EXPLICIT_MODEL_LINE_IDS = {
    28110: ("911 GT1", "911 GT1", "base"),  # 1997 911 GT1 Evolution
    23656: ("911 GT1", "911 GT1", "base"),  # 1998 GT1 Strassenversion (Bonhams 2003)
    17961: ("RS60", "RS60", "base"),        # 1960 718 RS 60 Werks
}

RSR38 = re.compile(r'RSR[- ]?3\.8|3\.8[- ]?RSR')
GT2R = re.compile(r'GT2[ -]?R\b|GT2 Race Car')
NOT_FACTORY = re.compile(
    r'3\.8L?-Powered|Conversion|Tribute|Recreation|Re-creation|Reproduction|'
    r'Replica|Evocation|Backdat|Project|Inspired',
    re.IGNORECASE,
)
MODIFIED = re.compile(
    r'Tribute|Replica|Recreation|Re-creation|Reproduction|Evocation|Conversion|'
    r'Backdat|Hot Rod|Outlaw|Inspired|[\w.]+-Style\b|[\w.]+-Powered\b|Race Car',
    re.IGNORECASE,
)
# Factory option package on the 992 GT3 RS — not a tribute build.
FACTORY_PACKAGE = re.compile(r'Tribute to Carrera RS', re.IGNORECASE)

FLAT_GEN = {
    '996.1': '996', '996.2': '996',
    '997.1': '997', '997.2': '997',
    '991.1': '991', '991.2': '991',
    '992.1': '992', '992.2': '992',
}


def classify(rec) -> tuple[str, str, str] | None:
    """Return (model_line, generation, variant) if the record must move."""
    t = rec.lot_title or ""
    gen = FLAT_GEN.get(rec.generation, rec.generation)

    if rec.id in EXPLICIT_FACTORY_RSR_IDS:
        return ("911 Race", rec.generation, "RSR")
    if rec.id in EXPLICIT_MODEL_LINE_IDS:
        return EXPLICIT_MODEL_LINE_IDS[rec.id]

    # Track-only customer racing car built on the 991 GT2 RS (incl. the
    # Manthey Clubsport 25) — not street legal, unlike the RS/GT2 Clubsport
    # *packages* on road cars, which stay in their street variants.
    if "GT2 RS Clubsport" in t:
        return ("911 Race", "991", "GT2 RS Clubsport")

    # ── Phase 1: factory race cars ────────────────────────────────────────────
    if "Cup" not in t and RSR38.search(t) and not NOT_FACTORY.search(t):
        return ("911 Race", "964", "RSR 3.8")
    if "Carrera Cup" in t:
        return ("911 Race", gen, "Carrera Cup")
    if "GT3 Cup" in t:
        return ("911 Race", gen, "GT3 Cup")
    if "GT3 RSR" in t:
        return ("911 Race", gen, "GT3 RSR")
    if rec.model_line == "911" and rec.generation == "993" and GT2R.search(t) \
            and not NOT_FACTORY.search(t) and "Project" not in t:
        return ("911 Race", "993", "GT2 R")

    return None


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line.in_(["911", "911 Race"]))
        )
        records = result.scalars().all()

        deleted = 0
        for rec in records:
            if rec.id in MEMORABILIA_IDS:
                print(f"  DELETE #{rec.id} (memorabilia): {rec.lot_title[:60]}")
                await session.delete(rec)
                deleted += 1

        moved = {}
        for rec in records:
            if rec.id in MEMORABILIA_IDS:
                continue
            target = classify(rec)
            if target is None:
                continue
            if (rec.model_line, rec.generation, rec.variant) == target:
                continue
            key = f"{target[0]} / {target[1]} / {target[2]}"
            moved[key] = moved.get(key, 0) + 1
            if target[2] != "Modified":
                print(f"  #{rec.id}: {rec.model_line}/{rec.generation}/{rec.variant} -> {key} | {rec.lot_title[:55]}")
            rec.model_line, rec.generation, rec.variant = target

        await session.commit()
        print(f"\nDeleted {deleted} memorabilia record(s).")
        for key in sorted(moved):
            print(f"  {moved[key]:4d} -> {key}")
        print(f"Moved {sum(moved.values())} record(s) total.")


if __name__ == "__main__":
    asyncio.run(main())
