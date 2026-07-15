"""
Visual output for detected T-patterns — clean, publication-ready figures.

The centrepiece is `pattern_dendrogram`: a T-pattern is a binary tree of
critical-interval links, and this draws it as a proper dendrogram — event types
as leaves, each internal join annotated with its critical interval [d1, d2] (the
time window within which the right side follows the left). THEME draws this as a
cramped detection tree; here it is a clean, labelled figure.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .pattern import Pattern


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
        ax.plot([cx, cx], [cd, d], color="#34495e", lw=1.4)
        ax.plot([cx, x], [d, d], color="#34495e", lw=1.4)
        _draw(child, pos, ax, ci_unit)
    # annotate the critical interval on the join
    if p.ci is not None:
        d1, d2 = p.ci
        ax.annotate(f"[{d1},{d2}]{ci_unit}", (x, d), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=7, color="#c0392b")


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
        ax.plot([i], [0], "o", color="#2980b9", ms=6)
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
    axes = axes.flatten() if n > 1 else [axes]
    for ax, p in zip(axes, comps):
        pattern_dendrogram(p, title=f"N={p.N}, level {p.level}", ci_unit=ci_unit, ax=ax)
    for ax in axes[n:]:
        ax.axis("off")
    plt.tight_layout(); plt.savefig(outfile, dpi=150); plt.close()
