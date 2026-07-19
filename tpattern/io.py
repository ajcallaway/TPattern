"""
Reading event data into a sample of observations.
==================================================

The primary entry point is :func:`read_table`, which reads the canonical flat CSV
that any coding tool can export (one row per event: ``observation, event, start``;
see SCHEMA.md). This is what almost all users want::

    from tpattern import read_table
    obs = read_table("events.csv")

A T-pattern analysis runs over a *collection* of observations (a "sample"). Each
observation is one independent time-line (a possession, rally, bout, match);
patterns are counted across all observations, but a single pattern occurrence can
never straddle two of them. Several events may share a timestamp — the detection
engine treats co-timed events as an unordered set at that instant (see
``Config.min_lag`` to require a genuine lag instead).

:func:`read_sample` / :func:`read_observation` are a legacy reader for THEME's
tab-separated observation files, kept for compatibility: one file per observation,
``time<TAB>event`` rows, with ``:`` and ``&`` marking the observation window.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


# The two reserved symbols that delimit the observation window rather than
# denoting a real event.
START_MARKER = ":"
END_MARKER = "&"


@dataclass
class Observation:
    """One time-line: the events of a single observation file.

    Attributes
    ----------
    name : str
        File stem, used to trace patterns back to a specific shot/sequence.
    start, end : int
        The observation window [start, end] in milliseconds, taken from the
        `:` and `&` markers. `T = end - start` is the window length used as the
        denominator of the NX/T baseline probability.
    events : list[tuple[int, str]]
        (time, event_type) pairs, sorted by time, markers removed.
    """

    name: str
    start: int
    end: int
    events: list[tuple[int, str]] = field(default_factory=list)

    @property
    def T(self) -> int:
        """Length of the observation window in time units (ms)."""
        return self.end - self.start


def read_observation(path: str | Path) -> Observation:
    """Parse a single THEME `.txt` file into an :class:`Observation`."""
    path = Path(path)
    start: int | None = None
    end: int | None = None
    events: list[tuple[int, str]] = []

    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            # Tolerate whitespace-separated files as well.
            parts = raw.split()
            if len(parts) != 2:
                continue
        tok_time, tok_event = parts[0].strip(), parts[1].strip()
        if tok_time.lower() == "time":  # header row
            continue
        try:
            t = int(tok_time)
        except ValueError:
            continue

        if tok_event == START_MARKER:
            start = t
        elif tok_event == END_MARKER:
            end = t
        else:
            events.append((t, tok_event))

    events.sort(key=lambda e: e[0])

    # Fall back gracefully if a marker is missing: use the event span.
    if start is None:
        start = events[0][0] if events else 0
    if end is None:
        end = events[-1][0] if events else start

    return Observation(name=path.stem, start=start, end=end, events=events)


def read_sample(folder: str | Path, pattern: str = "*.txt") -> list[Observation]:
    """Read every observation file in a folder into a list (a "sample")."""
    folder = Path(folder)
    files = sorted(folder.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} in {folder}")
    return [read_observation(f) for f in files]


def read_table(path: str | Path, *, observation: str = "observation",
               event: str = "event", start: str = "start",
               end: str | None = None, obs_start: str | None = None,
               obs_end: str | None = None, build_event_from: list[str] | None = None,
               time_unit: str = "s", sep: str = ",") -> list[Observation]:
    """Read the canonical flat event table (see SCHEMA.md) into a sample.

    One row per event; rows are grouped by the `observation` column into one
    :class:`Observation` each. This is the software-agnostic entry point — any
    tool (OpenTag, Sportscode, a spreadsheet) exports to these columns and the
    rest of the library is unchanged.

    Parameters
    ----------
    observation, event, start : str
        Column names for the required fields.
    end : str, optional
        Column giving each event's end time; if absent the observation window is
        taken from the min/max event `start`.
    obs_start, obs_end : str, optional
        Columns giving the *observation window* (constant within an observation).
        Supply these when the unit has real bounds that extend beyond its first and
        last event — a possession, rally or bout usually does. The window length
        T = obs_end - obs_start is the denominator of the NX/T baseline, so deriving
        it from the events instead will shift every baseline probability. If absent,
        the window falls back to the first/last event time.
    build_event_from : list[str], optional
        If given, the event code is built by joining these columns with '_'
        (for coders who keep the code split across descriptor columns) instead of
        reading `event` directly.
    time_unit : {'s', 'ms'}
        Unit of the time columns. Internally times are integer milliseconds, so
        seconds are scaled by 1000 (the engine's baseline maths is unit-agnostic;
        this only fixes the reported interval unit).
    """
    if time_unit not in ("s", "ms"):
        raise ValueError(f"time_unit must be 's' or 'ms', got {time_unit!r}")
    path = Path(path)
    scale = 1000 if time_unit == "s" else 1
    rows_by_obs: dict[str, list] = defaultdict(list)
    ends_by_obs: dict[str, list] = defaultdict(list)
    window_by_obs: dict[str, tuple] = {}

    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        cols = set(reader.fieldnames or [])
        # the event code comes from `event`, unless it is built from other columns
        code_cols = set(build_event_from) if build_event_from else {event}
        required = {observation, start} | code_cols
        missing = required - cols
        if missing:
            raise ValueError(
                f"table {path.name} is missing required column(s) {sorted(missing)}. "
                f"Found columns: {sorted(cols)}. Expected one row per event with at "
                f"least '{observation}', '{event}' and '{start}' (rename via the "
                f"read_table arguments if your export uses different names; see SCHEMA.md).")
        for r in reader:
            obs_id = (r.get(observation) or "").strip()
            if not obs_id:
                continue
            if build_event_from:
                # join only the non-empty parts, so an event with no value for one
                # column (e.g. a Challenge with no outcome) yields "Challenge_Pressure",
                # not "Challenge__Pressure", and one with none yields just its type.
                parts = [(r.get(c) or "").strip() for c in build_event_from]
                code = "_".join(p for p in parts if p)
            else:
                code = (r.get(event) or "").strip()
            if not code:
                continue
            try:
                t = int(round(float(r[start]) * scale))
            except (ValueError, TypeError, KeyError):
                continue
            rows_by_obs[obs_id].append((t, code))
            if end and r.get(end) not in (None, ""):
                try:
                    ends_by_obs[obs_id].append(int(round(float(r[end]) * scale)))
                except ValueError:
                    pass
            if obs_start and obs_end and obs_id not in window_by_obs:
                try:
                    window_by_obs[obs_id] = (
                        int(round(float(r[obs_start]) * scale)),
                        int(round(float(r[obs_end]) * scale)))
                except (ValueError, TypeError, KeyError):
                    pass

    sample: list[Observation] = []
    for obs_id, evs in rows_by_obs.items():
        evs.sort(key=lambda e: e[0])
        if obs_id in window_by_obs:
            o_start, o_end = window_by_obs[obs_id]
        else:
            o_start = evs[0][0]
            o_end = max(ends_by_obs[obs_id]) if ends_by_obs.get(obs_id) else evs[-1][0]
        sample.append(Observation(name=obs_id, start=o_start, end=o_end, events=evs))
    return sample
