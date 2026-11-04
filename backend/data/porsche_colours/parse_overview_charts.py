#!/usr/bin/env python3
"""
Parse Porsche's factory paint-colour overview charts ("Lackfarben bei Porsche-
Fahrzeugen", Porsche Classic *-overview-paint-colours.pdf) into rows of
(chart, code, german name, paint system, model year).

Input: `pdftotext -layout` output of each chart. Each table has a header row of
model years; an "X" under a year means the colour was a factory colour that
model year. X marks are assigned to the nearest year column by character
position. The source PDFs are Porsche's and are not committed (public repo);
this script and its output (facts: code / name / year) are.

Usage:
    python parse_overview_charts.py <txt-dir> > factory_palettes_overview.json
"""
import json
import re
import sys
from pathlib import Path

_SECTION = re.compile(r"Lackfarben - Porsche (.+?)\s{2,}")
_YEARS = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
# Paint system column: U1, U2, WU2, M2, WM2, P2, WP2, or a pair like "U2/WU 2".
_PAINT = r"(?:W?[UMP]\s?[12])(?:\s?/\s?W?[UMP]\s?[12])?"
_ROW = re.compile(r"^\s*\(?([0-9A-Z]{3,4})\)?\s{2,}(\S.*?)?\s+(" + _PAINT + r")\s")


def parse(text: str, source: str):
    rows, section, cols = [], None, None
    for page_no, page in enumerate(text.split("\f"), 1):
        lines = page.splitlines()
        for i, line in enumerate(lines):
            m = _SECTION.search(line + "  ")
            if m:
                section = m.group(1).strip()
            years = list(_YEARS.finditer(line))
            if len(years) >= 4 and "system" in line:
                cols = [((y.start() + y.end()) / 2, int(y.group())) for y in years]
                continue
            r = _ROW.match(line)
            if not (r and cols and section):
                continue
            tail_start = r.end(3)
            xs = [i for i, ch in enumerate(line) if ch == "X" and i >= tail_start]
            name = (r.group(2) or "").strip()
            if not name:
                # Two-line names ("amazonasgrün- / perlcolor") sit on the lines
                # above and below the code row in the text layer.
                frag = lambda l: l.strip() if l.strip() and not _ROW.match(l) and " X" not in l and len(l.strip()) < 30 else ""
                name = (frag(lines[i - 1]) + frag(lines[i + 1] if i + 1 < len(lines) else ""))
            for x in xs:
                nearest = min(cols, key=lambda c: abs(c[0] - x))
                if abs(nearest[0] - x) > 5:
                    raise ValueError(f"{source} p{page_no}: X at {x} far from any year: {line!r}")
                rows.append({
                    "chart": section, "code": r.group(1),
                    "name_de": name, "paint": re.sub(r"\s+", "", r.group(3)),
                    "model_year": nearest[1], "source": f"{source} p{page_no}",
                    "bracketed_code": line.lstrip().startswith("("),
                })
    return rows


if __name__ == "__main__":
    out = []
    for f in sorted(Path(sys.argv[1]).glob("*overview-paint-colours.txt")):
        out += parse(f.read_text(), f.name.replace(".txt", ".pdf"))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
