"""
Factory "Clubsport" 911s are street-legal (a package on the 964 RS N/GT and RS 3.8,
993 RS, GT2 and GT3 / GT3 RS: registered and titled cars; checked 2026-11-05).
migrate_race_in_street_lines.py had moved every "Clubsport" title to the 911 Race
line. This puts them back on their street card. Race-only cars (GT2 RS Clubsport,
Cup, R, RSR) are not touched.

Dry run by default; --apply writes (old values in data/migrate_clubsport_to_street_undo.json);
--undo restores.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.cards_911 import CARDS  # noqa: E402
from app.utils.generations import get_911_generation  # noqa: E402

UNDO = Path(__file__).with_name("migrate_clubsport_to_street_undo.json")

# (title pattern, street variant) — first match wins.
_RULES = [
    (re.compile(r"GT3\s*RS\s*4\.0", re.I), "GT3 RS 4.0"),
    (re.compile(r"GT3\s*RS", re.I), "GT3 RS"),
    (re.compile(r"GT3", re.I), "GT3"),
    (re.compile(r"GT2", re.I), "GT2"),
    (re.compile(r"Carrera\s+RS\s*3\.8", re.I), "RS 3.8"),
    (re.compile(r"Carrera\s+RS|\bRS\b", re.I), "Carrera RS"),
]


def street_card(year: int, title: str) -> tuple[str, str] | None:
    gen = get_911_generation(year, title)
    for pat, var in _RULES:
        if pat.search(title):
            if var == "RS 3.8" and gen != "964":   # the 993 Carrera RS *is* the 3.8
                var = "Carrera RS"
            return (gen, var) if var in (CARDS.get(gen) or ()) else None
    return None


async def main(apply: bool, undo: bool) -> None:
    async with AsyncSessionLocal() as s:
        if undo:
            for r in json.loads(UNDO.read_text()):
                await s.execute(text("UPDATE auction_results SET model_line=:m, generation=:g, variant=:v WHERE id=:i"),
                                {"m": r["model_line"], "g": r["generation"], "v": r["variant"], "i": r["id"]})
            await s.commit()
            print("restored")
            return
        rows = (await s.execute(text(
            "SELECT id, year, model_line, generation, variant, lot_title FROM auction_results "
            "WHERE model_line='911 Race' AND variant='Clubsport'"))).all()
        moves, unplaced = [], []
        for r in rows:
            tgt = street_card(r.year, r.lot_title or "")
            (moves if tgt else unplaced).append((r, tgt))
        for r, (g, v) in moves:
            print(f"{r.id} {r.year} -> 911 / {g} / {v}  | {r.lot_title[:70]}")
        for r, _ in unplaced:
            print("NO STREET CARD:", r.id, r.year, r.lot_title)
        if not apply:
            return
        UNDO.write_text(json.dumps([{"id": r.id, "model_line": r.model_line, "generation": r.generation,
                                     "variant": r.variant} for r, _ in moves], indent=1))
        for r, (g, v) in moves:
            await s.execute(text("UPDATE auction_results SET model_line='911', generation=:g, variant=:v WHERE id=:i"),
                            {"g": g, "v": v, "i": r.id})
        await s.commit()
        print(len(moves), "moved")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv, "--undo" in sys.argv))
