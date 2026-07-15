"""
Reporting — the output layer THEME does poorly.

Three things:

1. `patterns_table` — a tidy results table for detected patterns: the pattern
   string, N, length, level, loop flag, critical interval, and (when a
   calibration is supplied) the surrogate empirical p with **repeated-testing
   correction** (Benjamini–Hochberg q for screening, Holm/FWER keep for
   confirmation). Writes CSV and returns the rows.

2. `forest_plot` — effect sizes with confidence intervals (odds ratios from the
   group/outcome contrasts) as a forest plot, the standard way to show
   which contrasts matter and how uncertain they are.

3. `report` — one call that writes the table, the top-pattern dendrograms and (if
   given) the forest plot into an output folder, so a detection run yields a
   ready-to-read report.
"""

from __future__ import annotations

import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory

from .pattern import Pattern
from .significance import CalibrationResult, Calibrated
from .viz import patterns_overview


# --------------------------------------------------------------------- table
def _fmt_ci(ci, unit):
    if not ci:
        return ""
    return f"[{ci[0]},{ci[1]}]{unit}"


def patterns_table(source, outfile: str | None = None, ci_unit: str = "",
                   sort: str = "auto"):
    """Build a results table from a list of `Pattern` or a `CalibrationResult`.

    Returns a list of row dicts. If `outfile` is given, also writes CSV.
    When given a CalibrationResult, includes p_emp, fdr_q, fwer_keep and sorts by
    p_emp; otherwise sorts by N (descending).
    """
    calibrated = isinstance(source, CalibrationResult)
    items = source.real if calibrated else [p for p in source if p.level >= 1]

    rows = []
    for it in items:
        p = it.pattern if calibrated else it
        row = {
            "pattern": str(p),
            "signature": p.signature(),
            "N": p.N,
            "length": p.length,
            "level": p.level,
            "loop": int(p.has_loop),
            "critical_interval": _fmt_ci(p.ci, ci_unit),
        }
        if calibrated:
            row["p_emp"] = round(it.p_emp, 4)
            row["fdr_q"] = round(it.fdr_q, 4)
            row["fwer_keep"] = int(it.fwer_keep)
            row["strength"] = round(it.strength, 2)
        rows.append(row)

    key = sort
    if sort == "auto":
        key = "p_emp" if calibrated else "N"
    if key == "N":
        rows.sort(key=lambda r: (-r["N"], r["level"]))
    elif key in ("p_emp", "fdr_q") and calibrated:
        rows.sort(key=lambda r: (r[key], -r["N"]))

    if outfile:
        with open(outfile, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["pattern"])
            w.writeheader()
            w.writerows(rows)
    return rows


# --------------------------------------------------------------- forest plot
def forest_plot(items, outfile: str, title: str = "Effect sizes (odds ratios)",
                xlabel: str = "odds ratio (log scale)"):
    """Forest plot of odds ratios with 95% CIs.

    `items` is a list of dicts, each: {label, or, lo, hi, p (optional), n (opt)}.
    A reference line is drawn at OR = 1. Points whose CI excludes 1 are coloured.
    """
    items = list(items)
    if not items:
        return
    n = len(items)
    fig, ax = plt.subplots(figsize=(9, 0.6 * n + 1.4))
    ys = list(range(n, 0, -1))          # top-to-bottom in given order

    # fix x-range up front so label anchoring is stable on the log scale
    los = [it["lo"] for it in items]; his = [it["hi"] for it in items]
    ax.set_xscale("log")
    ax.set_xlim(min(los) * 0.7, max(his) * 1.35)
    ax.set_ylim(0.3, n + 0.9)
    # label in axes-x (fixed left/right), data-y
    tx = blended_transform_factory(ax.transAxes, ax.transData)

    for y, it in zip(ys, items):
        lo, hi, orr = it["lo"], it["hi"], it["or"]
        sig = lo > 1 or hi < 1
        colour = "#c0392b" if sig else "#7f8c8d"
        ax.plot([lo, hi], [y, y], color=colour, lw=1.8, solid_capstyle="round")
        ax.plot([orr], [y], "o", color=colour, ms=7)
        lbl = it["label"]
        if it.get("p") is not None:
            lbl += f"  (p={it['p']:.3g})"
        ax.text(0.005, y + 0.18, lbl, transform=tx, ha="left", va="bottom", fontsize=8)
        ax.text(0.995, y, f"{orr:.2f} [{lo:.2f}, {hi:.2f}]", transform=tx,
                ha="right", va="center", fontsize=7.5, color="#555")

    ax.axvline(1.0, color="#2c3e50", lw=1.0, ls="--")
    ax.set_yticks([])
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(outfile, dpi=150); plt.close()


# ------------------------------------------------------------------- report
def report(source, outdir: str, *, ci_unit: str = "", title: str = "T-pattern report",
           effects=None, max_dendrograms: int = 8):
    """Write a full report to `outdir`: table (CSV), top-pattern dendrograms and,
    if `effects` given, a forest plot. Returns paths written."""
    os.makedirs(outdir, exist_ok=True)
    calibrated = isinstance(source, CalibrationResult)
    patterns = [c.pattern for c in source.real] if calibrated else \
               [p for p in source if p.level >= 1]

    written = {}
    written["table"] = os.path.join(outdir, "patterns_table.csv")
    rows = patterns_table(source, written["table"], ci_unit=ci_unit)

    if patterns:
        written["dendrograms"] = os.path.join(outdir, "patterns_overview.png")
        patterns_overview(patterns, written["dendrograms"],
                          max_rows=max_dendrograms, ci_unit=ci_unit)

    if effects:
        written["forest"] = os.path.join(outdir, "effect_sizes.png")
        forest_plot(effects, written["forest"])

    # short text summary
    written["summary"] = os.path.join(outdir, "SUMMARY.txt")
    with open(written["summary"], "w") as fh:
        fh.write(f"{title}\n{'=' * len(title)}\n\n")
        fh.write(f"patterns (level >= 1): {len(patterns)}\n")
        if calibrated:
            kept_fdr = len(source.kept('fdr'))
            kept_fwer = len(source.kept('fwer'))
            fh.write(f"null: {source.null}   B={source.B}   "
                     f"alpha={source.alpha}   q_target={source.q_target}\n")
            fh.write(f"kept (FDR q<={source.q_target}): {kept_fdr}\n")
            fh.write(f"kept (FWER Holm): {kept_fwer}\n")
        fh.write("\ntop patterns:\n")
        for r in rows[:15]:
            line = f"  N={r['N']:>3}  L{r['level']}  {r['pattern']}"
            if calibrated:
                line += f"   p_emp={r['p_emp']}  q={r['fdr_q']}"
            fh.write(line + "\n")
    return written
