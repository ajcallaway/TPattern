"""
Reading your event data in.
===========================

Almost everyone wants one function: :func:`read_table`. Give it a plain table with
one row per event, and it returns the list of *observations* the rest of the
library analyses::

    from tpattern import read_table
    observations = read_table("my_events.csv")

Your table needs three columns — an **observation** id (which session/rally/bout/
possession the event belongs to), an **event** label (what happened), and a
**start** time (when). Anything else is optional (see SCHEMA.md).

An *observation* is one self-contained time-line: a single possession, rally, bout
or match. Patterns are counted across all of your observations, but one occurrence
of a pattern can never span two of them — so getting the observation column right
matters. Several events may share the same time; the engine treats same-time events
as an unordered set at that instant (use ``Config.min_lag`` to require a real gap
instead).

**Reading your own, un-cleaned data.** Real exports are messy. Rather than fail on
the first bad row or, worse, drop rows silently, :func:`read_table` runs a set of
checks and tells you — in plain language — what it found, how much of your file was
affected, and what to do about it. Each check has a short code (``E01``, ``W05`` …)
explained in the tutorial's Appendix A and in :data:`CHECKS`. A code beginning
``E`` stops the read (something must be fixed first); ``W`` and ``I`` never stop it
— the data loads and the notes are there if you want to tidy up.

:func:`read_sample` / :func:`read_observation` are an older reader for THEME's
tab-separated files (one file per observation, ``time<TAB>event`` rows, with ``:``
and ``&`` marking the window). :func:`read_sofcoder` reads SOF-CODER/THEME
``DATANAME, T, Events`` files.
"""

from __future__ import annotations

import csv
import difflib
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path


# The two reserved symbols that mark the observation window rather than a real
# event, in the older THEME/SOF-CODER file formats.
START_MARKER = ":"
END_MARKER = "&"


@dataclass
class Observation:
    """One time-line: all the events of a single observation.

    Attributes
    ----------
    name : str
        Which observation this is (its id), so a pattern can be traced back to a
        specific session/rally/bout.
    start, end : int
        The observation window [start, end] in milliseconds. ``T = end - start`` is
        the length of the window, used as the denominator of the NX/T baseline (how
        likely an event is to fall in a given slice of time by chance).
    events : list[tuple[int, str]]
        (time, event label) pairs, sorted by time, with any window markers removed.
    """

    name: str
    start: int
    end: int
    events: list[tuple[int, str]] = field(default_factory=list)

    @property
    def T(self) -> int:
        """Length of the observation window, in time units (ms)."""
        return self.end - self.start


# ---------------------------------------------------------------------------
# Data checks: the codes, and the human-readable report.
# ---------------------------------------------------------------------------

class DataFormatError(ValueError):
    """Raised when a file cannot be read as it stands (an ``E`` check).

    The message *is* the plain-language report: what is wrong, and how to fix it.
    ``W`` and ``I`` checks never raise — they are reported and the data still loads.
    """


