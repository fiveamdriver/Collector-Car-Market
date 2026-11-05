"""
Move 911s titled "Turbo S" onto their generation's Turbo S card
(app/utils/variants.cabriolet_variant). Dry run by default; --apply writes
(old variants in data/migrate_turbo_s_cards_undo.json); --undo restores.
"""
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.variants import cabriolet_variant  # noqa: E402

UNDO = Path(__file__).with_name("migrate_turbo_s_cards_undo.json")


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        if undo:
            for r in json.loads(UNDO.read_text()):
                await s.execute(text("UPDATE auction_results SET variant=:v WHERE id=:i"), {"v": r["variant"], "i": r["id"]})
            await s.commit()
            print("restored")
            return
        rows = (await s.execute(text(
            "SELECT id, year, generation, variant, lot_title FROM auction_results "
            "WHERE model_line='911' AND lot_title ~* 'turbo' AND variant <> 'Turbo S'"))).all()
        moves = [r for r in rows if cabriolet_variant(r.generation, r.variant, r.lot_title or "", r.year) == "Turbo S"]
        print(len(moves), Counter((r.generation, r.variant) for r in moves))
        odd = [r for r in moves if not (r.generation == "996.2" and r.year == 2005)]
        for r in odd:
            print("  ", r.id, r.year, r.generation, r.variant, "|", r.lot_title[:80])
        if not apply:
            return
        UNDO.write_text(json.dumps([{"id": r.id, "variant": r.variant} for r in moves], indent=1))
        for r in moves:
            await s.execute(text("UPDATE auction_results SET variant='Turbo S' WHERE id=:i"), {"i": r.id})
        await s.commit()
        print("moved")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
