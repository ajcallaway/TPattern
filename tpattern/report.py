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

import statistics as _stat

from .pattern import Pattern
from .significance import CalibrationResult, Calibrated
from .viz import patterns_overview


# --------------------------------------------------------------- timing / duration
# Every pattern occurrence has a start (first event) and end (last event); their
# difference is the occurrence's duration — for a two-event pattern that is the lag
# from the first event to the second. THEME exposes these only as an on-demand
# "Pattern Duration" export; here they are summarised (median and middle half) and
# reported by default, for every pattern, so the temporal content of a T-pattern is
# not left buried. All times are internal milliseconds (hence the `ms` unit).
def duration_stats(pattern):
    """Summary of a pattern's occurrence durations (end - start), or None if it has
    no occurrences. Returns n, median, mean, q1, q3, min, max — all in ms."""
    ds = sorted(i.end - i.start for i in pattern.instances)
    if not ds:
        return None
    if len(ds) >= 4:
        q1, med, q3 = (round(x) for x in _stat.quantiles(ds, n=4))
    else:
        q1, med, q3 = ds[0], round(_stat.median(ds)), ds[-1]
    return {"n": len(ds), "median": round(_stat.median(ds)), "mean": round(_stat.mean(ds)),
            "q1": q1, "q3": q3, "min": ds[0], "max": ds[-1]}


def _fmt_ci(ci, unit):
    if not ci:
        return ""
    return f"[{ci[0]},{ci[1]}]{unit}"


def interpret(pattern, N, fdr_q, *, q_target=0.05, ci_unit="ms", dur=None):
    """A plain-English reading of one calibrated pattern — what it is, whether it is
    trustworthy, and its observed timing. Used as the results table's
    `interpretation` column so a non-specialist can read the output directly.

    `dur` is the pattern's :func:`duration_stats`; when given, the typical timing is
    stated in words (median and middle half), which is the temporal content THEME's
    output leaves out.
    """
    if fdr_q <= q_target:
        verdict, meaning = (f"Robust (survives FDR, q={fdr_q:.3g})",
                            "a genuine recurring sequence")
    elif fdr_q <= 2 * q_target:
        verdict, meaning = (f"Borderline (q={fdr_q:.3g})",
                            "near the significance threshold — treat with caution and "
                            "re-check with more surrogates")
    else:
        verdict, meaning = (f"Not significant after correction (q={fdr_q:.3g})",
                            "consistent with chance")
    timing = ""
    if dur and dur["median"]:
        lead = ("the later event follows the earlier by a median of "
                if pattern.length == 2 else "the pattern spans a median of ")
        timing = (f"; {lead}{dur['median']} {ci_unit} "
                  f"(middle half {dur['q1']}–{dur['q3']}, range {dur['min']}–{dur['max']} {ci_unit})")
    elif pattern.ci and not pattern.is_terminal:
        d1, d2 = pattern.ci
        timing = (f"; its components are linked within {d1}–{d2} {ci_unit}"
                  if d1 != d2 else f"; components co-occur (0 {ci_unit} apart)")
    loop = " (a recycling loop: a repeated event type)" if pattern.has_loop else ""
    plural = "occurrence" if N == 1 else "occurrences"
    return f"{verdict}: {meaning}, {N} {plural}{timing}{loop}."


