#!/usr/bin/env python3
"""
Reclassify the transaxle cars (924/944/968/928) against app.utils.transaxle.

Three defects are repaired:

  1. 968 and 928 had no variant rules in any source, so every car was "base".
     928 GTS / GT / S4 and 968 Club Sport are now split out.

  2. The 924 variant list matched "Carrera GT" before "Carrera GTS", so the
     GTS and GTR cars were swallowed by the Carrera GT bucket.

  3. Competition cars (924 GTP, 924 Carrera GTR, 944 GTP, 944 Turbo Cup,
     968 Turbo RS/S, prototypes, clones) sat in the street buckets and
     dominated their averages.  They move to a "<line> Race" model line —
     still queryable, but out of the street pages.

Also rescues transaxle cars misfiled under model_line "911": the non-BaT
sources matched the model designation with \\b924\\b, which cannot match
"924S" / "928S", so those cars fell through to the "911" default.

Safe to re-run — the classification is a pure function of lot_title, and
already-correct rows are left untouched.  Race rows are re-evaluated on each
run, so a rule change can move a car back to the street lines.

Usage (from backend/ directory):
    python data/migrate_transaxle_variants.py            # dry run, prints the plan
    python data/migrate_transaxle_variants.py --apply    # write the changes
"""
import asyncio
import os
import re
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, engine
from app.models.listing import AuctionResult
from app.utils.transaxle import TRANSAXLE_LINES, classify, is_tribute, strip_style_prefix
from sqlalchemy import or_, select

# Model lines this migration owns: the street lines plus their race counterparts.
RACE_LINES = tuple(f"{line} Race" for line in TRANSAXLE_LINES)
OWNED_LINES = TRANSAXLE_LINES + RACE_LINES

# Trailing chassis / engine / VIN numbers are digit-soup that false-matches a
# model designation.  Strip from the first identifier keyword onward.
_IDENTIFIER_RE = re.compile(
    r'\b(?:chassis|engine|gearbox|frame|registration|reg\.?|body|coachwork)\b'
    r'|\bVIN\b|\bno\.\s*\d',
    re.IGNORECASE,
)

# Deliberately strict: only rescue a lot whose title names the model directly
# after "Porsche".  A loose \b944\b would match a chassis number fragment.
_MISFILED_RE = re.compile(r'Porsche\s+(968|944|928|924)\s?S?\d?\b', re.IGNORECASE)


def descriptive_part(title: str) -> str:
    m = _IDENTIFIER_RE.search(title or "")
    return title[:m.start()] if m else (title or "")


def base_line(model_line: str) -> str:
    """'924 Race' -> '924';  '924' -> '924'."""
    return model_line.removesuffix(" Race")


def misfiled_line(title: str) -> str | None:
    """Transaxle model line named by a title currently filed under 911."""
    m = _MISFILED_RE.search(descriptive_part(title))
    return m.group(1) if m else None


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(AuctionResult).where(
                or_(
                    AuctionResult.model_line.in_(OWNED_LINES),
                    AuctionResult.model_line.in_(("911", "914")),
                )
            )
        )).scalars().all()

        changes: list[tuple[AuctionResult, str, str, str, str]] = []
        for rec in rows:
            title = rec.lot_title or ""

            if rec.model_line == "914":
                # Same defect, adjacent model: bat_ingest ran 914s through the
                # 911 variant patterns, so "Twin-Turbocharged 1976 Porsche 914"
                # became a Turbo.  The 914 only ever split 914/6 vs 914/4.
                new_line = "914"
                new_variant = "base" if is_tribute(title) or not re.search(
                    r'914[/-]6', strip_style_prefix(title)) else "914/6"
            elif rec.model_line == "911":
                line = misfiled_line(title)
                if line is None:
                    continue          # a genuine 911
                new_line, new_variant = classify(line, title)
            else:
                new_line, new_variant = classify(base_line(rec.model_line), title)

            if rec.model_line == new_line and rec.variant == new_variant:
                continue
            changes.append((rec, rec.model_line, rec.variant, new_line, new_variant))

        # ── Report ────────────────────────────────────────────────────────────
        moves = Counter(
            (old_l, old_v, new_l, new_v) for _, old_l, old_v, new_l, new_v in changes
        )
        print(f"Rows examined : {len(rows)}")
        print(f"Rows changing : {len(changes)}\n")
        print(f"{'from':<28}{'to':<28}{'n':>5}")
        print("-" * 61)
        for (ol, ov, nl, nv), n in sorted(moves.items(), key=lambda kv: -kv[1]):
            print(f"{f'{ol}/{ov}':<28}{f'{nl}/{nv}':<28}{n:>5}")

        rescued = [c for c in changes if c[1] == "911"]
        if rescued:
            print(f"\nRescued from model_line=911 ({len(rescued)}):")
            for rec, ol, ov, nl, nv in rescued:
                print(f"  #{rec.id}  {nl}/{nv:<12} {(rec.lot_title or '')[:52]}")

        to_race = [c for c in changes if c[3].endswith(" Race")]
        if to_race:
            print(f"\nMoved to race lines ({len(to_race)}), top by price:")
            for rec, ol, ov, nl, nv in sorted(to_race, key=lambda c: -(c[0].sold_price or 0))[:10]:
                print(f"  ${rec.sold_price or 0:>9,}  {ol}/{ov} -> {nl}/{nv:<12} {(rec.lot_title or '')[:44]}")

        if not apply:
            print("\nDRY RUN — nothing written.  Re-run with --apply to commit.")
            await engine.dispose()
            return

        for rec, _ol, _ov, new_line, new_variant in changes:
            rec.model_line = new_line
            rec.variant = new_variant
            rec.generation = base_line(new_line)

        await session.commit()
        print(f"\nApplied {len(changes)} change(s).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
