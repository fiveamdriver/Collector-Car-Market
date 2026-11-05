"""One-off: apply the 2026-11-04 Broad Arrow site scan to auction_results.

- Adds the nullable sale_status column ('sold' / 'not_sold' / 'withdrawn' /
  'unverified'); NULL means sold (every other source only stores sales).
- Marks the 60 Not Sold and 8 Withdrawn lots; the API hides them.
- Marks the 12 lots whose page is gone as 'unverified' (still shown; their
  status and price could not be re-checked).
- Sets sold_price to the site's displayed, premium-inclusive price for 214
  USD lots, only where the stored value still equals the scanned one.

Backs up every touched row (id, sold_price, sale_status) to
reports/broad_arrow_fix_2026-11-04/backup_before_apply.json first.
Run with --apply to write; default is a dry run. --undo restores the backup.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402

REPORT = Path(__file__).resolve().parents[2] / "reports" / "broad_arrow_fix_2026-11-04"
BACKUP = REPORT / "backup_before_apply.json"


def _r(a, b):
    return list(range(a, b + 1))


NOT_SOLD = (_r(19368, 19393) + [19395, 19396] + _r(19398, 19404) + [19406, 19408]
            + _r(19411, 19420) + [19423, 19424] + _r(19426, 19428) + _r(28245, 28249)
            + [28252, 31167, 31168])
WITHDRAWN = [19360, 19361] + _r(28240, 28244) + [28260]
PAGE_GONE = [19054, 19055, 19357, 19394, 19397, 19405, 19407, 19409, 19410, 19421, 19422, 19425]


async def main(apply: bool, undo: bool) -> None:
    updates = json.loads((REPORT / "price_updates.json").read_text())
    status = {i: "not_sold" for i in NOT_SOLD}
    status.update({i: "withdrawn" for i in WITHDRAWN})
    status.update({i: "unverified" for i in PAGE_GONE})
    assert len(status) == 80
    async with AsyncSessionLocal() as s:
        await s.execute(text("ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS sale_status TEXT"))
        if undo:
            for row in json.loads(BACKUP.read_text()):
                await s.execute(text("UPDATE auction_results SET sold_price=:p, sale_status=:st WHERE id=:i"),
                                {"p": row["sold_price"], "st": row["sale_status"], "i": row["id"]})
            await s.commit()
            print("restored", len(json.loads(BACKUP.read_text())), "rows")
            return
        rows = {r.id: r for r in (await s.execute(text(
            "SELECT id, sold_price, sale_status FROM auction_results WHERE auction_source='Broad Arrow'"))).all()}
        prices = [(i, old, new) for i, old, new in updates
                  if i in rows and rows[i].sold_price == old and old != new and i not in status]
        skipped_hidden = [u for u in updates if u[0] in status and u[1] != u[2]]
        drift = [u for u in updates if u[0] in rows and rows[u[0]].sold_price != u[1]]
        missing = [i for i in status if i not in rows]
        print(f"status: not_sold {len(NOT_SOLD)}, withdrawn {len(WITHDRAWN)}, unverified {len(PAGE_GONE)}; missing ids {missing}")
        print(f"prices: apply {len(prices)}, drifted {len(drift)}, skipped (unsold/withdrawn/unverified) {len(skipped_hidden)}")
        if not apply:
            await s.rollback()
            return
        touched = sorted(set(status) | {i for i, _, _ in prices})
        BACKUP.write_text(json.dumps(
            [{"id": i, "sold_price": rows[i].sold_price, "sale_status": rows[i].sale_status} for i in touched], indent=1))
        for i, st in status.items():
            await s.execute(text("UPDATE auction_results SET sale_status=:st WHERE id=:i"), {"st": st, "i": i})
        for i, old, new in prices:
            await s.execute(text("UPDATE auction_results SET sold_price=:n WHERE id=:i AND sold_price=:o"),
                            {"n": new, "o": old, "i": i})
        await s.commit()
        print("applied; backup:", BACKUP)


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