def patterns_table(source, outfile: str | None = None, ci_unit: str = "ms",
                   sort: str = "auto", n_observations: int = 0):
    """Build a results table from a list of `Pattern` or a `CalibrationResult`.

    Returns a list of row dicts. If `outfile` is given, also writes CSV.
    When given a CalibrationResult, includes p_emp, fdr_q, fwer_keep and sorts by
    p_emp; otherwise sorts by N (descending).

    Every row carries `bouts` (distinct observations the pattern spans) and
    `bout_support` (that as a fraction of the sample). Prevalence is reported rather
    than filtered on: a reader can apply whatever support threshold they consider
    appropriate, which a pre-applied cut-off would have denied them. Pass
    `n_observations` to get support when `source` is a plain list of patterns.
    """
    calibrated = isinstance(source, CalibrationResult)
    items = source.real if calibrated else [p for p in source if p.level >= 1]
    n_obs = n_observations or (source.n_observations if calibrated else 0)

    rows = []
    for it in items:
        p = it.pattern if calibrated else it
        # Distinct observations (bouts) the pattern spans. N counts occurrences and
        # can exceed this, because one bout may contain the pattern several times.
        # Reported so prevalence is visible as a number: a reader can then apply any
        # support threshold they wish, rather than trusting one applied for them.
        bouts = len({inst.obs for inst in p.instances})
        dur = duration_stats(p)
        row = {
            "pattern": str(p),
            "signature": p.signature(),
            "N": p.N,
            "bouts": bouts,
            "bout_support": round(bouts / n_obs, 4) if n_obs else None,
            "length": p.length,
            "level": p.level,
            "loop": int(p.has_loop),
            "critical_interval": _fmt_ci(p.ci, ci_unit),
            # observed timing of the occurrences (THEME's Pattern Duration, summarised
            # and reported by default rather than left as an on-demand export)
            "duration_median_ms": dur["median"] if dur else None,
            "duration_iqr_ms": f"[{dur['q1']},{dur['q3']}]" if dur else None,
            "duration_range_ms": f"[{dur['min']},{dur['max']}]" if dur else None,
        }
        if calibrated:
            row["p_emp"] = round(it.p_emp, 4)
            row["fdr_q"] = round(it.fdr_q, 4)
            row["fwer_keep"] = int(it.fwer_keep)
            row["analytic_strength"] = round(it.strength, 2)  # -log10(analytic p); comparison only
            row["interpretation"] = interpret(p, it.N, it.fdr_q, ci_unit=ci_unit, dur=dur)
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

    # fix x-range up front so label anchoring is stable on the log scale.
    # An odds-ratio CI can hit 0 or inf when a group has a zero cell, and neither
    # is a valid limit on a log axis, so fall back to sensible finite bounds.
    los = [it["lo"] for it in items]; his = [it["hi"] for it in items]
    pos_lo = [x for x in los if x and x > 0]
    fin_hi = [x for x in his if x not in (float("inf"), float("nan")) and x > 0]
    ax.set_xscale("log")
    ax.set_xlim((min(pos_lo) if pos_lo else 0.1) * 0.7,
                (max(fin_hi) if fin_hi else 10.0) * 1.35)
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


# -------------------------------------------------- extra tables (default outputs)
# THEME produces a menu of statistical export tables, buried under Tools -> Generate
# Tables and off by default. These reproduce the useful ones and emit them by default,
# because the application a user will put them to cannot be predicted and nothing that
# could inform a reading should be hidden.

def _leaves(p):
    """Ordered event-type leaves of a pattern, left to right (temporal order)."""
    if p.is_terminal:
        return [p.event]
    return _leaves(p.left) + _leaves(p.right)


def _patterns_of(source):
    if isinstance(source, CalibrationResult):
        return [c.pattern for c in source.real]
    return [p for p in source if p.level >= 1]


def _write_csv(rows, outfile):
    if outfile and rows:
        with open(outfile, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)


def pattern_durations(source, outfile: str | None = None):
    """One row per pattern *occurrence*: its observation, start, end and duration
    (ms). This is THEME's "Pattern Duration" export, produced by default. The
    per-pattern summary is in `patterns_table` (duration_median_ms etc.); this is the
    raw occurrence-level table for a reader who wants the full distribution."""
    rows = []
    for p in _patterns_of(source):
        for inst in p.instances:
            rows.append({"pattern": str(p), "signature": p.signature(),
                         "observation": inst.obs, "start_ms": inst.start,
                         "end_ms": inst.end, "duration_ms": inst.end - inst.start})
    rows.sort(key=lambda r: (r["signature"], r["start_ms"]))
    _write_csv(rows, outfile)
    return rows


def event_type_roles(source, outfile: str | None = None):
    """For each event type, how often it sits first, in the middle (inner) or last
    within the detected patterns (THEME's "Event-Types in Patterns"). Counts are
    weighted by pattern occurrences (N). Reveals, e.g., which events start chains and
    which end them."""
    from collections import defaultdict
    roles = defaultdict(lambda: {"in_patterns": 0, "as_first": 0, "as_inner": 0, "as_last": 0})
    for p in _patterns_of(source):
        leaves = _leaves(p)
        for i, ev in enumerate(leaves):
            r = roles[ev]; r["in_patterns"] += p.N
            slot = "as_first" if i == 0 else "as_last" if i == len(leaves) - 1 else "as_inner"
            r[slot] += p.N
    rows = []
    for ev, r in sorted(roles.items(), key=lambda kv: -kv[1]["in_patterns"]):
        tot = r["in_patterns"] or 1
        rows.append({"event_type": ev, **r,
                     "pct_first": round(r["as_first"] / tot, 3),
                     "pct_inner": round(r["as_inner"] / tot, 3),
                     "pct_last": round(r["as_last"] / tot, 3)})
    _write_csv(rows, outfile)
    return rows


