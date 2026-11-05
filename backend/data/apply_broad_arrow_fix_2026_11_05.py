"""One-off: second Broad Arrow correction, from the 2026-11-05 scan of the
results-list cards (all 533 DB lots found; 542 Porsche cards).

- 39 lots whose card says "Now Asking" / "Estimate Available Upon Request"
  (schema InStock): they did not sell -> sale_status 'not_sold'.
- 9 lots marked 'unverified' on 2026-11-04 show "Not Sold" -> 'not_sold'.
- 3 'unverified' lots show a sold price -> back to NULL (sold).
- 11 "Sold After Auction" lots: Broad Arrow publishes no price, so the stored
  number (from the JSON-LD, unverifiable) is cleared -> sold_price NULL,
  sale_status 'sold_after_auction' (still served as a sale, without a price).
- 4 EUR/CHF lots stored at 1/10 -> displayed local price x the ingest's FX rate.

Backup of every touched row: reports/broad_arrow_fix_2026-11-04/backup_before_apply_2.json.
--apply writes; default is a dry run; --undo restores the backup.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402

BACKUP = Path(__file__).resolve().parents[2] / "reports" / "broad_arrow_fix_2026-11-04" / "backup_before_apply_2.json"

NOW_ASKING = [19432, 19433, 19429, 19445, 19447, 19457, 19438, 19443, 19446, 19460, 19461, 19463,
              19468, 19442, 19430, 19450, 19451, 19435, 19439, 19437, 19440, 19455, 19464, 19449,
              19452, 19453, 19436, 19434, 19454, 19458, 19441, 19444, 19462, 19448, 19466, 19467,
              19456, 19431, 19465]
UNVERIFIED_NOT_SOLD = [19394, 19397, 19407, 19409, 19421, 19422, 19425, 19405, 19410]
UNVERIFIED_SOLD = [19054, 19055, 19357]
SOLD_AFTER_AUCTION = [19094, 19029, 19365, 19101, 19010, 19102, 19037, 19367, 18996, 19280, 19366]
# id: (stored, corrected) — card price x NON_USD_RATES of the sale.
FX_TENFOLD = {19459: (16650, 166500), 19357: (7659, 76590), 31166: (14944, 149443), 19210: (16520, 165200)}


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        if undo:
            rows = json.loads(BACKUP.read_text())
            for r in rows:
                await s.execute(text("UPDATE auction_results SET sold_price=:p, sale_status=:st WHERE id=:i"),
                                {"p": r["sold_price"], "st": r["sale_status"], "i": r["id"]})
            await s.commit()
            print("restored", len(rows))
            return
        ids = sorted(set(NOW_ASKING + UNVERIFIED_NOT_SOLD + UNVERIFIED_SOLD + SOLD_AFTER_AUCTION) | set(FX_TENFOLD))
        rows = {r.id: r for r in (await s.execute(text(
            "SELECT id, sold_price, sale_status, auction_source FROM auction_results WHERE id = ANY(:ids)"),
            {"ids": ids})).all()}
        assert len(rows) == len(ids) and all(r.auction_source == "Broad Arrow" for r in rows.values())
        bad_fx = {i: v for i, v in FX_TENFOLD.items() if rows[i].sold_price != v[0]}
        print(f"not_sold +{len(NOW_ASKING) + len(UNVERIFIED_NOT_SOLD)}, unverified->sold {len(UNVERIFIED_SOLD)}, "
              f"sold_after_auction (price cleared) {len(SOLD_AFTER_AUCTION)}, fx x10 {len(FX_TENFOLD)} (drifted: {bad_fx})")
        if not apply:
            return
        BACKUP.write_text(json.dumps([{"id": i, "sold_price": rows[i].sold_price,
                                       "sale_status": rows[i].sale_status} for i in ids], indent=1))
        for i in NOW_ASKING + UNVERIFIED_NOT_SOLD:
            await s.execute(text("UPDATE auction_results SET sale_status='not_sold' WHERE id=:i"), {"i": i})
        for i in UNVERIFIED_SOLD:
            await s.execute(text("UPDATE auction_results SET sale_status=NULL WHERE id=:i"), {"i": i})
        for i in SOLD_AFTER_AUCTION:
            await s.execute(text("UPDATE auction_results SET sold_price=NULL, sale_status='sold_after_auction' "
                                 "WHERE id=:i"), {"i": i})
        for i, (old, new) in FX_TENFOLD.items():
            if i not in bad_fx:
                await s.execute(text("UPDATE auction_results SET sold_price=:n WHERE id=:i AND sold_price=:o"),
                                {"n": new, "o": old, "i": i})
        await s.commit()
        print("applied; backup:", BACKUP)


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