# The single source of truth for every check. The runtime report and the tutorial's
# Appendix A are both built from this, so they can never drift apart. `severity`:
# 'E' stops the read (must fix first), 'W' is a warning (loads anyway, worth tidying),
# 'I' is information (loads anyway, nothing to fix). `condition` says when it fires;
# `fix` says what to do; `example` shows it concretely (a code snippet, or a data
# before -> after). Runtime adds the specifics (counts, percentages, example rows).
CHECKS: dict[str, dict[str, str]] = {
    "E01": {"severity": "E", "condition": "A column the analysis needs is not in the file.",
            "fix": "Rename the column, or tell read_table its name.",
            "example": "read_table(\"events.csv\", start=\"Start Time\")"},
    "E02": {"severity": "E", "condition": "The file read as a single column, so it is probably not comma-separated.",
            "fix": "Re-save it as a comma-separated CSV, or pass the separator.",
            "example": "read_table(\"events.csv\", sep=\";\")"},
    "E03": {"severity": "E", "condition": "The file has a header row but no data under it (or is empty).",
            "fix": "Check the export actually contains events, then re-run.",
            "example": "a data row looks like: p1,pass,0"},
    "E04": {"severity": "E", "condition": "Every row was unusable, so there was nothing to load.",
            "fix": "Open the file and check the observation, event and start columns are filled in.",
            "example": "p1,pass,0 (a value in observation, event and start)"},
    "E05": {"severity": "E", "condition": "No observation has at least two events, so no pattern can form.",
            "fix": "Check the observation column groups events correctly; a pattern needs two or more events in the same observation.",
            "example": "two rows sharing an id: p1,pass,0 and p1,shot,3"},
    "W10": {"severity": "W", "condition": "Some start times are not numbers, so those rows were left out.",
            "fix": "Times must be numbers. If yours is a mm:ss clock, convert it to seconds first.",
            "example": "01:23 -> 83"},
    "W11": {"severity": "W", "condition": "Some rows have a blank observation id and were left out.",
            "fix": "Fill in the observation column, or remove the empty rows.",
            "example": ",pass,0 -> p1,pass,0"},
    "W12": {"severity": "W", "condition": "Some rows have a blank event label and were left out.",
            "fix": "Fill in the event column, or remove the empty rows.",
            "example": "p1,,0 -> p1,pass,0"},
    "W13": {"severity": "W", "condition": "Two or more event labels differ only by capitalisation or spacing.",
            "fix": "They are counted as different events. Merge them if they mean the same thing.",
            "example": "Pass and pass -> both Pass"},
    "W14": {"severity": "W", "condition": "Some events fall outside their observation's window, or a window has end at or before start.",
            "fix": "Check the obs_start / obs_end columns; the window should contain all of the observation's events.",
            "example": "event at 620 with window 0-600 -> set obs_end >= 620"},
    "W15": {"severity": "W", "condition": "The time values look like they might be in the other unit.",
            "fix": "Check time_unit: pass \"s\" for seconds or \"ms\" for milliseconds.",
            "example": "read_table(\"events.csv\", time_unit=\"s\")"},
    "I20": {"severity": "I", "condition": "Some observations have fewer than two events.",
            "fix": "None needed. They set the baseline event rates but cannot themselves contain a pattern; the Methods text reports both counts.",
            "example": "Methods reports \"163 observations, 131 with >=2 events\""},
    "I21": {"severity": "I", "condition": "The file contains only one observation.",
            "fix": "None needed, but check it is intended: patterns are counted across observations, so a single time-line will detect little.",
            "example": "is the observation column accidentally a constant?"},
    "I22": {"severity": "I", "condition": "One event type makes up a large share of all events.",
            "fix": "None needed. A very common event can link to almost everything; the advisor may suggest setting it aside from pattern-building.",
            "example": "exclude_events=[\"Interception\"]"},
    "I23": {"severity": "I", "condition": "A high fraction of neighbouring events share an identical time.",
            "fix": "None needed. The advisor will likely suggest requiring a genuine gap so co-timed events are read as co-occurrence, not sequence.",
            "example": "Config(min_lag=1)"},
    "I24": {"severity": "I", "condition": "Some rows are exact duplicates (same observation, event and time).",
            "fix": "None needed by default: identical same-time events are counted once. If they are double entries and you turned that collapsing off, remove the copies.",
            "example": "keep collapse_duplicates on (the default)"},
}


@dataclass
class _Finding:
    """One thing a check turned up, with the specifics filled in at runtime."""
    code: str
    detail: str            # the specifics: counts, percentages, an example

    @property
    def severity(self) -> str:
        return CHECKS[self.code]["severity"]

    @property
    def fix(self) -> str:
        return CHECKS[self.code]["fix"]

    @property
    def example(self) -> str:
        return CHECKS[self.code].get("example", "")


