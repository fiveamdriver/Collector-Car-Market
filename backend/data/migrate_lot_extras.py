#!/usr/bin/env python3
"""
Add auction_results.chassis / interior / options / provenance, make
transmission nullable, and fill all five from each row's title + details_text
(app/utils/lot_extras.py).

Transmission: every ingest script used to default to "Manual" when the title
didn't say, so 24k of 25k rows read "Manual" — including PDK-only GT3 RS and
Turbo S cars — and BaT's title parser read the 991's 7-speed manual as PDK.
Now:
  * the parser's answer wins when it has one;
  * otherwise a stored PDK/Automatic is kept (those only ever came from an
    explicit title token);
  * otherwise transmission becomes NULL (unknown), not a guessed "Manual".

Usage (from backend/ directory):
    python data/backup_db.py                 # first
    python data/migrate_lot_extras.py        # dry run: counts + samples
    python data/migrate_lot_extras.py --apply

Safe to re-run. Re-run after improving lot_extras.py.
"""
import argparse
import asyncio
import collections
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.database import AsyncSessionLocal, engine
from app.services.derived import FIELDS, derive_row
from sqlalchemy import text

DDL = [
    "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS chassis TEXT",
    "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS interior TEXT",
    "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS options TEXT",
    "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS provenance TEXT",
    "ALTER TABLE auction_results ALTER COLUMN transmission DROP NOT NULL",
]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    if args.apply:
        async with engine.begin() as conn:
            for stmt in DDL:
                await conn.execute(text(stmt))
        cols = ", ".join(FIELDS)
    else:
        # Dry run before the columns exist: read what is there.
        async with AsyncSessionLocal() as s:
            have = {r[0] for r in (await s.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'auction_results'"))).fetchall()}
        cols = ", ".join(f if f in have else f"NULL AS {f}" for f in FIELDS)

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            f"SELECT id, lot_title, details_text, year, model_line, generation, variant, {cols} FROM auction_results"
        ))).mappings().fetchall()

    updates, changed = [], collections.Counter()
    trans = collections.Counter()
    for row in rows:
        new = derive_row(row, distrust_manual=True)
        diff = {f: new[f] for f in FIELDS if new[f] != row[f]}
        if diff:
            updates.append({"id": row["id"], **new})
            changed.update(diff.keys())
            if "transmission" in diff:
                trans[(row["transmission"], new["transmission"])] += 1

    print(f"{len(rows)} rows, {len(updates)} to update")
    for f in FIELDS:
        print(f"  {f:<13} {changed[f]:>6} changed")
    print("  transmission old -> new:")
    for (old, new), n in trans.most_common():
        print(f"    {old!s:>9} -> {new!s:<9} {n:>6}")

    if args.apply and updates:
        sets = ", ".join(f"{f} = :{f}" for f in FIELDS)
        async with AsyncSessionLocal() as s:
            for i in range(0, len(updates), 1000):
                await s.execute(text(f"UPDATE auction_results SET {sets} WHERE id = :id"),
                                updates[i:i + 1000])
            await s.commit()
        print("applied.")
    elif not args.apply:
        print("dry run — re-run with --apply to write.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
