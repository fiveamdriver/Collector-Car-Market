"""
Move MY1993-94 964 Turbos from the 'Turbo' card to their own 'Turbo 3.6' card
(app/utils/variants.split_964_turbo). Dry run by default; --apply writes;
--undo moves them back.

    python data/migrate_964_turbo_36.py [--apply | --undo]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.variants import TURBO_36_FROM_MY  # noqa: E402

TABLES = ("auction_results", "active_listings")


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        for table in TABLES:
            if undo:
                q = f"UPDATE {table} SET variant='Turbo' WHERE generation='964' AND variant='Turbo 3.6'"
            else:
                q = (f"UPDATE {table} SET variant='Turbo 3.6' WHERE model_line='911' AND generation='964' "
                     f"AND variant='Turbo' AND year >= :my")
            n = (await s.execute(text(q), {"my": TURBO_36_FROM_MY})).rowcount
            print(f"{table}: {n} rows {'would move' if not (apply or undo) else 'moved'}")
        if apply or undo:
            await s.commit()
        else:
            await s.rollback()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
