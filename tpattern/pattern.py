"""
The T-pattern data structure.
=============================

A T-pattern is a **binary tree**. This mirrors how Magnusson (2000) builds
patterns: never more than two things are joined at once. Bigger patterns are
made by joining a pattern to another pattern (or single event), so the tree
grows one critical-interval relationship at a time.

    Level 0 (a "terminal"):   a single event type, e.g.  Challenge_Pressure
    Level 1:                  (A B)         two events linked by a critical interval
    Level 2:                  (A (B C))     an event linked to a level-1 pattern
    ...

Reading order is always left-to-right in time: in `(A B)`, every occurrence has
an A that is *followed by* a B within the critical interval discovered for that
link.

Occurrences
-----------
Each pattern carries a concrete list of the times it actually happened. One
occurrence is an :class:`Instance`: which observation it is in, and the
[t_start, t_end] span it covers (t_start = time of the first/left-most event,
t_end = time of the last/right-most event). The *number of occurrences* N is
simply ``len(pattern.instances)`` — this is the N reported in the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instance:
    """One realised occurrence of a pattern within one observation.

    `tokens` holds the identities of the *distinct raw event occurrences* that
    make up this instance. THEME requires every pattern occurrence to be built
    from distinct events — one event may not fill two roles — so when two
    sub-patterns are joined their token sets must be disjoint. Terminals carry a
    single token (the event's unique id).
    """

    obs: int                    # index of the observation in the sample
    start: int                  # time (ms) of the left-most event
    end: int                    # time (ms) of the right-most event
    tokens: frozenset = frozenset()


@dataclass
class Pattern:
    """A node in the T-pattern tree.

    A *terminal* has ``left is None and right is None`` and an ``event`` label.
    A *composite* has ``left`` and ``right`` sub-patterns joined by the critical
    interval ``ci = (d1, d2)`` (only meaningful for composites).
    """

    event: str | None = None                 # set only for terminals
    left: "Pattern | None" = None
    right: "Pattern | None" = None
    ci: tuple[int, int] | None = None         # (d1, d2) critical interval, ms
    p_value: float | None = None              # significance of the link
    instances: list[Instance] = field(default_factory=list)

    # ------------------------------------------------------------------ counts
    @property
    def N(self) -> int:
        """Number of occurrences across the whole sample."""
        return len(self.instances)

    @property
    def is_terminal(self) -> bool:
        return self.left is None and self.right is None

    # ----------------------------------------------------------- tree geometry
    def leaves(self) -> list[str]:
        """Event types in left-to-right (temporal) order, with repeats kept."""
        if self.is_terminal:
            return [self.event]  # type: ignore[list-item]
        return self.left.leaves() + self.right.leaves()

    @property
    def length(self) -> int:
        """Pattern length = number of terminal events (THEME 'length')."""
        return len(self.leaves())

    @property
    def level(self) -> int:
        """Hierarchical level = tree depth. Terminals are level 0."""
        if self.is_terminal:
            return 0
        return 1 + max(self.left.level, self.right.level)

    @property
    def has_loop(self) -> bool:
        """A 'loop' is a recurrence: the same event type appears twice or more.

        THEME flags these (hasloop = 1) as recycling structures — e.g. the
        interception-mediated loops that characterise saved-shot sequences.
        """
        seen = self.leaves()
        return len(set(seen)) < len(seen)

    # ------------------------------------------------------------- identity/str
    def signature(self) -> str:
        """A canonical string that uniquely identifies the tree's *shape*.

        Two patterns with the same signature are the same pattern (same events,
        same bracketing). Used to deduplicate during detection. Critical-interval
        widths are deliberately excluded so that the same structure discovered
        via slightly different intervals is treated as one pattern.
        """
        if self.is_terminal:
            return self.event  # type: ignore[return-value]
        return f"({self.left.signature()} {self.right.signature()})"

    def __str__(self) -> str:
        """Human-readable rendering, e.g.  cross → (challenge → shot_goal)."""
        if self.is_terminal:
            return self.event  # type: ignore[return-value]
        l, r = str(self.left), str(self.right)
        if not self.left.is_terminal:
            l = f"({l})"
        if not self.right.is_terminal:
            r = f"({r})"
        return f"{l} → {r}"

    __repr__ = __str__
