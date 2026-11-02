"""
Columns derived from a row's own title + details_text (app/utils/lot_extras.py):
transmission, chassis, interior, options, provenance.

One rule set, used by the backfill (data/migrate_lot_extras.py) and by
enrichment after it stores new details_text, so a row comes out the same
however it got its text.
"""
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.utils.lot_extras import derive

FIELDS = ("transmission", "paint_to_sample", "chassis", "interior", "options", "provenance")


def derive_row(row, distrust_manual: bool = False) -> dict:
    """
    New values for FIELDS. `row` maps id, lot_title, details_text, year,
    model_line and the current FIELDS values.

    paint_to_sample, chassis / interior / options / provenance come only from the text, so
    they are always replaced — that is how a parser fix removes a wrong tag.
    Transmission: a parsed value wins; without one the stored value is kept,
    since ingest may have set it from a structured field (Mecum's).
    distrust_manual: treat a stored "Manual" as unknown. Only for the one-time
    backfill — until 2026-11 "Manual" was every ingest script's default and so
    said nothing; since then ingest stores NULL when it doesn't know.
    """
    parsed = derive(row["lot_title"], row["details_text"], row["year"], row["model_line"])
    out = {}
    for f in FIELDS:
        current = row[f]
        if distrust_manual and f == "transmission" and current == "Manual":
            current = None
        if f == "transmission":
            out[f] = parsed[f] if parsed[f] is not None else current
        elif f == "paint_to_sample" and not row["details_text"]:
            # No page text to judge by: keep a flag an older source set
            # (Broad Arrow's live pages, before they were stripped).
            out[f] = parsed[f] or current
        else:
            out[f] = parsed[f]
    return out


async def refresh(ids: list[int]) -> None:
    """Recompute FIELDS for these rows (just enriched) and write any changes."""
    if not ids:
        return
    cols = ", ".join(FIELDS)
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            f"SELECT id, lot_title, details_text, year, model_line, {cols} "
            "FROM auction_results WHERE id = ANY(:ids)"), {"ids": ids})).mappings().fetchall()
        updates = []
        for row in rows:
            new = derive_row(row)
            if any(new[f] != row[f] for f in FIELDS):
                updates.append({"id": row["id"], **new})
        if updates:
            sets = ", ".join(f"{f} = :{f}" for f in FIELDS)
            await s.execute(text(f"UPDATE auction_results SET {sets} WHERE id = :id"), updates)
            await s.commit()
