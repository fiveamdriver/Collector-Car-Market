#!/usr/bin/env python3
"""
Aggregate PTSRS evidence rows (parse_ptsrs.py) into the PTS evidence table.

Key: (model_line, generation, variant, colour). PTS is generation- AND
variant-specific — a colour PTS on a 992.1 GT3 says nothing about a 992.1
Carrera or a 996 — so nothing is rolled up across generations or variants.
Colours are grouped by name (codes vary by era: Signal Yellow 114 -> 1YH), and
every code seen is kept; "Slate Grey 6601" and "Slate Grey 7015" stay separate.

Output (outside the public repo): ~/Projects/CollectorCarMarket-data/ptsrs/
    pts_evidence_table.json / .csv, plus unplaced.csv for rows without a generation.
"""
import csv
import json
import os
import re
from collections import defaultdict

DATA_DIR = os.path.expanduser("~/Projects/CollectorCarMarket-data/ptsrs")
_ALIAS = [(r"\bazzuro\b", "azzurro"), (r"\bgray\b", "grey"), (r"^racing green metallic$", "porsche racing green metallic")]


def colour_key(name: str) -> str:
    n = re.sub(r"\s+", " ", name.lower().replace("’", "'")).strip()
    for pat, rep in _ALIAS:
        n = re.sub(pat, rep, n)
    return n


def main():
    rows = json.load(open(os.path.join(DATA_DIR, "ptsrs_evidence.json")))
    # Group within each (model_line, generation, variant): two rows are the same
    # colour if they share a paint code (current or "formerly") or a name.
    unplaced, buckets = [], defaultdict(list)
    for r in rows:
        if not r.get("generation") or not r.get("model_line") or r["model_line"] == "other":
            unplaced.append(r)
            continue
        r["_codes"] = set(r.get("codes") or []) | {
            c for f in r.get("formerly") or [] for c in re.findall(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{3}\b", f)}
        buckets[(r["model_line"], r["generation"], r.get("variant") or "")].append(r)
    table = {}
    for car, rs in buckets.items():
        parent = list(range(len(rs)))
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i
        by_token = {}
        for i, r in enumerate(rs):
            for tok in [("c", c) for c in r["_codes"]] + [("n", colour_key(r["colour"]))]:
                if tok in by_token:
                    parent[find(i)] = find(by_token[tok])
                else:
                    by_token[tok] = i
        groups = defaultdict(list)
        for i, r in enumerate(rs):
            groups[find(i)].append(r)
        for g in groups.values():
            t = {"names": set(), "codes": set(), "german": set(), "finish": set(), "posts": set(),
                 "dates": [], "urls": [], "gen_source": set(), "years": set()}
            for r in g:
                t["names"].add(r["colour"]); t["codes"] |= r["_codes"]
                if r.get("colour_de"): t["german"].add(r["colour_de"])
                if r.get("finish"): t["finish"].add(r["finish"])
                if r["post"] not in t["posts"]:
                    t["posts"].add(r["post"]); t["dates"].append(r["date"]); t["urls"].append(r["url"])
                t["gen_source"].add(r.get("gen_source") or "")
                t["years"].add(r.get("car_year") or int(r["date"][:4]))
            table[car + (colour_key(sorted(t["names"], key=len)[-1]),)] = t
    out = []
    for (line, gen, var, key), t in sorted(table.items()):
        out.append({"model_line": line, "generation": gen, "variant": var, "colour": sorted(t["names"], key=len)[-1], "also_called": sorted(t["names"], key=len)[:-1],
                    "colour_key": key, "codes": sorted(t["codes"]), "german": sorted(t["german"]),
                    "finish": "/".join(sorted(t["finish"])) or None, "posts": len(t["posts"]), "car_years": sorted(t["years"]),
                    "first_seen": min(t["dates"]), "last_seen": max(t["dates"]), "example_posts": t["urls"][:5],
                    "generation_basis": "/".join(sorted(x for x in t["gen_source"] if x))})
    json.dump(out, open(os.path.join(DATA_DIR, "pts_evidence_table.json"), "w"), indent=1, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, "pts_evidence_table.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        for o in out:
            w.writerow({**o, "codes": " ".join(o["codes"]), "german": " ".join(o["german"]),
                        "also_called": " | ".join(o["also_called"]),
                        "example_posts": " ".join(o["example_posts"])})
    with open(os.path.join(DATA_DIR, "unplaced.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "colour", "codes", "model_text_or_sentence", "url"])
        for r in unplaced:
            w.writerow([r["date"], r["colour"], " ".join(r.get("codes") or []), r["sentence"][:200], r["url"]])
    gens = defaultdict(int)
    for o in out:
        gens[(o["model_line"], o["generation"])] += 1
    print(f"{len(out)} (generation, variant, colour) entries from {len(rows)} rows; {len(unplaced)} unplaced")
    for k, v in sorted(gens.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k[0]} {k[1]}")


if __name__ == "__main__":
    main()
