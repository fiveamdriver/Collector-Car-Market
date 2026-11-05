"""
Split the 964 'Turbo' card by engine: MY1993-94 -> 'Turbo 3.6', MY1991-92 ->
'Turbo 3.3' (app/utils/variants.split_964_turbo). Dry run by default; --apply
writes; --undo puts both back on 'Turbo'.

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
                qs = [f"UPDATE {table} SET variant='Turbo' WHERE generation='964' "
                      f"AND variant IN ('Turbo 3.3', 'Turbo 3.6')"]
            else:
                base = f"UPDATE {table} SET variant=:v WHERE model_line='911' AND generation='964' AND variant='Turbo' "
                qs = [(base + "AND year >= :my", "Turbo 3.6"), (base + "AND year < :my", "Turbo 3.3")]
            for q in qs:
                q, v = q if isinstance(q, tuple) else (q, None)
                n = (await s.execute(text(q), {"my": TURBO_36_FROM_MY, "v": v})).rowcount
                print(f"{table}: {n} rows {'-> ' + v if v else 'back to Turbo'} "
                      f"{'(dry run)' if not (apply or undo) else ''}")
        if apply or undo:
            await s.commit()
        else:
            await s.rollback()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
