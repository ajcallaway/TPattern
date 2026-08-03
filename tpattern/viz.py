"""
Visual output for detected T-patterns — clean, publication-ready figures.

The centrepiece is `pattern_dendrogram`: a T-pattern is a binary tree of
critical-interval links, and this draws it as a proper dendrogram — event types
as leaves, each internal join annotated with its critical interval [d1, d2] (the
time window within which the right side follows the left). THEME draws this as a
cramped detection tree; here it is a clean, labelled figure.
"""

from __future__ import annotations

import statistics as _stat

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .pattern import Pattern


# --------------------------------------------------------------------- styling
# One place to change how every figure looks. Edit these values (or set them at
# run time, e.g. `tpattern.viz.STYLE["accent"] = "#0b7285"`) to restyle all plots
# without touching the plotting code — colours, fonts, grid and resolution are all
# read from here. Kept deliberately small and legible so it is easy to customise.
STYLE = {
    "node":     "#2980b9",   # event-type leaf markers
    "line":     "#34495e",   # dendrogram links
    "interval": "#c0392b",   # timing annotations
    "accent":   "#4a6fa5",   # primary bar/point colour
    "accent2":  "#c07a3e",   # secondary group colour
    "muted":    "#8a93a3",   # captions, secondary text
    "text":     "#1a1c22",   # primary text
    "grid":     "#dfe3e8",   # gridlines
    "font_size": 8.0,
    "title_size": 10.5,
    "dpi": 150,
}


def _tidy(ax, *, grid_axis=None):
    """Apply the shared look to an Axes: drop the top/right frame, optional soft grid."""
    ax.spines[["top", "right"]].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=STYLE["grid"], lw=0.7, zorder=0)
    ax.tick_params(labelsize=STYLE["font_size"] - 0.5)
    return ax


def _median_duration(p):
    """Median of a (sub)pattern's occurrence durations in ms, or None."""
    ds = [i.end - i.start for i in p.instances]
    return round(_stat.median(ds)) if ds else None


def _layout(p: Pattern, leaves: list, pos: dict):
    """Assign (x, depth) to every node. Leaves get sequential x; internal nodes
    sit at the mid-x of their children, depth = 1 + max child depth."""
    if p.is_terminal:
        x = len(leaves)
        leaves.append(p.event)
        pos[id(p)] = (x, 0)
        return x, 0
    lx, ld = _layout(p.left, leaves, pos)
    rx, rd = _layout(p.right, leaves, pos)
    x = (lx + rx) / 2.0
    d = 1 + max(ld, rd)
    pos[id(p)] = (x, d)
    return x, d


def _draw(p: Pattern, pos: dict, ax, ci_unit: str):
    """Recursively draw dendrogram elbows from each internal node to its children."""
    if p.is_terminal:
        return
    x, d = pos[id(p)]
    for child in (p.left, p.right):
        cx, cd = pos[id(child)]
        # elbow: up from child to this node's depth, then across
        ax.plot([cx, cx], [cd, d], color=STYLE["line"], lw=1.4)
        ax.plot([cx, x], [d, d], color=STYLE["line"], lw=1.4)
        _draw(child, pos, ax, ci_unit)
    # annotate the join with the OBSERVED median timing (the interpretable value) and,
    # smaller, the critical interval it was accepted within.
    med = _median_duration(p)
    if med is not None:
        ax.annotate(f"~{med} {ci_unit}".strip(), (x, d), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=7, fontweight="bold",
                    color=STYLE["interval"])
    if p.ci is not None:
        d1, d2 = p.ci
        ax.annotate(f"[{d1},{d2}]", (x, d), textcoords="offset points",
                    xytext=(0, -9), ha="center", fontsize=6, color=STYLE["muted"])


def pattern_dendrogram(pattern: Pattern, title: str | None = None,
                       ci_unit: str = "", outfile: str | None = None, ax=None):
    """Draw one T-pattern as a dendrogram. Returns the Axes.

    Leaves (event types) are labelled along the bottom in temporal order; each
    internal join shows its critical interval. `pattern.N` and significance can
    be put in the title.
    """
    leaves: list = []
    pos: dict = {}
    _layout(pattern, leaves, pos)

    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(max(4, 1.1 * len(leaves)), 3.2))
    _draw(pattern, pos, ax, ci_unit)

    # leaf labels
    for i, name in enumerate(leaves):
        ax.plot([i], [0], "o", color=STYLE["node"], ms=6)
        ax.annotate(name, (i, 0), textcoords="offset points", xytext=(0, -8),
                    ha="right", va="top", rotation=35, fontsize=8)

    ax.set_xlim(-0.7, len(leaves) - 0.3)
    ax.set_ylim(-1.2, pattern.level + 0.6)
    ax.set_yticks(range(pattern.level + 1))
    ax.set_ylabel("level")
    ax.set_xticks([])
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    if title:
        ax.set_title(title, fontsize=9, wrap=True)

    if own and outfile:
        plt.tight_layout(); plt.savefig(outfile, dpi=150); plt.close()
    return ax


