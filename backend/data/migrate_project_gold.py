"""
Project Gold (RM po18 lot 33, id 18083) -> 993 Turbo S, Manual.

It was filed 991.2 Turbo by model year, which also stamped it PDK (the 991
Turbo's only gearbox). The car is a 2018 new-build 993 Turbo with the 450 hp
Turbo S kit and a six-speed manual (lot text). Owner chose the Turbo S card
2026-11-10. Ingests now file it there (variants.is_project_gold).

Undo: --undo puts back 991.2 / Turbo / PDK.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402
from app.database import engine  # noqa: E402

ROW = 18083
NEW = {"generation": "993", "variant": "Turbo S", "transmission": "Manual"}
OLD = {"generation": "991.2", "variant": "Turbo", "transmission": "PDK"}


async def main(apply: bool, undo: bool) -> None:
    target = OLD if undo else NEW
    async with engine.begin() as c:
        row = (await c.execute(text(
            "select id, lot_title, generation, variant, transmission from auction_results where id=:i"),
            {"i": ROW})).mappings().first()
        print("now:   ", dict(row))
        print("target:", target)
        if not apply:
            print("dry run; pass --apply")
            return
        await c.execute(text(
            "update auction_results set generation=:generation, variant=:variant, "
            "transmission=:transmission where id=:i"), {**target, "i": ROW})
        print("applied")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