class CheckReport:
    """Collects findings for one file and renders the plain-language report.

    Access ``.findings`` for the raw list, ``.errors`` for the blocking ones, and
    ``str(report)`` for the human-readable text. ``read_table`` attaches the report
    to what it prints; a blocking finding is raised as :class:`DataFormatError`.
    """

    def __init__(self, filename: str, rows_read: int):
        self.filename = filename
        self.rows_read = rows_read          # data rows (header excluded)
        self.rows_used = rows_read
        self.n_observations = 0
        self.findings: list[_Finding] = []

    def add(self, code: str, detail: str) -> None:
        self.findings.append(_Finding(code, detail))

    @property
    def errors(self) -> list[_Finding]:
        return [f for f in self.findings if f.severity == "E"]

    def _pct(self, n: int) -> str:
        base = self.rows_read or 1
        return f"{n} ({n / base:.1%} of {self.rows_read})"

    def render(self) -> str:
        lines: list[str] = []
        if self.errors:
            lines.append(f"Data check — {self.filename}   ✗ couldn't load the file")
            lines.append("Nothing was loaded yet. Fix and re-run:")
            for f in self.errors:
                lines.append(f"  • {f.detail} ({f.code})")
                eg = f"  e.g. {f.example}" if f.example else ""
                lines.append(f"      → {f.fix}{eg}")
            return "\n".join(lines)

        # Loaded successfully; W/I notes are optional.
        lines.append(f"Data check — {self.filename}   ✓ loaded")
        if self.rows_used < self.rows_read:
            left = self.rows_read - self.rows_used
            lines.append(f"  Loaded {self.rows_used} of {self.rows_read} rows "
                         f"({left} left out, {left / (self.rows_read or 1):.1%}) "
                         f"across {self.n_observations} observations.")
        else:
            lines.append(f"  Loaded all {self.rows_used} rows across "
                         f"{self.n_observations} observations.")
        notes = [f for f in self.findings if f.severity in ("W", "I")]
        if notes:
            lines.append("  Your data is ready. The notes below are optional — "
                         "nothing here stopped the load:")
            for f in notes:
                lines.append(f"    • {f.detail} ({f.code})")
                if f.severity == "W":
                    eg = f"  e.g. {f.example}" if f.example else ""
                    lines.append(f"        → {f.fix}{eg}")
        else:
            lines.append("  Your data is ready. No issues found.")
        return "\n".join(lines)

    def __str__(self) -> str:      # so print(report) just works
        return self.render()


def _closest_column(wanted: str, available) -> str | None:
    """Best guess at which real column a missing required one was meant to be."""
    hit = difflib.get_close_matches(wanted, list(available), n=1, cutoff=0.6)
    if hit:
        return hit[0]
    low = {c.lower(): c for c in available}
    return low.get(wanted.lower())


def _norm_label(code: str) -> str:
    """Fold a label to compare look-alikes: lower-case, single-spaced, trimmed."""
    return " ".join(code.lower().split())


def _example_rows(rows: list[int]) -> str:
    """Render a couple of example row numbers for a message."""
    shown = ", ".join(f"row {r}" for r in rows[:2])
    return shown


