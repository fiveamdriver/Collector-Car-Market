#!/usr/bin/env python3
"""
Move five road cars off the transaxle race lines (owner rule 2026-11-08: if it
is street legal, it is not a race car). Each was checked against its listing:

  23239, 27660, 28234  1987 928 Club Sport prototypes: factory drivers' company
                       cars, UK-registered, 42k-73k miles
  17680                1992 968 Turbo S prototype: Porsche press car on plates
  31076                1988 944 Turbo S: production road model ("Restoration
                       Challenge" is Porsche Classic's restoration contest)

    python data/migrate_transaxle_street_cars.py            # dry run
    python data/migrate_transaxle_street_cars.py --apply    # write, with undo file

Undo file: ~/Projects/CollectorCarMarket-data/reports/migrate_transaxle_street_cars_<stamp>_undo.json
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402

# id -> (expected current model_line, new model_line = generation, variant)
MOVES = {
    23239: ("928 Race", "928", "Club Sport"),
    27660: ("928 Race", "928", "Club Sport"),
    28234: ("928 Race", "928", "Club Sport"),
    17680: ("968 Race", "968", "Turbo S"),
    31076: ("944 Race", "944", "Turbo S"),
}
REPORT_DIR = Path.home() / "Projects" / "CollectorCarMarket-data" / "reports"


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as s:
        rows = {r["id"]: r for r in (await s.execute(text(
            "SELECT id, year, model_line, generation, variant, sold_price, lot_title FROM auction_results "
            "WHERE id = ANY(:ids)"), {"ids": list(MOVES)})).mappings().all()}
        todo = []
        for i, (expect, line, variant) in MOVES.items():
            r = rows.get(i)
            if not r or r["model_line"] != expect:
                print(f"  {i}: skipped (now {r and r['model_line']!r}, expected {expect!r})")
                continue
            todo.append((r, line, variant))
            print(f"  {i} {r['year']} {r['model_line']}/{r['generation']}/{r['variant']} -> "
                  f"{line}/{line}/{variant}  ${r['sold_price']:,}  {r['lot_title']}")
        print(f"{len(todo)} rows to move.")
        if not apply:
            print("Dry run: nothing changed. Re-run with --apply.")
        elif todo:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            undo = REPORT_DIR / f"migrate_transaxle_street_cars_{datetime.now():%Y%m%d_%H%M%S}_undo.json"
            undo.write_text(json.dumps({str(r["id"]): {k: r[k] for k in ("model_line", "generation", "variant")}
                                        for r, _, _ in todo}, indent=1))
            for r, line, variant in todo:
                await s.execute(text(
                    "UPDATE auction_results SET model_line = :l, generation = :l, variant = :v "
                    "WHERE id = :id AND model_line = :old"),
                    {"l": line, "v": variant, "id": r["id"], "old": r["model_line"]})
            await s.commit()
            print(f"Applied. Undo file: {undo}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
