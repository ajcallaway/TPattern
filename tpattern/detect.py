"""
The T-pattern detection engine.
===============================

Bottom-up, level by level (Magnusson, 2000):

  Level 0  Build a "terminal" pattern for every event *type* (one leaf per type).
           These are the univariate patterns.
  Level 1  Test every ordered pair of event types (A, B) for a critical
           interval. Each accepted link becomes a bivariate pattern (A B).
  Level k  Treat every *retained* pattern as a symbol in its own right and test
           it (on either side) against every terminal for a new critical
           interval. Accepted links are one level deeper. Repeat until a level
           adds nothing new.

Three THEME options handled here:
  * Exclude Frequent Event-Types (threshold 1.50): before any linking, drop event
    types whose mean number of occurrences *per observation* exceeds the
    threshold, so they cannot act as universal connectors in multi-event
    patterns. NOTE: this affects pattern *construction* only. Univariate
    patterns (Level 0) list the full event alphabet and are reported regardless
    (the paper: "univariate counts ... are not subject to the frequent
    event-type exclusion").
  * Minimum Occurrence (3): a pattern is only kept if it occurs at least 3 times.
  * Completeness competition: a shorter pattern is discarded when it never
    occurs *outside* a longer detected pattern — i.e. all its occurrences are
    absorbed by a more complete pattern, so it carries no independent
    information. This both matches Magnusson's "completeness" pruning and keeps
    the hierarchy from proliferating redundant fragments.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .ci import find_critical_interval
from .io import Observation
from .pattern import Instance, Pattern


@dataclass
class Config:
    """Detection settings. The defaults reproduce THEME's parameters, so most users
    change only a couple of things. Every field below is user-editable; each carries
    a mathematical reason to change it and a consequence if you do — stated here and,
    for the data-driven ones, advised from your data by ``advisor.recommend``.

    Data-driven (let ``advisor.recommend(observations)`` set these, with reasons):

    * ``min_lag`` — set to 1 on frame-coded data (video timestamps), where events
      sharing a timestamp are co-occurrence, not sequence. Default 0 = THEME's
      behaviour. Impact: at 0, co-timed events read as directional sequences
      (Δt = 0 has no defined order → spurious patterns); at 1 they are reported as
      co-occurrence instead.
    * ``freq_exclude`` — mean occurrences per observation above which a type is
      barred from *building* patterns. Impact: raise/disable to keep a near-ubiquitous
      connector (risking combinatorial growth of the hierarchy); lower to exclude more
      types. The excluded type is still counted at Level 0.
    * ``min_occurrence`` — fewest times a chain must recur to be kept. Impact: below
      ~3 the occurrence test is too coarse to calibrate; raise it to drop the rare,
      near-threshold tail and shrink the multiple-comparison family.

    Documented defaults (sensible as-is; change only with a specific reason):

    * ``alpha`` — threshold on the critical-interval binomial-tail p that accepts a
      time window. Impact: lower → tighter, fewer windows; higher → more candidate
      structure. Final significance comes from ``calibrate``, so this mainly ranks
      strength, not truth.
    * ``lumping_factor`` — treat B as part of A (and drop it from further search)
      when the forward conditional prob N_AB/N_A exceeds this. Impact: set 0.7–1.0 on
      dense data to bound combinatorial blow-up; None (default) keeps every pair
      separate.
    * ``min_samples_frac`` — a pattern must occur in at least this fraction of
      observations (anti-monotone support; pruned during the search). Impact: set
      (e.g. 0.1) to require patterns be widespread rather than one-offs.
    * ``exclude_events`` — explicit include/exclude list; overrides the frequency
      rule. Impact: force-keep a central event or force-drop a nuisance one by hand;
      ``[]`` disables exclusion entirely.

    The null and the error-rate control (FDR q-target, family-wise α) are set at
    ``calibrate`` — see its docstring for their maths and impact.
    """

    alpha: float = 0.005              # Significance Level
    min_occurrence: int = 3           # Minimum Occurrence
    max_edges: int | None = None      # cap candidate CI edges (dense-data speedup)
    min_lag: int = 0                  # minimum A->B gap (ms). 0 = THEME behaviour
    #                                   (simultaneous events allowed); 1 = require
    #                                   a genuine temporal lag, so same-timestamp
    #                                   co-occurrences are excluded and handled
    #                                   separately as "simultaneity".
    freq_exclude: float | None = 1.50  # auto exclude if mean/obs exceeds this
    exclude_events: list[str] | None = None  # explicit exclusion list (overrides
    #                                          the frequency rule when provided;
    #                                          [] disables exclusion entirely)
    include_univariate: bool = True   # Univariate Patterns = Include
    completeness: bool = True         # apply completeness competition
    collapse_equivalent: bool = True  # collapse occurrence-identical patterns (the
    #   two directions of a co-timed pair, or different bracketings of one chain)
    #   to a single representative, so counts and the multiple-comparison family
    #   reflect distinct hypotheses rather than perfectly-dependent duplicates.
    lumping_factor: float | None = None  # THEME Lumping Factor. When (A B) forms
    #   with forward conditional prob N_AB/N_A > this, B is removed from the rest
    #   of the search (it almost always follows A, so the pair is treated as a
    #   unit); likewise A if N_AB/N_B exceeds it. Controls combinatorial blow-up
    #   in dense/highly-structured data. None = off (default). Typical: 0.7-1.0.
    min_samples_frac: float | None = None  # THEME "Minimum % of Samples": a pattern
    #                                        must occur in at least this fraction of
    #                                        observations. Anti-monotone (a longer
    #                                        pattern can only span fewer observations),
    #                                        so it is pruned during the search.
    max_level: int = 8                # safety cap on hierarchy depth

    def is_excluded(self, event: str, mean_per_obs: float) -> bool:
        """Decide whether an event type is barred from *building* patterns.

        Manual list (if given) takes precedence over the automatic frequency
        rule — this mirrors THEME, where the analyst can override, and lets us
        reproduce the paper's Saved analysis by keeping Interception in.
        """
        if self.exclude_events is not None:
            return event in self.exclude_events
        if self.freq_exclude is None:
            return False
        return mean_per_obs > self.freq_exclude


def _group_pair(a: Pattern, b: Pattern) -> dict[int, tuple[list, list]]:
    """Group A- and B-instances by observation id, each sub-list time-sorted."""
    idx: dict[int, tuple[list, list]] = defaultdict(lambda: ([], []))
    for inst in a.instances:
        idx[inst.obs][0].append(inst)
    for inst in b.instances:
        idx[inst.obs][1].append(inst)
    for a_list, b_list in idx.values():
        a_list.sort(key=lambda x: x.end)
        b_list.sort(key=lambda x: x.start)
    return idx


class Engine:
    """Runs a full T-pattern detection on one sample of observations."""

    def __init__(self, observations: list[Observation], config: Config | None = None):
        self.obs = observations
        self.cfg = config or Config()
        self.total_time = sum(max(o.T, 1) for o in observations)
        self.univariate: list[Pattern] = []    # all event types (for output)
        self.terminals: list[Pattern] = []      # constructable terminals only
        self.excluded: list[str] = []

    # ------------------------------------------------------------- level 0
    def build_terminals(self) -> list[Pattern]:
        """Create terminal patterns.

        `univariate` = one per distinct event type (the full alphabet, reported
        as Level-0 patterns). `terminals` = the subset usable to *build*
        multi-event patterns (survive the frequent-event exclusion and reach the
        minimum occurrence).
        """
        by_type: dict[str, list[Instance]] = defaultdict(list)
        token = 0
        for i, o in enumerate(self.obs):
            for t, ev in o.events:
                # Every raw event occurrence gets a globally-unique token id so
                # that composite patterns can never reuse the same event twice.
                by_type[ev].append(Instance(obs=i, start=t, end=t, tokens=frozenset((token,))))
                token += 1

        n_obs = len(self.obs)
        self.univariate, self.terminals, self.excluded = [], [], []
        for ev, insts in sorted(by_type.items()):
            term = Pattern(event=ev, instances=insts)
            self.univariate.append(term)
            if self.cfg.is_excluded(ev, len(insts) / n_obs):
                self.excluded.append(ev)
                continue
            if len(insts) < self.cfg.min_occurrence:
                continue
            self.terminals.append(term)
        return self.terminals

    # ------------------------------------------------------- one link test
    def _link(self, a: Pattern, b: Pattern) -> Pattern | None:
        """Test A -> B; return the composite pattern if a CI is significant."""
        res = find_critical_interval(
            a, b, _group_pair(a, b), self.total_time,
            alpha=self.cfg.alpha, min_occurrence=self.cfg.min_occurrence,
            min_lag=self.cfg.min_lag, max_edges=self.cfg.max_edges,
        )
        if res is None:
            return None
        return Pattern(
            left=a, right=b, ci=(res.d1, res.d2),
            p_value=res.p_value, instances=res.instances,
        )

    # -------------------------------------------- completeness competition
    @staticmethod
    def _covered_by(sub: Pattern, sup: Pattern) -> bool:
        """True iff `sub` is a deterministic sub-part of `sup` — exact test.

        Every occurrence carries the set of raw event tokens it is built from.
        `sub` is absorbed by `sup` iff *every* occurrence of sub is built from a
        subset of the tokens of some occurrence of sup, i.e. sub's events are
        always a subset of sup's events. Then sub never occurs independently and
        carries no information beyond sup — an exact, information-based redundancy
        criterion, not a span-overlap heuristic.

        Safety note for the frontier pruning: if sub is absorbed, then every A→B
        that forms sub is already followed (inside sup) by the rest of sup, so
        there is no free sub occurrence to extend differently — dropping it from
        the search frontier cannot lose any extension.
        """
        sup_by_obs: dict[int, list[frozenset]] = defaultdict(list)
        for ins in sup.instances:
            sup_by_obs[ins.obs].append(ins.tokens)
        for ins in sub.instances:
            toks = sup_by_obs.get(ins.obs)
            if not toks:
                return False
            st = ins.tokens
            if not any(st <= t for t in toks):
                return False
        return True

    def _completeness_competition(self, patterns: list[Pattern]) -> list[Pattern]:
        """Drop patterns whose every occurrence is absorbed by a longer one."""
        composites = [p for p in patterns if p.level >= 1]
        keep = []
        for p in composites:
            absorbed = False
            for q in composites:
                if q is p or q.length <= p.length:
                    continue
                if self._covered_by(p, q):
                    absorbed = True
                    break
            if not absorbed:
                keep.append(p)
        return keep

    # ------------------------------------------- occurrence-equivalence collapse
    @staticmethod
    def _occ_key(p: Pattern):
        """A pattern's occurrence identity: the set of (observation, event-token
        multiset) over its instances. Two composites with the same key describe the
        SAME underlying occurrences — they are the same hypothesis written
        differently (the two directions of a co-timed pair, or different bracketings
        of one chain)."""
        return frozenset((i.obs, tuple(sorted(i.tokens))) for i in p.instances)

    def _collapse_equivalent(self, patterns: list[Pattern]) -> list[Pattern]:
        """Keep one deterministic representative per occurrence-equivalence class.

        Occurrence-identical patterns are perfectly dependent: reporting or
        error-correcting over all of them inflates the pattern count and the
        multiple-comparison family without adding a distinct hypothesis. We keep the
        lexicographically smallest signature in each class (deterministic, and the
        same choice in real and surrogate data, so calibration stays consistent).
        """
        groups: dict = {}
        for p in patterns:
            groups.setdefault(self._occ_key(p), []).append(p)
        kept = [min(g, key=lambda p: p.signature()) for g in groups.values()]
        kept.sort(key=lambda p: (p.level, p.signature()))
        return kept

    # --------------------------------------------------------- full search
    def detect(self, verbose: bool = False) -> list[Pattern]:
        """Run the complete bottom-up detection and return all patterns.

        Completeness competition is applied *per level*: a newly formed pattern
        that is already absorbed by a longer pattern is not carried into the next
        round, which both matches THEME's during-construction pruning and stops
        redundant fragments (e.g. loop repeats among frequent passes) from
        seeding an ever-growing frontier.
        """
        if not self.terminals:
            self.build_terminals()

        # THEME "Minimum % of Samples": minimum number of distinct observations a
        # pattern must span. Anti-monotone, so it prunes the search frontier.
        min_bouts = 0
        if self.cfg.min_samples_frac:
            import math
            min_bouts = math.ceil(self.cfg.min_samples_frac * len(self.obs))

        # Cache each terminal's observation set for the bout co-occurrence prune.
        term_obs = {id(t): {i.obs for i in t.instances} for t in self.terminals}
        lump = self.cfg.lumping_factor
        eliminated: set[str] = set()        # terminal event names removed by lumping

        composites: list[Pattern] = []
        seen: set[str] = set()

        # MAIN LOOP — build the hierarchy one level at a time. At each level we try
        # to extend every pattern on the frontier by linking it (on either side)
        # with every terminal; surviving new patterns seed the next level. The loop
        # stops as soon as a level produces nothing new.
        frontier: list[Pattern] = list(self.terminals)  # patterns to extend
        for level in range(self.cfg.max_level):
            new: list[Pattern] = []
            for p in frontier:
                p_obs = {i.obs for i in p.instances}
                for term in self.terminals:
                    if term.event in eliminated:
                        continue
                    # A->B can only occur in observations where both occur, so if
                    # they co-occur in too few, skip the expensive CI search entirely.
                    if min_bouts and len(p_obs & term_obs[id(term)]) < min_bouts:
                        continue
                    for a, b in ((p, term), (term, p)):
                        if a is b:
                            continue
                        combo = self._link(a, b)
                        if combo is None:
                            continue
                        if min_bouts and len({i.obs for i in combo.instances}) < min_bouts:
                            continue          # too few observations; prune (anti-monotone)
                        sig = combo.signature()
                        if sig in seen:
                            continue
                        seen.add(sig)
                        new.append(combo)
                        # Lumping: if the pair is near-deterministic, drop the
                        # predictable component from the rest of the search.
                        if lump is not None:
                            if a.N and combo.N / a.N > lump and b.is_terminal:
                                eliminated.add(b.event)
                            if b.N and combo.N / b.N > lump and a.is_terminal:
                                eliminated.add(a.event)
            if not new:
                break

            composites.extend(new)
            if self.cfg.completeness:
                # Keep only new patterns that are NOT already absorbed by a
                # longer retained pattern; those seed the next level.
                retained = set(id(p) for p in self._completeness_competition(composites))
                frontier = [p for p in new if id(p) in retained]
            else:
                frontier = new
            if verbose:
                print(f"  level {level + 1}: +{len(new)} new, "
                      f"{len(frontier)} carried forward "
                      f"(maxN={max((p.N for p in new), default=0)})")
            if not frontier:
                break

        if self.cfg.completeness:
            composites = self._completeness_competition(composites)
        if self.cfg.collapse_equivalent:
            composites = self._collapse_equivalent(composites)

        result: list[Pattern] = []
        if self.cfg.include_univariate:
            result.extend(self.univariate)
        result.extend(composites)
        return result
