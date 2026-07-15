"""
Synthetic ground-truth validation.
==================================

A "nothing survives" result is only meaningful if the method is *able* to find
real patterns and *refrains* from inventing them. This module builds data where
the truth is known, so we can measure both:

* Power / sensitivity  — when we plant a genuine A->B(->C) coupling in a fraction
  of sequences, does the calibrated detector recover it, and at what strength?
* Calibration / specificity — on pure-null data (no planted coupling), does the
  family-wise error rate stay at alpha (FWER) and the false-discovery proportion
  at q (FDR)? If a method flags patterns in pure noise, it is broken.

Construction. Each sequence is a window [0, T]. Every event type has a marginal
temporal profile (where in the window it tends to fall) and a per-sequence count,
mirroring the real data's structure. Background events are placed independently
from their profiles — so there is NO cross-type coupling by construction. A
planted pattern adds, in a chosen fraction of sequences, events A, B (, C) at a
fixed inter-event lag plus jitter — a genuine, known temporal coupling. Anything
the detector reports other than the planted pattern is, by construction, a false
positive.

This is deliberately generated independently of the tpattern engine so it is a
true external test, not a tautology.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .io import Observation


@dataclass
class SyntheticSpec:
    n_seq: int = 300
    T: int = 6000                       # window length (ms)
    bg_types: int = 8                   # number of background event types
    bg_rate: float = 2.0               # mean background events per type per seq
    # planted pattern: sequence of (label, lag_ms_from_previous)
    planted: list = field(default_factory=lambda: [("A", 0), ("B", 1500)])
    plant_fraction: float = 0.15        # fraction of sequences carrying it
    jitter: int = 200                   # +/- ms jitter on planted lags
    seed: int = 7


def _profile_time(rng, T, kind):
    """Draw a within-window time for a background event given a profile kind."""
    if kind == "early":
        u = rng.beta(2, 5)
    elif kind == "late":
        u = rng.beta(5, 2)
    else:
        u = rng.random()
    return int(u * T)


def make_dataset(spec: SyntheticSpec):
    """Return (observations, truth_signature) for one synthetic spec."""
    rng = np.random.default_rng(spec.seed)
    kinds = ["early", "mid", "late"]
    type_kind = {f"bg{i}": kinds[i % 3] for i in range(spec.bg_types)}

    obs = []
    n_plant = int(round(spec.n_seq * spec.plant_fraction))
    plant_flags = np.array([i < n_plant for i in range(spec.n_seq)])
    rng.shuffle(plant_flags)

    for s in range(spec.n_seq):
        events = []
        # background: each type gets Poisson(bg_rate) events from its profile
        for ev, kind in type_kind.items():
            c = rng.poisson(spec.bg_rate)
            for _ in range(c):
                events.append((_profile_time(rng, spec.T, kind), ev))
        # planted coupling in a fraction of sequences
        if plant_flags[s]:
            anchor = int(rng.uniform(0.1, 0.6) * spec.T)
            t = anchor
            for lbl, lag in spec.planted:
                t = t + lag + int(rng.integers(-spec.jitter, spec.jitter + 1))
                events.append((max(0, min(spec.T, t)), lbl))
        events.sort()
        obs.append(Observation(name=f"syn{s}", start=0, end=spec.T, events=events))

    truth = "(" * (len(spec.planted) - 1)
    # build the expected signature the same way Pattern.signature would (left-assoc)
    labels = [lbl for lbl, _ in spec.planted]
    sig = labels[0]
    for lbl in labels[1:]:
        sig = f"({sig} {lbl})"
    return obs, sig
