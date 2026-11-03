#!/usr/bin/env python3
"""
One entry point for scheduled data collection.

    python data/run_ingest.py due        # what the schedule says is due today (run daily)
    python data/run_ingest.py due --dry-run              # ...just show it
    python data/run_ingest.py monthly    # every source: new results + lot details
    python data/run_ingest.py presale    # Broad Arrow catalogues for upcoming sales
    python data/run_ingest.py monthly --only bat rm     # a subset, same procedure

due  (the scheduler runs this once a day; it usually exits in a second)
    Broad Arrow follows its sale calendar (SALE_CALENDAR in
    broad_arrow_ingest.py): catalogue capture 10, 5 and 2 days before each
    sale, results ingest 3 and 10 days after. Every other source runs monthly.
    Each job is recorded once done (~/Projects/CollectorCarMarket-data/
    schedule_state.json), so a day the Mac was asleep is caught up at the next
    run — a pre-sale capture only while the sale is still ahead.

monthly
    1. Back up the database (data/backup_db.py).
    2. Each source's ingest. Every ingest script adds new results and then
       fetches its new lots' detail pages (enrichment), which sets mileage,
       exact color, PTS, Sonderwunsch, transmission and the rest through the
       shared, tested parsers in app/utils.
    3. Taxonomy preflight (frontend `npm run preflight`): new rows whose
       generation/variant has no card on the site.
    4. Coverage report (enrich_details.py --stats).

presale  (run weekly, or a few days before every Broad Arrow sale)
    Broad Arrow deletes a lot's description once the sale is over, so it must
    be captured while the lot is listed (data/broad_arrow_presale.py). The
    monthly Broad Arrow ingest then uses the kept catalogue.

Every step runs as its own process with a time limit, so one failing source
cannot stop the others or hang the run. Output goes to
~/Projects/CollectorCarMarket-data/logs/<mode>_<timestamp>.log. Exit status is
non-zero when any step failed, so a scheduler can report it.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
PYTHON = sys.executable
DATA_DIR = Path.home() / "Projects" / "CollectorCarMarket-data"
LOG_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "schedule_state.json"

PRESALE_DAYS_BEFORE = (10, 5, 2)
RESULTS_DAYS_AFTER = (3, 10)
MONTHLY_DAY = 1          # other sources: on/after the 1st of each month

HOUR = 3600
# (key, command, time limit). Order: the quick structured APIs first, Broad
# Arrow (archive.org pacing) last.
SOURCES = [
    ("bat",         [PYTHON, "data/bat_ingest.py"],         6 * HOUR),
    ("rm",          [PYTHON, "data/rms_ingest.py"],         3 * HOUR),
    ("gooding",     [PYTHON, "data/gooding_ingest.py"],     2 * HOUR),
    ("mecum",       [PYTHON, "data/mecum_ingest.py"],       3 * HOUR),
    ("bonhams",     [PYTHON, "data/bonhams_ingest.py"],     2 * HOUR),
    ("broad-arrow", [PYTHON, "data/broad_arrow_ingest.py"], 6 * HOUR),
]


def run_step(name: str, cmd: list[str], limit: int, log, cwd: Path = BACKEND_DIR) -> bool:
    started = time.monotonic()
    log.write(f"\n===== {name}: {' '.join(str(c) for c in cmd)}  [{datetime.now():%Y-%m-%d %H:%M}]\n")
    log.flush()
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                              timeout=limit, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        ok = proc.returncode == 0
        status = "ok" if ok else f"FAILED (exit {proc.returncode})"
    except subprocess.TimeoutExpired:
        ok, status = False, f"FAILED (time limit {limit // 60} min)"
    except OSError as exc:
        ok, status = False, f"FAILED ({exc})"
    mins = (time.monotonic() - started) / 60
    line = f"===== {name}: {status} after {mins:.0f} min\n"
    log.write(line)
    log.flush()
    print(line.strip(), flush=True)
    return ok


# ── Schedule ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1, sort_keys=True))


def due_jobs(today: date, state: dict) -> list[tuple[str, str, list[str] | None]]:
    """
    [(job id, mode, sources)] due today and not yet done. A job id names one
    scheduled occurrence ("presale 2026-11-07 -5"), so each runs once.
    """
    from data.broad_arrow_ingest import SALE_CALENDAR
    jobs = []
    presale_due = results_due = None
    for sale, name in SALE_CALENDAR:
        for d in PRESALE_DAYS_BEFORE:
            jid = f"presale {sale} -{d}"
            # Due from its day until the sale; never after (nothing to capture).
            if sale - timedelta(days=d) <= today < sale and jid not in state:
                presale_due = presale_due or jid
                state.setdefault("_pending", []).append(jid)
        for d in RESULTS_DAYS_AFTER:
            jid = f"broad-arrow results {sale} +{d}"
            if today >= sale + timedelta(days=d) and jid not in state:
                results_due = results_due or jid
                state.setdefault("_pending", []).append(jid)
    # Several overdue occurrences collapse into one run.
    if presale_due:
        jobs.append((presale_due, "presale", None))
    if results_due:
        jobs.append((results_due, "monthly", ["broad-arrow"]))
    month = f"monthly {today:%Y-%m}"
    if today.day >= MONTHLY_DAY and month not in state:
        others = [k for k, *_ in SOURCES if k != "broad-arrow"]
        jobs.append((month, "monthly", others))
        state.setdefault("_pending", []).append(month)
    return jobs


def run_mode(mode: str, sources: list[str] | None, backup: bool, log) -> list[tuple[str, bool]]:
    results: list[tuple[str, bool]] = []
    if mode == "presale":
        results.append(("broad-arrow presale",
                        run_step("broad-arrow presale", [PYTHON, "data/broad_arrow_presale.py"],
                                 3 * HOUR, log)))
        return results
    if backup:
        ok = run_step("backup", [PYTHON, "data/backup_db.py"], 1 * HOUR, log)
        results.append(("backup", ok))
        if not ok:
            print("Backup failed — not ingesting.", flush=True)  # no safety copy, no writes
            return results
    for key, cmd, limit in SOURCES:
        if sources and key not in sources:
            continue
        results.append((key, run_step(key, cmd, limit, log)))
    results.append(("taxonomy preflight",
                    run_step("taxonomy preflight", ["npm", "run", "--silent", "preflight"],
                             15 * 60, log, cwd=ROOT_DIR / "frontend")))
    run_step("coverage", [PYTHON, "data/enrich_details.py", "--stats"], 15 * 60, log)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["due", "monthly", "presale"])
    parser.add_argument("--dry-run", action="store_true", help="due: list what is due, run nothing")
    parser.add_argument("--only", nargs="+", metavar="SOURCE",
                        help=f"monthly: only these sources ({', '.join(k for k, *_ in SOURCES)})")
    parser.add_argument("--no-backup", action="store_true", help="monthly: skip the backup step")
    args = parser.parse_args()

    unknown = set(args.only or []) - {k for k, *_ in SOURCES}
    if unknown:
        parser.error(f"unknown source(s): {', '.join(sorted(unknown))}")

    if args.mode == "due":
        sys.path.insert(0, str(BACKEND_DIR))
        state = load_state()
        jobs = due_jobs(date.today(), state)
        pending = state.pop("_pending", [])
        if not jobs:
            print(f"{date.today()}: nothing due.", flush=True)
            return 0
        for jid, mode, sources in jobs:
            print(f"due: {jid}  ->  {mode} {' '.join(sources or [])}".rstrip(), flush=True)
        if args.dry_run:
            return 0
    else:
        jobs = [(None, args.mode, args.only)]
        pending = []

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{args.mode}_{datetime.now():%Y%m%d_%H%M}.log"
    print(f"Logging to {log_path}", flush=True)
    results: list[tuple[str, bool]] = []
    with open(log_path, "a") as log:
        for jid, mode, sources in jobs:
            step_results = run_mode(mode, sources, backup=not args.no_backup, log=log)
            results += step_results
            if jid and all(ok for _, ok in step_results):
                # Mark this occurrence and the overdue ones it stood in for.
                state = load_state()
                kind = jid.split(" 20")[0]
                for p in [jid] + [p for p in pending if p.split(" 20")[0] == kind]:
                    state[p] = datetime.now().isoformat(timespec="minutes")
                save_state(state)

        failed = [name for name, ok in results if not ok]
        summary = (f"\n{args.mode} run finished {datetime.now():%Y-%m-%d %H:%M}: "
                   f"{len(results) - len(failed)}/{len(results)} steps ok"
                   + (f"; FAILED: {', '.join(failed)}" if failed else ""))
        log.write(summary + "\n")
    print(summary.strip(), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
