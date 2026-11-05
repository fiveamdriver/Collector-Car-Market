"""
Move Carrera-family Targas off the coupe cards onto their generation's Targa card
(app/utils/variants.cabriolet_variant). Dry run by default; --apply writes and
saves the moved ids to data/migrate_targa_cards_undo.json; --undo restores.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.variants import cabriolet_variant  # noqa: E402

UNDO = Path(__file__).with_name("migrate_targa_cards_undo.json")


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        if undo:
            rows = json.loads(UNDO.read_text())
            for r in rows:
                await s.execute(text("UPDATE auction_results SET variant=:v WHERE id=:i AND variant='Targa'"),
                                {"v": r["variant"], "i": r["id"]})
            await s.commit()
            print("restored", len(rows))
            return
        rows = (await s.execute(text(
            "SELECT id, year, generation, variant, lot_title FROM auction_results "
            "WHERE model_line='911' AND lot_title ~* 'targa' AND variant <> 'Targa'"))).all()
        moves = [r for r in rows if cabriolet_variant(r.generation, r.variant, r.lot_title, r.year) == "Targa"]
        from collections import Counter
        print(len(moves), "to move:", Counter((r.generation, r.variant) for r in moves))
        if not apply:
            return
        UNDO.write_text(json.dumps([{"id": r.id, "variant": r.variant} for r in moves], indent=1))
        for r in moves:
            await s.execute(text("UPDATE auction_results SET variant='Targa' WHERE id=:i"), {"i": r.id})
        await s.commit()
        print("moved; undo file", UNDO.name)


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