def patterns_overview(patterns: list, outfile: str, max_rows: int = 8,
                      ci_unit: str = "", by=lambda p: -p.N):
    """A grid of the top pattern dendrograms (by `by`, default most frequent)."""
    comps = sorted([p for p in patterns if p.level >= 1], key=by)[:max_rows]
    n = len(comps)
    if not n:
        return
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.0 * rows))
    # plt.subplots returns an ndarray whenever rows*cols > 1 (cols is always 2 here,
    # so even a single pattern yields a 2-axis array); flatten it, else wrap the lone Axes.
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
    for ax, p in zip(axes, comps):
        pattern_dendrogram(p, title=f"N={p.N}, level {p.level}", ci_unit=ci_unit, ax=ax)
    for ax in axes[n:]:
        ax.axis("off")
    plt.tight_layout(); plt.savefig(outfile, dpi=150); plt.close()


def support_profile(result, outfile: str, title: str | None = None,
                    mark_thresholds=(0.10, 0.25), max_rows: int = 25,
                    method: str = "fdr", color_by=None, highlight=None):
    """Ranked bout-support profile of the patterns that survived calibration.

    One bar per surviving pattern, ordered by the fraction of observations (bouts)
    it spans. This reports prevalence instead of filtering on it: the reader sees
    each pattern's spread directly and can apply whatever support threshold they
    consider defensible.

    `mark_thresholds` draws reference lines for candidate thresholds. Read them as
    "everything below this line would be deleted", not as recommended values. A
    knee in this profile separates common patterns from rare ones; it does NOT
    separate real from chance, because calibration has already done that. Cutting
    at a knee therefore removes rare patterns that are demonstrably not noise, and
    on real data the knee ordering and the evidence ordering can disagree entirely.

    Colouring the bars answers a question that generalises to any dataset: *does some
    family of events cluster at one end of the prevalence range?* Two ways to ask it:

    * ``highlight="LooseBall"`` (or a list of terms) colours every pattern whose
      signature contains that text. No code needed, works with whatever labels your
      own coding scheme uses.
    * ``color_by=fn`` takes a callable mapping a signature to a group label, for
      groupings a substring cannot express.

    Leave both None for a single colour.

    Returns the list of (signature, support) pairs actually plotted.
    """
    if color_by is None and highlight:
        terms = [highlight] if isinstance(highlight, str) else list(highlight)

        def color_by(sig, _terms=terms):
            hit = next((t for t in _terms if t.lower() in sig.lower()), None)
            return f"contains {hit}" if hit else "other patterns"

    n_obs = getattr(result, "n_observations", 0)
    items = []
    for c in result.kept(method):
        bouts = len({inst.obs for inst in c.pattern.instances})
        items.append((c.pattern.signature(), bouts, bouts / n_obs if n_obs else 0.0))
    items.sort(key=lambda x: -x[2])
    shown = items[:max_rows]

    n = len(shown)
    # Long signatures are unreadable as rotated tick labels once there are more than
    # a handful of bars, so rank-number them and let the caller print the key (the
    # returned list) into the caption. Identity is recoverable, the shape stays clean.
    number_bars = n > 6
    fig, ax = plt.subplots(
        figsize=((max(7.0, 0.42 * n + 2.2), 4.9) if number_bars
                 else (max(6.0, 1.15 * n + 2.6), 5.2)), dpi=200)
    if not shown:
        ax.text(0.5, 0.5, "No pattern survived calibration,\nso there is no prevalence to report.",
                ha="center", va="center", fontsize=10, color="#5b6270")
        ax.axis("off")
    else:
        xs = range(n)
        sup = [s for _, _, s in shown]
        if color_by is None:
            bar_colors = "#4a6fa5"
        else:
            palette = ["#4a6fa5", "#c07a3e", "#5b8c5a", "#8a6d9a"]
            groups, seen = [], {}
            for sig, _, _ in shown:
                g = color_by(sig)
                seen.setdefault(g, palette[len(seen) % len(palette)])
                groups.append(g)
            bar_colors = [seen[g] for g in groups]
        bars = ax.bar(list(xs), sup, color=bar_colors, edgecolor="#2c4a72",
                      width=0.68, zorder=3)
        if color_by is not None:
            from matplotlib.patches import Patch
            ax.legend(handles=[Patch(facecolor=c, edgecolor="#2c4a72", label=g)
                               for g, c in seen.items()],
                      fontsize=7.4, frameon=False, loc="upper right")
        ax.set_xticks(list(xs))
        if number_bars:
            ax.set_xticklabels([str(i + 1) for i in xs], fontsize=7.6)
            ax.set_xlabel("pattern, ranked by prevalence (see caption for identities)",
                          fontsize=8.4)
        else:
            ax.set_xticklabels([sig if len(sig) <= 34 else sig[:31] + "..."
                                for sig, _, _ in shown],
                               rotation=45, ha="right", fontsize=6.6)
        ax.set_ylabel("bout support\n(fraction of observations the pattern appears in)",
                      fontsize=8.4)
        top = max(sup)
        for i, (_, b, s) in enumerate(shown):
            ax.text(i, s + top * 0.022, f"{s:.1%}", ha="center", va="bottom",
                    fontsize=6.2, color="#1a1c22", zorder=4)
        for thr in mark_thresholds or ():
            lost = sum(1 for _, _, s in items if s < thr)
            ax.axhline(thr, color="#b0303a", lw=1.1, ls="--", alpha=0.85, zorder=1)
            ax.text(n - 0.4, thr, f"  {thr:.0%} would delete {lost} of {len(items)}",
                    fontsize=6.8, color="#b0303a", va="bottom", ha="right")
        ax.set_ylim(0, max(top * 1.30,
                           (max(mark_thresholds) if mark_thresholds else 0) * 1.15))
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25, lw=0.6, zorder=0)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
    if title:
        ax.set_title(title, fontsize=10.5, fontweight="bold")
    if len(items) > max_rows:
        fig.text(0.99, 0.005, f"showing {max_rows} of {len(items)} surviving patterns",
                 ha="right", fontsize=6.8, color="#8a93a3")
    fig.tight_layout()
    fig.savefig(outfile)
    plt.close(fig)
    return [(sig, s) for sig, _, s in items]