def read_table(path: str | Path, *, observation: str = "observation",
               event: str = "event", start: str = "start",
               end: str | None = "end", obs_start: str | None = "obs_start",
               obs_end: str | None = "obs_end", build_event_from: list[str] | None = None,
               time_unit: str = "s", sep: str = ",",
               check: bool = True, report: bool = True) -> list[Observation]:
    """Read a plain event table (one row per event) into a list of observations.

    This is the software-agnostic way in: any tool — OpenTag, SportsCode, a
    spreadsheet — can export these columns, and the rest of the library is the same
    whatever produced them. Rows are grouped by the ``observation`` column into one
    :class:`Observation` each.

    Parameters
    ----------
    observation, event, start : str
        The names of the three required columns in *your* file. If your export uses
        different names, pass them here (e.g. ``start="Start Time"``).
    end : str, optional
        A column giving each event's end time. If it is absent the observation
        window is taken from the earliest and latest event.
    obs_start, obs_end : str, optional
        Columns giving the observation *window* (the same value for every row of an
        observation). These default to the usual names, so a file that includes them
        is read correctly with no extra arguments, and a file without them simply
        falls back to the first and last event. Give a window when the observation
        has real bounds beyond its first and last event — a possession or rally
        usually does. The window length ``T = obs_end - obs_start`` is the
        denominator of the NX/T baseline, so taking it from the events instead shifts
        every baseline probability.
    build_event_from : list[str], optional
        Build the event label by joining these columns with '_', for data that keeps
        the label split across descriptor columns, instead of reading ``event``.
    time_unit : {'s', 'ms'}
        The unit of your time columns. Times are held internally as whole
        milliseconds, so seconds are multiplied by 1000.
    check : bool
        Run the data checks (default on). See :data:`CHECKS` and Appendix A.
    report : bool
        Print the plain-language report when a check finds something (default on).
        A clean file prints nothing. Blocking (``E``) problems are always raised as
        :class:`DataFormatError` whatever this is set to.

    Raises
    ------
    DataFormatError
        If the file cannot be read as it stands (any ``E`` check).
    """
    if time_unit not in ("s", "ms"):
        raise ValueError(f"time_unit must be 's' or 'ms', got {time_unit!r}")
    path = Path(path)
    scale = 1000 if time_unit == "s" else 1

    # utf-8-sig quietly strips the byte-order mark Excel puts on the first column
    # name, which would otherwise make the observation column look "missing".
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    rep = CheckReport(path.name, rows_read=len(rows))
    cols = set(fieldnames)

    def finish_or_raise():
        """Emit the report and, if anything blocks, raise it.

        A blocking (E) finding is always raised. Otherwise the plain-language report
        is printed only when there is something the user should act on — any warning
        (W) — so a clean file, or one with information-only notes, stays quiet.
        Pass ``report="all"`` to print the report whenever there is any note at all
        (what the guided notebook does, to surface the information notes too).
        """
        if check and rep.errors:
            raise DataFormatError("\n" + rep.render())
        if not (check and report) or not rep.findings:
            return
        if report == "all" or any(f.severity == "W" for f in rep.findings):
            print(rep.render())

    # --- E02: the whole file read as one column => wrong separator ---
    if check and len(fieldnames) == 1 and (";" in fieldnames[0] or "\t" in fieldnames[0]):
        guess = ";" if ";" in fieldnames[0] else "a tab"
        rep.add("E02", f"the file read as a single column ({fieldnames[0]!r}); it "
                       f"looks separated by {guess}, not commas")
        finish_or_raise()

    # --- E01: required columns present? (with a best-guess suggestion) ---
    code_cols = set(build_event_from) if build_event_from else {event}
    required = {observation: observation, start: start}
    required.update({c: c for c in code_cols})
    missing = [c for c in required if c not in cols]
    if check and missing:
        for c in missing:
            guess = _closest_column(c, cols)
            hint = f"; your file has {guess!r} — did you mean that?" if guess else ""
            rep.add("E01", f"no column called {c!r}. Columns found: "
                           f"{sorted(cols)}{hint}")
        finish_or_raise()

    # --- E03: header but no data ---
    if check and not rows:
        rep.add("E03", "the file has a header row but no events under it")
        finish_or_raise()

    # --- parse rows, recording (not hiding) anything we cannot use ---
    rows_by_obs: dict[str, list] = defaultdict(list)
    ends_by_obs: dict[str, list] = defaultdict(list)
    window_by_obs: dict[str, tuple] = {}
    seen_rows: set = set()

    blank_obs: list[int] = []
    blank_event: list[int] = []
    bad_time: list[int] = []
    bad_time_examples: list[str] = []
    dup_rows: list[int] = []
    used = 0

    for i, r in enumerate(rows, start=2):        # row 1 is the header, so data starts at 2
        obs_id = (r.get(observation) or "").strip()
        if not obs_id:
            blank_obs.append(i)
            continue
        if build_event_from:
            parts = [(r.get(c) or "").strip() for c in build_event_from]
            code = "_".join(p for p in parts if p)
        else:
            code = (r.get(event) or "").strip()
        if not code:
            blank_event.append(i)
            continue
        try:
            t = int(round(float(r[start]) * scale))
        except (ValueError, TypeError, KeyError):
            bad_time.append(i)
            if len(bad_time_examples) < 2:
                bad_time_examples.append(f"row {i} '{str(r.get(start))[:20]}'")
            continue

        key = (obs_id, code, t)
        if key in seen_rows:
            dup_rows.append(i)
        seen_rows.add(key)

        rows_by_obs[obs_id].append((t, code))
        used += 1
        if end and r.get(end) not in (None, ""):
            try:
                ends_by_obs[obs_id].append(int(round(float(r[end]) * scale)))
            except ValueError:
                pass
        if obs_start and obs_end and obs_id not in window_by_obs:
            try:
                window_by_obs[obs_id] = (int(round(float(r[obs_start]) * scale)),
                                         int(round(float(r[obs_end]) * scale)))
            except (ValueError, TypeError, KeyError):
                pass

    rep.rows_used = used

    # --- build the observations (identical to the clean-data path) ---
    sample: list[Observation] = []
    bad_window = 0
    out_of_window = 0
    for obs_id, evs in rows_by_obs.items():
        evs.sort(key=lambda e: e[0])
        if obs_id in window_by_obs:
            o_start, o_end = window_by_obs[obs_id]
        else:
            o_start = evs[0][0]
            o_end = max(ends_by_obs[obs_id]) if ends_by_obs.get(obs_id) else evs[-1][0]
        if o_end < o_start:            # inverted window (a zero-length one is fine)
            bad_window += 1
        else:
            out_of_window += sum(1 for t, _ in evs if t < o_start or t > o_end)
        sample.append(Observation(name=obs_id, start=o_start, end=o_end, events=evs))
    rep.n_observations = len(sample)

    # --- checks that need the parsed data ------------------------------------
    if check:
        # E04 / E05: nothing usable, or nothing that can host a pattern
        if not sample:
            reasons = []
            if blank_obs:
                reasons.append(f"{len(blank_obs)} had a blank {observation}")
            if blank_event:
                reasons.append(f"{len(blank_event)} had a blank {event}")
            if bad_time:
                reasons.append(f"{len(bad_time)} had a start time that isn't a number")
            why = "; ".join(reasons) if reasons else "no rows had all three of "\
                  f"{observation}, {event} and {start}"
            rep.add("E04", f"every row was left out ({why})")
            finish_or_raise()
        elif not any(len(o.events) >= 2 for o in sample):
            rep.add("E05", "no observation contains two or more events, so no "
                           "pattern can form")
            finish_or_raise()

        # W10-W12: rows left out
        if bad_time:
            eg = "; ".join(bad_time_examples)
            hint = " — if that's a mm:ss clock, convert it to seconds" if bad_time_examples else ""
            rep.add("W10", f"{rep._pct(len(bad_time))} have a start time that isn't a "
                           f"number, so were left out (e.g. {eg}){hint}")
        if blank_obs:
            rep.add("W11", f"{rep._pct(len(blank_obs))} have a blank {observation} and "
                           f"were left out (e.g. {_example_rows(blank_obs)})")
        if blank_event:
            rep.add("W12", f"{rep._pct(len(blank_event))} have a blank {event} and "
                           f"were left out (e.g. {_example_rows(blank_event)})")
        # W13: labels that differ only by case/spacing
        groups: dict[str, set] = defaultdict(set)
        for evs in rows_by_obs.values():
            for _, code in evs:
                groups[_norm_label(code)].add(code)
        clashes = [sorted(v) for v in groups.values() if len(v) > 1]
        if clashes:
            eg = ", ".join(repr(x) for x in clashes[0])
            more = f", and {len(clashes) - 1} more set(s)" if len(clashes) > 1 else ""
            rep.add("W13", f"{len(clashes)} set(s) of labels differ only by "
                           f"capitalisation or spacing (e.g. {eg}){more}; they are "
                           f"counted as different events")
        # W14: window problems
        if bad_window or out_of_window:
            bits = []
            if bad_window:
                bits.append(f"{bad_window} observation(s) have a window ending at or "
                            f"before it starts")
            if out_of_window:
                bits.append(f"{out_of_window} event(s) fall outside their window")
            rep.add("W14", "; ".join(bits))
        # W15: time unit looks wrong
        all_t = [t for evs in rows_by_obs.values() for t, _ in evs]
        if all_t:
            hi = max(all_t)
            if time_unit == "ms" and hi < 1000 and len(all_t) > 5:
                rep.add("W15", f"with time_unit='ms', every event falls in under one "
                               f"second (largest time {hi} ms); the times may really be "
                               f"in seconds")
            elif time_unit == "s" and hi > 1_000_000:
                rep.add("W15", f"with time_unit='s', the times run very large (up to "
                               f"{hi} s, over 11 days); they may really be in milliseconds")

        # I20: observations too small to host a pattern
        tiny = sum(1 for o in sample if len(o.events) < 2)
        if tiny:
            rep.add("I20", f"{tiny} of {len(sample)} observations have fewer than two "
                           f"events; they set the baseline rates but cannot contain a "
                           f"pattern (the Methods text reports both counts)")
        # I21: single observation
        if len(sample) == 1:
            rep.add("I21", "the file contains only one observation; patterns are "
                           "counted across observations, so a single time-line will "
                           "detect little")
        # I22: a dominant event type
        counts = Counter(code for evs in rows_by_obs.values() for _, code in evs)
        total_ev = sum(counts.values())
        if total_ev:
            top, n_top = counts.most_common(1)[0]
            if len(counts) > 1 and n_top / total_ev >= 0.30:
                rep.add("I22", f"one event type, {top!r}, is {n_top / total_ev:.0%} of "
                               f"all events; a very common event can link to almost "
                               f"anything")
        # I23: high co-timestamp fraction
        adj = same = 0
        for evs in rows_by_obs.values():
            ts = sorted(t for t, _ in evs)
            for a, b in zip(ts, ts[1:]):
                adj += 1
                if a == b:
                    same += 1
        if adj and same / adj >= 0.10:
            rep.add("I23", f"{same / adj:.0%} of neighbouring events share an identical "
                           f"time; their order is undefined at that resolution")

    finish_or_raise()
    return sample


