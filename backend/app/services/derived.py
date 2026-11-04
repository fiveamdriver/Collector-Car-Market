"""
Columns derived from a row's own title + details_text (app/utils/lot_extras.py):
transmission, chassis, interior, options, provenance.

One rule set, used by the backfill (data/migrate_lot_extras.py) and by
enrichment after it stores new details_text, so a row comes out the same
however it got its text.
"""
import re

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.utils.cards_911 import target_variant
from app.utils.generations import get_911_generation
from app.utils.lot_extras import derive

# Street-911 generations a VIN can re-file a car between (race and coachbuilt
# lines keep their own taxonomy).
_REFILE_GENS = {"G-Body", "964", "993", "996.1", "996.2", "997.1", "997.2",
                "991.1", "991.2", "992.1", "992.2"}

_PTS_EVIDENCE_RE = re.compile(
    r'paint[-\s]?to[-\s]?sample|\bPTS\b|\b(?:special|custom)[-\s]?order|\b00501\b|\bL999\b',
    re.IGNORECASE)

_VALID_VIN = re.compile(r"^WP0[A-HJ-NPR-Z0-9]{14}$")

# Paint-to-sample decided by hand; wins over the text parser on every re-derive.
# id -> (paint_to_sample, why). Added after review of the factory-colour dry run
# (data/porsche_colours/pts_dry_run.py): each colour is on Porsche's own list for
# that model year, and the owner confirmed none of these is PTS.
PTS_OVERRIDES: dict[int, tuple[bool, str]] = {
    561:   (False, "918 Liquid Metal Silver: listed 918 special colour (918 brochure p2); reviewed 2026-11-03"),
    17432: (False, "964 Turbo 3.6 Grand Prix White: on 964 chart MY1994; 'special-order' = interior; reviewed 2026-11-03"),
    18234: (False, "993 Turbo Polar Silver: on 993 chart MY1994-96 despite seller's PTS claim; reviewed 2026-11-03"),
    27971: (False, "964 Turbo 3.6 Midnight Blue Metallic: on 964 chart MY1994, no PTS text; reviewed 2026-11-03"),
    # @ptsrs cross-check (data/ptsrs/crosscheck_auctions.py), owner-confirmed 2026-11-04
    1542:  (True,  "2018 991.2 GT3 Nardo Grey (Y7C): PTS on 991.2 GT3 per @ptsrs Bsg2mNun9vv; owner-confirmed 2026-11-04"),
    14864: (True,  "2021 718 GT4 Pastel Orange (Z17): PTS per @ptsrs CMsBjNYnP2P; owner-confirmed 2026-11-04"),
    14778: (True,  "2023 718 GT4 RS Grey Black (7GS): PTS per @ptsrs C-A7m-VvQNH; owner-confirmed 2026-11-04"),
    26173: (True,  "2019 991.2 GT3 RS Brewster Green (22B): PTS per @ptsrs CDwN8mIHWo7; owner-confirmed 2026-11-04"),
    30426: (True,  "2022 992 Targa Bahama Yellow (Z14): PTS per @ptsrs CYfEw7HveNg; owner-confirmed 2026-11-04"),
    10600: (False, "2023 992 Sport Classic in Sport Classic Grey: the model's own listed colour; owner-confirmed not PTS 2026-11-04"),
}

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
    parsed = derive(row["lot_title"], row["details_text"], row["year"], row["model_line"],
                    row.get("generation"), row.get("variant"))
    out = {}
    for f in FIELDS:
        current = row[f]
        if distrust_manual and f == "transmission" and current == "Manual":
            current = None
        if f == "transmission":
            out[f] = parsed[f] if parsed[f] is not None else current
        elif f == "chassis" and parsed[f] is None and _VALID_VIN.match(current or ""):
            # A 17-digit VIN read from the lot page header (data/migrate_
            # facelift_boundaries.py backfill) isn't in details_text; it decides
            # the car's generation, so a re-parse must not erase it.
            out[f] = current
        elif f == "paint_to_sample" and not _PTS_EVIDENCE_RE.search(
                f'{row["lot_title"] or ""} {row["details_text"] or ""}'):
            # Nothing in the text speaks to the paint order either way (no
            # text, or a stripped post-sale page): keep a flag an older source
            # set (Broad Arrow's live pages, before they were stripped). When
            # the text does discuss it, the parser decides — that is how a
            # parser fix removes a wrong flag.
            out[f] = parsed[f] or current
        else:
            out[f] = parsed[f]
    if row.get("id") in PTS_OVERRIDES:
        out["paint_to_sample"] = PTS_OVERRIDES[row["id"]][0]
    return out


async def refresh(ids: list[int]) -> None:
    """Recompute FIELDS for these rows (just enriched) and write any changes."""
    if not ids:
        return
    cols = ", ".join(FIELDS)
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            f"SELECT id, lot_title, details_text, year, model_line, generation, variant, {cols} "
            "FROM auction_results WHERE id = ANY(:ids)"), {"ids": ids})).mappings().fetchall()
        updates, refiles = [], []
        for row in rows:
            new = derive_row(row)
            if any(new[f] != row[f] for f in FIELDS):
                updates.append({"id": row["id"], **new})
            # A VIN found in the new text is the best evidence of model year and
            # chassis: re-file the car if it now points at another generation.
            if (row["model_line"] == "911" and row["generation"] in _REFILE_GENS
                    and row["year"] and new["chassis"]):
                gen = get_911_generation(row["year"], row["lot_title"] or "", new["chassis"])
                var = target_variant(row["variant"], gen) if gen != row["generation"] else None
                if var:
                    refiles.append({"id": row["id"], "generation": gen, "variant": var})
        if updates:
            sets = ", ".join(f"{f} = :{f}" for f in FIELDS)
            await s.execute(text(f"UPDATE auction_results SET {sets} WHERE id = :id"), updates)
        if refiles:
            await s.execute(text("UPDATE auction_results SET generation = :generation, "
                                 "variant = :variant WHERE id = :id"), refiles)
        if updates or refiles:
            await s.commit()
