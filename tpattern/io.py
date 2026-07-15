"""
Reading THEME observation files.
================================

THEME stores each observation (here: one shot-ending possession sequence) as a
plain tab-separated text file:

    time    event
    1       :                       <- window START marker
    2       Pass_Complete_NoPressure
    1303    Shot_Goal_Pressure
    1304    &                       <- window END marker

* `time` is an integer clock in milliseconds.
* `:`  marks the beginning of the observation window.
* `&`  marks the end of the observation window.
* Every other row is a real *event occurrence*: a point in time at which an
  event of a given *type* happened.

Several events may share a timestamp (simultaneous events). We keep them; the
detection engine treats co-occurring events as an unordered set at that instant.

A T-pattern analysis is run over a *collection* of these files (a "sample").
Patterns are counted across all observations, but a single pattern occurrence
can never straddle two observations — each file is an independent time-line.
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
               end: str | None = None, build_event_from: list[str] | None = None,
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
    build_event_from : list[str], optional
        If given, the event code is built by joining these columns with '_'
        (for coders who keep the code split across descriptor columns) instead of
        reading `event` directly.
    time_unit : {'s', 'ms'}
        Unit of the time columns. Internally times are integer milliseconds, so
        seconds are scaled by 1000 (the engine's baseline maths is unit-agnostic;
        this only fixes the reported interval unit).
    """
    path = Path(path)
    scale = 1000 if time_unit == "s" else 1
    rows_by_obs: dict[str, list] = defaultdict(list)
    ends_by_obs: dict[str, list] = defaultdict(list)

    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        missing = {observation, start} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"table missing required column(s): {sorted(missing)}")
        for r in reader:
            obs_id = (r.get(observation) or "").strip()
            if not obs_id:
                continue
            if build_event_from:
                code = "_".join((r.get(c) or "").strip() for c in build_event_from)
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

    sample: list[Observation] = []
    for obs_id, evs in rows_by_obs.items():
        evs.sort(key=lambda e: e[0])
        o_start = evs[0][0]
        o_end = max(ends_by_obs[obs_id]) if ends_by_obs.get(obs_id) else evs[-1][0]
        sample.append(Observation(name=obs_id, start=o_start, end=o_end, events=evs))
    return sample