def connections(source, outfile: str | None = None):
    """For each event type, which other types follow it within at least one detected
    pattern, and how many distinct ones (THEME's "Connections per Event-Type"). A
    compact 'what follows what' view of the detected structure."""
    from collections import defaultdict
    follows = defaultdict(set)
    appears = defaultdict(int)
    for p in _patterns_of(source):
        leaves = _leaves(p)
        for i, a in enumerate(leaves):
            appears[a] += 1
            for b in leaves[i + 1:]:
                follows[a].add(b)
    rows = [{"event_type": ev, "in_patterns": appears[ev],
             "n_followed_by": len(follows[ev]),
             "followed_by": ", ".join(sorted(follows[ev]))}
            for ev in sorted(follows, key=lambda e: -len(follows[e]))]
    _write_csv(rows, outfile)
    return rows


def data_summary(observations, outfile: str | None = None):
    """Descriptive table of the input before any detection: per event type its count,
    how many observations contain it, its mean rate per observation and share of all
    events (THEME's event-type/overview tables). Reported so a reader can see the
    shape of the data that produced the patterns."""
    from collections import Counter, defaultdict
    counts = Counter(); in_obs = defaultdict(set)
    for o in observations:
        for _, ev in o.events:
            counts[ev] += 1; in_obs[ev].add(o.name)
    n_obs = len(observations); n_ev = sum(counts.values()) or 1
    rows = [{"event_type": ev, "count": c, "observations": len(in_obs[ev]),
             "mean_per_observation": round(c / (n_obs or 1), 3),
             "pct_of_events": round(c / n_ev, 4)}
            for ev, c in counts.most_common()]
    _write_csv(rows, outfile)
    return rows


def interval_counts(source, intervals, outfile: str | None = None, split_time=None):
    """Opt-in: count each pattern's occurrences that begin within given time windows,
    and (optionally) before vs after a split time (THEME's "Interval Counts"). Useful
    for phase analysis, e.g. how a pattern's rate differs across halves of a session.
    `intervals` is a list of (t1, t2) pairs in ms."""
    rows = []
    for p in _patterns_of(source):
        starts = [inst.start for inst in p.instances]
        row = {"pattern": str(p), "signature": p.signature(), "N": p.N}
        for t1, t2 in intervals:
            row[f"in[{t1},{t2}]"] = sum(1 for s in starts if t1 <= s <= t2)
        if split_time is not None:
            row["before_split"] = sum(1 for s in starts if s < split_time)
            row["after_split"] = sum(1 for s in starts if s >= split_time)
        rows.append(row)
    _write_csv(rows, outfile)
    return rows


# ------------------------------------------------------------------- report
def report(source, outdir: str, *, ci_unit: str = "ms", title: str = "T-pattern report",
           effects=None, max_dendrograms: int = 8, observations=None):
    """Write a full report to `outdir`: table (CSV), top-pattern dendrograms and,
    if `effects` given, a forest plot. Returns paths written."""
    os.makedirs(outdir, exist_ok=True)
    calibrated = isinstance(source, CalibrationResult)
    patterns = [c.pattern for c in source.real] if calibrated else \
               [p for p in source if p.level >= 1]

    written = {}
    written["table"] = os.path.join(outdir, "patterns_table.csv")
    rows = patterns_table(source, written["table"], ci_unit=ci_unit)

    # extra default tables (nothing hidden): per-occurrence durations, event-type
    # roles, connections, and — if the raw observations are passed — a data summary.
    written["durations"] = os.path.join(outdir, "pattern_durations.csv")
    pattern_durations(source, written["durations"])
    written["roles"] = os.path.join(outdir, "event_type_roles.csv")
    event_type_roles(source, written["roles"])
    written["connections"] = os.path.join(outdir, "connections.csv")
    connections(source, written["connections"])
    if observations is not None:
        written["data_summary"] = os.path.join(outdir, "data_summary.csv")
        data_summary(observations, written["data_summary"])

    if patterns:
        written["dendrograms"] = os.path.join(outdir, "patterns_overview.png")
        patterns_overview(patterns, written["dendrograms"],
                          max_rows=max_dendrograms, ci_unit=ci_unit)
        # temporal-signature plot: the per-occurrence duration spread per pattern
        from .viz import duration_plot
        written["durations_plot"] = os.path.join(outdir, "pattern_durations.png")
        duration_plot(source, written["durations_plot"], max_rows=max_dendrograms,
                      ci_unit=ci_unit)

    if observations is not None:
        from .viz import occurrence_plot
        written["occurrence_plot"] = os.path.join(outdir, "event_occurrences.png")
        occurrence_plot(observations, written["occurrence_plot"])

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
