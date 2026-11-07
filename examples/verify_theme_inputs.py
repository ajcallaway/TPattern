"""
verify_theme_inputs.py — prove tpattern and THEME were fed identical input.
==========================================================================

The fidelity comparison in the validation paper rests on both tools reading the
same events. THEME's *pattern output* is not re-derivable (it came from a THEME
Edu v6 GUI run), but THEME's *input files* are archived, so the input side of the
comparison is fully checkable — and this script checks it.

For each group it compares the archived THEME observation files (one plain-text
file per sequence, `time<TAB>event`, delimited by THEME's `:` and `&` markers,
with the event vocabulary in `vvt.vvt`) against the derived event table shipped
in this repository, on: sequence identity, per-sequence event times, and event
types. The repository's `observation` values are the THEME filenames, so the
comparison is one-to-one by construction.

Blank event codes in the THEME files (malformed/empty rows carrying a timestamp
but no event) are reported and excluded: they are not events.

Run:
    python examples/verify_theme_inputs.py --theme-root "<dir containing THEME_*>"
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
GROUPS = {                      # group: (repo csv, archived THEME input dir)
    "Goals":       ("worldcup_goals.csv",              "THEME_Goals"),
    "NonGoals":    ("worldcup_nongoals.csv",           "THEME_NonGoals"),
    "DefRecovery": ("worldcup_defensive_recovery.csv", "THEME_Saved"),
}


def load_repo(path):
    seqs = defaultdict(list)
    with open(path) as fh:
        for row in csv.DictReader(fh):
            seqs[row["observation"]].append((int(row["start"]), row["event"].lower()))
    return {k: sorted(v) for k, v in seqs.items()}


def load_theme(directory):
    """Read THEME's per-sequence input files. Returns (sequences, blank_rows)."""
    seqs, blanks = {}, 0
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        events = []
        for i, line in enumerate(open(path)):
            parts = line.rstrip("\n").split("\t")
            if i == 0 or len(parts) != 2:      # header, or not a time/event row
                continue
            t, event = parts
            if event in (":", "&"):            # THEME's start/end delimiters
                continue
            if event.strip() == "":            # malformed row, no event code
                blanks += 1
                continue
            events.append((int(t), event.strip().lower()))
        seqs[Path(path).stem] = sorted(events)
    return seqs, blanks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-root", required=True,
                    help="directory containing THEME_Goals / THEME_NonGoals / THEME_Saved")
    args = ap.parse_args()
    root = Path(args.theme_root).expanduser()

    total_seq = 0
    all_exact = True
    print(f"{'group':13}{'sequences':>11}{'events':>9}{'blank rows':>12}{'result':>14}")
    for group, (csv_name, theme_dir) in GROUPS.items():
        d = root / theme_dir
        if not d.is_dir():
            print(f"{group:13}{'--':>11}{'--':>9}{'--':>12}{'DIR MISSING':>14}")
            all_exact = False
            continue
        repo = load_repo(DATA / csv_name)
        theme, blanks = load_theme(d)
        n_ev = sum(len(v) for v in repo.values())
        same_ids = set(repo) == set(theme)
        differing = [k for k in repo if repo[k] != theme.get(k)]
        ok = same_ids and not differing
        all_exact &= ok
        total_seq += len(repo)
        print(f"{group:13}{len(repo):>11}{n_ev:>9}{blanks:>12}"
              f"{('EXACT' if ok else 'MISMATCH'):>14}")
        if not ok:
            if not same_ids:
                print(f"    only in repo : {sorted(set(repo) - set(theme))[:5]}")
                print(f"    only in THEME: {sorted(set(theme) - set(repo))[:5]}")
            for k in differing[:3]:
                print(f"    {k}\n      repo : {repo[k][:4]}\n      THEME: {theme.get(k, [])[:4]}")

    print()
    if all_exact:
        print(f"All {total_seq} sequences match exactly: same sequence identifiers, same "
              f"event times, same event types.\nTHEME and tpattern were given identical input.")
        return 0
    print("Input files do NOT match — the fidelity comparison cannot be claimed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
