"""The API must never serve not_sold / withdrawn lots as results.

Run from backend/:  python -m unittest tests.test_sale_status_filter -v
"""
import asyncio
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.listing import AuctionResult
from app.routers import listings


def _row(i, price, status):
    return AuctionResult(id=i, make="Porsche", model_line="911", generation="992", variant="Sport Classic",
                         year=2023, sold_price=price, auction_source="Broad Arrow",
                         auction_url=f"u{i}", sold_date=date(2025, 3, 1), sale_status=status)


class SaleStatusFilterTests(unittest.TestCase):
    def test_unsold_rows_hidden_everywhere(self):
        async def run():
            engine = create_async_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            Session = async_sessionmaker(engine, expire_on_commit=False)
            async with Session() as s:
                s.add_all([_row(1, 500_000, None), _row(2, 675_000, "not_sold"),
                           _row(3, 900_000, "withdrawn"), _row(4, 400_000, "unverified")])
                await s.commit()
                rows = await listings.list_auction_results(make=None, model_line=None, generation=None,
                                                            variant=None, transmission=None, limit=100, db=s)
                self.assertEqual(sorted(r.id for r in rows), [1, 4])
                lines = await listings.get_model_line_stats(db=s)
                self.assertEqual((lines[0].count, lines[0].avg_sold_price), (2, 450_000))
                with self.assertRaises(HTTPException):
                    await listings.get_auction_result(record_id=2, db=s)
                self.assertEqual((await listings.get_auction_result(record_id=4, db=s)).id, 4)
            await engine.dispose()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