def null_comparison_plot(comparison, outfile, title=None, max_rows=25):
    """Grid of which surrogate nulls each pattern survives, so the DIFFERENCE reads
    at a glance. One row per pattern (surviving under at least one null), one column
    per null; a filled cell means the pattern survives that null, annotated with its
    q-value. Patterns are grouped core-first, then each null's unique (shell) set.

    `comparison` is a NullComparison from compare_nulls(). Returns the rows plotted.
    """
    nulls = comparison.nulls
    # order: core first, then each null's unique set, most significant within group
    def _minq(sig):
        return min((comparison._q(n, sig) or 1.0) for n in nulls)
    ordered = ([s for s in sorted(comparison.common, key=_minq)]
               + [s for n in nulls for s in sorted(comparison.unique[n], key=_minq)])
    seen = set()
    ordered = [s for s in ordered if not (s in seen or seen.add(s))][:max_rows]
    if not ordered:
        fig, ax = plt.subplots(figsize=(6, 2), dpi=200)
        ax.text(0.5, 0.5, "No pattern survived under any null.", ha="center", va="center")
        ax.axis("off"); fig.savefig(outfile); plt.close(fig); return []

    GREEN, GREY, EDGE = "#2f7d4f", "#e4e7ec", "#333"
    nrow, ncol = len(ordered), len(nulls)
    fig, ax = plt.subplots(figsize=(3.0 + 1.5 * ncol, 1.1 + 0.42 * nrow), dpi=200)
    for r, sig in enumerate(ordered):
        y = nrow - 1 - r
        layer = comparison.layer(sig)
        for c, n in enumerate(nulls):
            surv = sig in comparison.survives[n]
            ax.add_patch(plt.Rectangle((c, y), 0.92, 0.92, facecolor=GREEN if surv else GREY,
                                       edgecolor=EDGE, lw=0.6))
            q = comparison._q(n, sig)
            if q is not None:
                ax.text(c + 0.46, y + 0.46, f"{q:.3f}", ha="center", va="center",
                        fontsize=7.5, color="white" if surv else "#8a93a3",
                        fontweight="bold" if surv else "normal")
        ax.text(ncol + 0.15, y + 0.46, f"{sig}", ha="left", va="center", fontsize=7.4)
        ax.text(-0.15, y + 0.46, layer, ha="right", va="center", fontsize=6.8,
                color="#5b6270", style="italic")
    ax.set_xlim(-2.4, ncol + 6.5); ax.set_ylim(-0.3, nrow + 0.2)
    for c, n in enumerate(nulls):
        ax.text(c + 0.46, nrow + 0.02, n, ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left")
    fig.text(0.5, 0.005, "filled = survives that null (q shown); core = survives all nulls, "
             "shell = survives one null only", ha="center", fontsize=6.8, color="#8a93a3")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(outfile)
    plt.close(fig)
    return ordered


def occurrence_plot(observations, outfile: str, title: str | None = None,
                    max_types: int = 25):
    """When does each event type happen? A strip plot of every occurrence's position
    within its observation (0 = start of the window, 1 = end), one row per event type,
    with the median marked. This is THEME's event-type occurrence view, and it shows
    directly whether a type clusters early or late — the same structure the
    conditional-uniformity diagnostic tests. Returns the event types plotted."""
    from collections import defaultdict
    pos = defaultdict(list)
    for o in observations:
        T = (o.end - o.start) or 1
        for t, ev in o.events:
            pos[ev].append((t - o.start) / T)
    types = sorted(pos, key=lambda e: _stat.median(pos[e]))
    types = types[:max_types]
    n = len(types)
    fig, ax = plt.subplots(figsize=(7.5, max(2.0, 0.32 * n + 1.0)), dpi=STYLE["dpi"])
    for y, ev in enumerate(types):
        xs = pos[ev]
        ax.scatter(xs, [y] * len(xs), s=10, color=STYLE["accent"], alpha=0.35,
                   edgecolors="none", zorder=2)
        ax.plot([_stat.median(xs)], [y], "|", color=STYLE["interval"], ms=16,
                mew=2.2, zorder=3)
    ax.set_yticks(range(n)); ax.set_yticklabels(types, fontsize=STYLE["font_size"] - 1)
    ax.set_xlim(-0.02, 1.02); ax.set_xlabel("position within observation (0 = start, 1 = end)",
                                            fontsize=STYLE["font_size"])
    ax.set_ylim(-0.6, n - 0.4)
    _tidy(ax, grid_axis="x")
    ax.set_title(title or "When each event type occurs", fontsize=STYLE["title_size"],
                 fontweight="bold")
    fig.text(0.99, 0.005, "red mark = median position", ha="right",
             fontsize=STYLE["font_size"] - 1.5, color=STYLE["muted"])
    fig.tight_layout(); fig.savefig(outfile); plt.close(fig)
    return types


def duration_plot(source, outfile: str, title: str | None = None, max_rows: int = 8,
                  ci_unit: str = "ms"):
    """Temporal signature of each pattern: a strip of its occurrence durations (ms),
    one row per pattern, median marked. Turns 'N=14, q=.006' into a picture of *when*
    the later event lands relative to the earlier. Returns the patterns plotted."""
    from .significance import CalibrationResult
    if isinstance(source, CalibrationResult):
        pats = [c.pattern for c in source.real]
    else:
        pats = [p for p in source if p.level >= 1]
    pats = sorted(pats, key=lambda p: -p.N)[:max_rows]
    pats = [p for p in pats if p.instances]
    n = len(pats)
    if not n:
        fig, ax = plt.subplots(figsize=(6, 2), dpi=STYLE["dpi"])
        ax.text(0.5, 0.5, "No patterns to plot.", ha="center", va="center")
        ax.axis("off"); fig.savefig(outfile); plt.close(fig); return []
    fig, ax = plt.subplots(figsize=(7.5, max(2.0, 0.5 * n + 1.0)), dpi=STYLE["dpi"])
    labels = []
    for y, p in enumerate(pats):
        ds = sorted(i.end - i.start for i in p.instances)
        ax.scatter(ds, [y] * len(ds), s=22, color=STYLE["accent"], alpha=0.5,
                   edgecolors="none", zorder=2)
        med = _stat.median(ds)
        ax.plot([med], [y], "|", color=STYLE["interval"], ms=18, mew=2.4, zorder=3)
        ax.annotate(f"~{round(med)} {ci_unit}", (med, y), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=STYLE["font_size"] - 1.5,
                    color=STYLE["interval"])
        sig = p.signature()
        labels.append(sig if len(sig) <= 40 else sig[:37] + "...")
    ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=STYLE["font_size"] - 1)
    ax.set_ylim(-0.6, n - 0.2)
    ax.set_xlabel(f"pattern occurrence duration ({ci_unit})", fontsize=STYLE["font_size"])
    ax.set_xlim(left=0)
    _tidy(ax, grid_axis="x")
    ax.set_title(title or "Temporal signature (duration of each pattern's occurrences)",
                 fontsize=STYLE["title_size"], fontweight="bold")
    fig.tight_layout(); fig.savefig(outfile); plt.close(fig)
    return pats
