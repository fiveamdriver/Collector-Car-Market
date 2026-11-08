#!/usr/bin/env python3
"""
Refile cars titled "Carrera 3.8 RS" (Gooding's word order) that the old matcher
missed: a 993 belongs on the Carrera RS card, a 964 on the RS 3.8 card.
Tributes, conversions and replicas are left alone (same rule as the ingests).

    python data/migrate_carrera_38_rs.py            # dry run: list the rows
    python data/migrate_carrera_38_rs.py --apply    # write, with an undo file

Undo file: ~/Projects/CollectorCarMarket-data/reports/migrate_carrera_38_rs_<stamp>_undo.json
(id -> old variant). Re-running is safe: refiled rows no longer match.
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
from app.utils.variants import _CARRERA_38_RS, _RS_38_NOT_FACTORY  # noqa: E402

TARGET = {"993": "Carrera RS", "964": "RS 3.8"}
REPORT_DIR = Path.home() / "Projects" / "CollectorCarMarket-data" / "reports"


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, year, generation, variant, sold_price, auction_source, lot_title FROM auction_results "
            "WHERE model_line = '911' AND generation IN ('964', '993') AND lot_title ~ 'Carrera\\s+3\\.8\\s+RS'"
        ))).mappings().all()
        todo = [r for r in rows
                if _CARRERA_38_RS.search(r["lot_title"]) and not _RS_38_NOT_FACTORY.search(r["lot_title"])
                and r["variant"] != TARGET[r["generation"]]]
        for r in todo:
            print(f"  {r['id']:>6} {r['year']} {r['generation']} {r['variant']!r} -> {TARGET[r['generation']]!r}"
                  f"  ${r['sold_price']:,}  {r['auction_source']}: {r['lot_title']}")
        print(f"{len(todo)} rows to refile.")
        if not apply:
            print("Dry run: nothing changed. Re-run with --apply.")
        elif todo:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            undo = REPORT_DIR / f"migrate_carrera_38_rs_{datetime.now():%Y%m%d_%H%M%S}_undo.json"
            undo.write_text(json.dumps({str(r["id"]): r["variant"] for r in todo}, indent=1))
            for r in todo:
                await s.execute(text("UPDATE auction_results SET variant = :v WHERE id = :id AND variant = :old"),
                                {"v": TARGET[r["generation"]], "id": r["id"], "old": r["variant"]})
            await s.commit()
            print(f"Applied. Undo file: {undo}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
