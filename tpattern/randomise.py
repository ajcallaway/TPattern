"""
Randomisation null — the Type-I-error control THEME can't easily give you.
==========================================================================

The analytic critical-interval test assumes that, under the null, the second
event is scattered independently and uniformly. Real event streams violate that
(events cluster, densities vary within a possession). So a pattern can clear the
analytic 0.005 bar and still be an artefact of that clustering rather than a
genuine temporal relationship.

The fix is an *empirical* null: destroy the real cross-event timing while keeping
each event type's own frequency and internal spacing, re-run the entire
detection, and see which patterns still show up. A pattern that keeps appearing
in randomised data — where by construction there is no genuine structure — is not
trustworthy. This is exactly what makes the result defensible to a sceptical
reviewer, and it is the honest way to decide which borderline patterns to keep.

Two surrogate schemes (THEME's "Shuffling and Rotation"), 10 runs each:

* Rotation  — within each observation, cyclically shift every event type's
              time-line by its own random offset (mod window length). This keeps
              each type's count and internal inter-event spacing intact but
              scrambles the *relative* timing between types. It is the stricter,
              more structure-preserving null.
* Shuffling — within each observation, keep the set of event *times* but randomly
              permute which event *type* sits at each time. This preserves the
              overall event density and timing but destroys type-specific
              temporal relationships.

For each real pattern we report an empirical p-value: the fraction of surrogate
runs in which the *same* pattern (identical signature) recurs with an occurrence
count at least as high as observed. Empirical p = 0 means the pattern never
arose by chance in any surrogate.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from .detect import Config, Engine
from .io import Observation
from .pattern import Pattern


def rotate(obs: Observation, rng: random.Random) -> Observation:
    """Rotation surrogate for one observation (per-type cyclic time shift)."""
    T = max(obs.T, 1)
    by_type: dict[str, list[int]] = defaultdict(list)
    for t, ev in obs.events:
        by_type[ev].append(t)
    new_events: list[tuple[int, str]] = []
    for ev, times in by_type.items():
        offset = rng.randrange(T)
        for t in times:
            nt = obs.start + ((t - obs.start + offset) % T)
            new_events.append((nt, ev))
    new_events.sort()
    return Observation(name=obs.name, start=obs.start, end=obs.end, events=new_events)


def shuffle(obs: Observation, rng: random.Random) -> Observation:
    """Shuffling surrogate for one observation (permute type labels over times)."""
    times = [t for t, _ in obs.events]
    types = [ev for _, ev in obs.events]
    rng.shuffle(types)
    new_events = sorted(zip(times, types))
    return Observation(name=obs.name, start=obs.start, end=obs.end, events=new_events)


def build_profiles(observations) -> dict:
    """Pooled within-sequence position (u = (t-start)/T) for each event type.

    This is each type's empirical *marginal temporal intensity* — where in a
    sequence it tends to occur (shots late ~0.9, passes early ~0.3). It is the
    structure the profile-preserving null keeps.
    """
    import numpy as np
    pos: dict[str, list[float]] = defaultdict(list)
    for o in observations:
        span = max(o.end - o.start, 1)
        for t, ev in o.events:
            # clamp to [0, 1] so a surrogate can never be placed outside the
            # observation window even if an event's time falls on/just past a border.
            pos[ev].append(min(1.0, max(0.0, (t - o.start) / span)))
    return {ev: np.asarray(v) for ev, v in pos.items()}


def profile_surrogate(observations, profiles, rng) -> list:
    """Profile-preserving surrogate (null N2).

    For each observation and each event type, redraw that type's event times from
    its *own* pooled marginal position profile (with replacement), keeping the
    per-observation count. This preserves (i) each type's count per sequence and
    (ii) each type's marginal temporal profile, while destroying any *cross-type*
    temporal coupling. Significance against this null therefore isolates genuine
    coordination between event types — beyond the fact that each type has its own
    characteristic timing.

    `rng` is a numpy Generator (fast vectorised sampling).
    """
    out = []
    for o in observations:
        span = max(o.end - o.start, 1)
        counts: dict[str, int] = defaultdict(int)
        for _, ev in o.events:
            counts[ev] += 1
        events: list[tuple[int, str]] = []
        for ev, c in counts.items():
            us = rng.choice(profiles[ev], size=c, replace=True)
            for u in us:
                events.append((int(round(o.start + float(u) * span)), ev))
        events.sort()
        out.append(Observation(name=o.name, start=o.start, end=o.end, events=events))
    return out


def randomise_sample(observations, method: str, rng: random.Random):
    fn = rotate if method == "rotation" else shuffle
    return [fn(o, rng) for o in observations]


@dataclass
class NullResult:
    """Summary of the randomisation null for one detection."""

    real: list[Pattern]                       # patterns detected in real data
    runs: dict[str, list[list[Pattern]]]      # method -> list of per-run pattern lists
    empirical_p: dict[str, float]             # real-pattern signature -> empirical p
    n_runs_total: int

    def level_counts(self):
        """Mean number of composite patterns per level: real vs surrogate."""
        def by_level(pats):
            c = defaultdict(int)
            for p in pats:
                if p.level >= 1:
                    c[p.level] += 1
            return c

        real_c = by_level(self.real)
        rand_lists = [p for runs in self.runs.values() for p in runs]
        rand_c = defaultdict(list)
        for pats in rand_lists:
            c = by_level(pats)
            lv = set(c) | set(real_c)
            for k in lv:
                rand_c[k].append(c.get(k, 0))
        levels = sorted(set(real_c) | set(rand_c))
        return [
            (lv, real_c.get(lv, 0),
             sum(rand_c.get(lv, [])) / max(len(rand_c.get(lv, [])), 1))
            for lv in levels
        ]

    def survivors(self, threshold: float = 0.0) -> list[Pattern]:
        """Real composite patterns with empirical p <= threshold.

        threshold = 0.0 keeps only patterns that never recurred in any surrogate
        at equal-or-greater strength — the strictest, cleanest filter given a
        finite number of runs.
        """
        return [p for p in self.real
                if p.level >= 1 and self.empirical_p.get(p.signature(), 1.0) <= threshold]


def run_null(observations, config: Config | None = None,
             n_runs: int = 10, seed: int = 12345) -> NullResult:
    """Detect on real data, then on 10 rotation + 10 shuffling surrogates."""
    config = config or Config()

    real = Engine(observations, config).detect()
    real_index: dict[str, int] = {}
    for p in real:
        if p.level >= 1:
            real_index[p.signature()] = p.N

    runs: dict[str, list[list[Pattern]]] = {"rotation": [], "shuffling": []}
    # count, per real signature, how many surrogate runs match-or-beat it
    beat: dict[str, int] = defaultdict(int)

    # fixed per-method offset — NOT hash(method), whose value is salted per Python
    # process (PYTHONHASHSEED), which would make identical `seed` arguments produce
    # different surrogates across runs despite the reproducibility the signature promises.
    method_offset = {"rotation": 0, "shuffling": 1}
    for method in ("rotation", "shuffling"):
        for r in range(n_runs):
            rng = random.Random((method_offset[method] * 2246822519
                                 ^ (r * 2654435761) ^ seed) & 0xFFFFFFFF)
            surrogate = randomise_sample(observations, method, rng)
            pats = Engine(surrogate, config).detect()
            runs[method].append(pats)
            rand_best: dict[str, int] = {}
            for p in pats:
                if p.level >= 1:
                    sig = p.signature()
                    if p.N > rand_best.get(sig, 0):
                        rand_best[sig] = p.N
            for sig, n_real in real_index.items():
                if rand_best.get(sig, 0) >= n_real:
                    beat[sig] += 1

    total = n_runs * 2
    empirical_p = {sig: beat.get(sig, 0) / total for sig in real_index}
    return NullResult(real=real, runs=runs, empirical_p=empirical_p, n_runs_total=total)