def check_reference() -> list[dict]:
    """Return the check registry as ordered rows (code, severity, condition, fix).

    Used to generate the tutorial's Appendix A from the same source the runtime
    messages use, so the paper and the software cannot disagree.
    """
    label = {"E": "Error (stops the read)", "W": "Warning (loads anyway)",
             "I": "Information (loads anyway)"}
    return [{"code": c, "severity": label[m["severity"]],
             "condition": m["condition"], "fix": m["fix"],
             "example": m.get("example", "")}
            for c, m in CHECKS.items()]


def read_observation(path: str | Path) -> Observation:
    """Read a single THEME ``.txt`` file into one :class:`Observation`.

    THEME files have one ``time<TAB>event`` row per line, with ``:`` marking the
    start of the window and ``&`` the end. Whitespace-separated files are tolerated,
    and if a marker is missing the window falls back to the first and last event.
    """
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
    if start is None:
        start = events[0][0] if events else 0
    if end is None:
        end = events[-1][0] if events else start
    return Observation(name=path.stem, start=start, end=end, events=events)


def read_sample(folder: str | Path, pattern: str = "*.txt") -> list[Observation]:
    """Read every THEME file in a folder into a list of observations (a "sample")."""
    folder = Path(folder)
    files = sorted(folder.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} in {folder}")
    return [read_observation(f) for f in files]


