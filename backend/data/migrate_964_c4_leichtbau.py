"""
Move 964 Carrera 4 Leichtbau cars onto their own card (app/utils/variants.
is_964_c4_leichtbau). Dry run by default; --apply writes (old variants saved to
data/migrate_964_c4_leichtbau_undo.json); --undo restores.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.variants import is_964_c4_leichtbau  # noqa: E402

UNDO = Path(__file__).with_name("migrate_964_c4_leichtbau_undo.json")


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        if undo:
            for r in json.loads(UNDO.read_text()):
                await s.execute(text("UPDATE auction_results SET variant=:v WHERE id=:i"), {"v": r["variant"], "i": r["id"]})
            await s.commit()
            print("restored")
            return
        rows = (await s.execute(text(
            "SELECT id, year, variant, sold_price, lot_title FROM auction_results "
            "WHERE model_line='911' AND generation='964' AND variant <> 'Carrera 4 Leichtbau'"))).all()
        moves = [r for r in rows if is_964_c4_leichtbau(r.lot_title)]
        for r in moves:
            print(r.id, r.year, r.variant, r.sold_price, "|", r.lot_title[:80])
        if not apply:
            return
        UNDO.write_text(json.dumps([{"id": r.id, "variant": r.variant} for r in moves], indent=1))
        for r in moves:
            await s.execute(text("UPDATE auction_results SET variant='Carrera 4 Leichtbau' WHERE id=:i"), {"i": r.id})
        await s.commit()
        print(len(moves), "moved")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