def read_sofcoder(path: str | Path, *, dataname: str = "DATANAME",
                  t: str = "T", events: str = "Events", sep: str | None = None,
                  code_sep: str = ",", frames_per_second: float | None = None,
                  start_marker: str = ":", end_marker: str = "&") -> list[Observation]:
    """Read a SOF-CODER / THEME data file (``DATANAME, T, Events``) into a sample.

    SOF-CODER (Jonsson et al., 2006) writes one row per time frame, each row holding
    several comma-separated codes that are active at that frame. This reader splits
    each row so every code becomes one event at time ``T``; codes that share a frame
    are co-timed, and ``min_lag`` / ``collapse_duplicates`` then decide how that
    co-occurrence is treated. Each ``DATANAME`` becomes one :class:`Observation`, and
    rows whose Events field is the ``:`` or ``&`` marker set the window (``T = end -
    start`` is the NX/T denominator); without the markers the window falls back to
    the first and last event.

    The outer separator is auto-detected (tab if present, else whitespace) unless
    ``sep`` is given; ``code_sep`` splits the Events field (default ``','``). ``T`` is
    kept in the file's own frame unit unless ``frames_per_second`` is given, which
    converts frames to milliseconds. A header naming the columns is used if present,
    otherwise the columns are read positionally as (DATANAME, T, Events).

    This is the way in for data collected in the SOF-CODER/THEME world; for a tool
    that already exports one row per single event, use :func:`read_table`.
    """
    path = Path(path)
    scale = (1000.0 / frames_per_second) if frames_per_second else 1.0

    def split_row(line: str) -> list[str]:
        if sep is not None:
            parts = line.split(sep)
        elif "\t" in line:
            parts = line.split("\t")
        else:
            parts = line.split(None, 2)   # DATANAME, T, Events (Events holds no spaces)
        return [p.strip() for p in parts]

    with open(path, newline="") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        return []

    header = [h.lower() for h in split_row(lines[0])]
    if dataname.lower() in header and events.lower() in header:
        di, ti, ei = (header.index(dataname.lower()), header.index(t.lower()),
                      header.index(events.lower()))
        body = lines[1:]
    else:
        di, ti, ei, body = 0, 1, 2, lines   # positional fallback

    rows_by_obs: dict[str, list] = defaultdict(list)
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    for line in body:
        parts = split_row(line)
        if len(parts) <= max(di, ti, ei):
            continue
        obs_id = parts[di]
        if not obs_id:
            continue
        try:
            tv = int(round(float(parts[ti]) * scale))
        except (ValueError, TypeError):
            continue
        raw = parts[ei]
        if raw == start_marker:
            starts.setdefault(obs_id, tv)
            continue
        if raw == end_marker:
            ends[obs_id] = tv
            continue
        for code in raw.split(code_sep):
            code = code.strip()
            if code and code not in (start_marker, end_marker):
                rows_by_obs[obs_id].append((tv, code))

    sample: list[Observation] = []
    for obs_id, evs in rows_by_obs.items():
        evs.sort(key=lambda e: e[0])
        o_start = starts.get(obs_id, evs[0][0])
        o_end = ends.get(obs_id, evs[-1][0])
        sample.append(Observation(name=obs_id, start=o_start, end=o_end, events=evs))
    return sample
