"""
A guided, transparent analysis workflow.
========================================

Wraps the library's pieces — read the data, inspect it, take the tool's
recommendation, run the calibrated analysis, and write the outputs — into a
step-by-step flow a non-programmer can follow. Every choice is shown and
overridable, so the analysis stays transparent and repeatable.

Two entry points:

  run_analysis(...)   pure function: load -> advise -> calibrate -> report ->
                      Methods text. No UI; used by scripts, tests and the widget.
  launch()            an interactive wizard (file upload, radio buttons, run,
                      download) for Google Colab / Jupyter. Needs ipywidgets.

The logic lives in run_analysis so it can be tested headlessly; launch() is a
thin UI over it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .io import read_table
from .detect import Config
from .significance import calibrate
from .report import report, patterns_table
from .methods import methods_text
from .advisor import recommend

#: the most recent CalibrationResult (set by launch()); use it to redraw figures or
#: rebuild tables, e.g. patterns_overview([c.pattern for c in tpattern.guided.last.kept("fdr")], ...)
last = None


@dataclass
class GuidedResult:
    outdir: str
    files: dict = field(default_factory=dict)   # label -> path
    n_detected: int = 0
    n_survivors: int = 0
    methods: str = ""
    recommendation: str = ""
    survivors: list = field(default_factory=list)   # [{pattern, N, q}] surviving FDR
    calibration: object = None                      # the CalibrationResult (for re-plotting)
    ci_unit: str = ""


def run_analysis(path, *, observation="observation", event="event", start="start",
                 obs_start=None, obs_end=None, time_unit="s",
                 null="profile", min_lag=1, B=200, q_target=0.05, alpha=0.005,
                 seed=20260714, outdir="tpattern_output", title="T-pattern analysis",
                 build_event_from=None):
    """Run the whole pipeline and write the outputs. Returns a GuidedResult.

    This is the engine behind the wizard: it reads the canonical table, records
    what the tool would recommend (for transparency), calibrates with the chosen
    settings, writes the report (table, dendrograms, summary) plus an Excel copy
    of the results table, and generates the paste-ready Methods paragraph.
    """
    obs = read_table(path, observation=observation, event=event, start=start,
                     obs_start=obs_start, obs_end=obs_end, time_unit=time_unit,
                     build_event_from=build_event_from)
    if not obs:
        raise ValueError("No observations were read — check the column names and "
                         "that the file has one row per event (see SCHEMA.md).")

    rec = str(recommend(obs))
    cfg = Config(min_lag=min_lag)
    result = calibrate(obs, cfg, null=null, B=B, alpha=alpha, q_target=q_target,
                       seed=seed)

    Path(outdir).mkdir(parents=True, exist_ok=True)
    written = report(result, outdir, title=title,
                     ci_unit=" ms" if time_unit == "ms" else " s")

    # an Excel-friendly copy of the surviving patterns (falls back to CSV-only)
    xlsx = _write_excel(result, q_target, Path(outdir) / "results.xlsx")
    if xlsx:
        written["excel"] = xlsx

    methods = methods_text(cfg, observations=obs, calibration=result)
    Path(outdir, "METHODS.txt").write_text(methods)
    written["methods"] = str(Path(outdir, "METHODS.txt"))

    survivors = [{"pattern": str(c.pattern), "N": c.N, "q": round(c.fdr_q, 4)}
                 for c in sorted(result.kept("fdr"), key=lambda c: c.p_emp)]

    return GuidedResult(
        outdir=outdir, files=written,
        n_detected=len(result.real), n_survivors=len(result.kept("fdr")),
        methods=methods, recommendation=rec, survivors=survivors,
        calibration=result, ci_unit=" ms" if time_unit == "ms" else " s")


def _write_excel(result, q_target, path):
    """Write the results table to .xlsx if pandas+openpyxl are available; else
    a plain CSV next to it. Returns the path written, or None."""
    rows = []
    for c in sorted(result.real, key=lambda c: c.p_emp):
        rows.append({
            "pattern": str(c.pattern), "N": c.N, "level": c.level,
            "critical_interval": f"[{c.ci[0]},{c.ci[1]}]" if c.ci else "",
            "p_empirical": round(c.p_emp, 4), "q_FDR": round(c.fdr_q, 4),
            "survives_FDR": int(c.fdr_q <= q_target), "survives_FWER": int(c.fwer_keep),
        })
    try:
        import pandas as pd
        pd.DataFrame(rows).to_excel(path, index=False)
        return str(path)
    except Exception:
        csv_path = path.with_suffix(".csv")
        if rows:
            with open(csv_path, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)
            return str(csv_path)
        return None


# ------------------------------------------------------------------- the wizard
def launch():
    """Interactive wizard for Google Colab / Jupyter.

    Guides the user through: upload a CSV -> map the columns -> see the tool's
    inspection and recommendation -> confirm or change the settings (radio
    buttons, pre-set to the recommendation) -> run -> download the outputs and
    copy the Methods sentence. Requires ipywidgets (pip install 'tpattern[gui]').
    """
    try:
        import ipywidgets as W
        from IPython.display import display, clear_output
    except ImportError as e:  # pragma: no cover - UI only
        raise ImportError(
            "launch() needs ipywidgets — install with `pip install ipywidgets` "
            "(or `pip install 'tpattern[gui]'`) and run in Colab/Jupyter. For a "
            "non-interactive run use run_analysis(...).") from e

    import csv as _csv
    from collections import Counter
    state = {"path": None}
    HELP = "color:#5b6270;font-size:90%"
    STYLE = {"description_width": "initial"}
    WIDE = W.Layout(width="480px")

    # ---------- Step 1: file + columns ----------
    upload = W.FileUpload(accept=".csv", multiple=False, description="1. Upload CSV")
    cols_info = W.HTML("")
    obs_c = W.Text(value="observation", description="observation", style=STYLE)
    ev_c = W.Text(value="event", description="event", style=STYLE)
    st_c = W.Text(value="start", description="start", style=STYLE)
    unit = W.RadioButtons(options=["s", "ms"], value="s", description="time unit",
                          style=STYLE)
    unit_help = W.HTML(f"<span style='{HELP}'>seconds by default; choose <b>ms</b> if "
                       "your timestamps are whole numbers of milliseconds.</span>")
    advise_btn = W.Button(description="2. Inspect & advise", button_style="info",
                          layout=W.Layout(width="200px"))
    advice_out = W.Output()

    # ---------- Step 3: method settings (revealed after inspect) ----------
    null_w = W.RadioButtons(options=["profile", "rotation"], value="profile",
                            description="null", style=STYLE)
    null_help = W.HTML(f"<span style='{HELP}'><b>profile</b> (recommended): checks a "
                       "pattern is a real link between actions, not just their usual "
                       "timing. <b>rotation</b>: the simpler THEME-style shuffle.</span>")
    lag_w = W.RadioButtons(
        options=[("require a genuine lag  (min_lag = 1)", 1),
                 ("allow co-timing  (min_lag = 0)", 0)],
        value=1, description="lag", style=STYLE, layout=WIDE)
    lag_help = W.HTML(f"<span style='{HELP}'><b>genuine lag</b> (recommended for "
                      "video/frame data): events at the same timestamp are treated as "
                      "happening together, not as a sequence. <b>co-timing</b>: keeps "
                      "them as ordered (THEME's default).</span>")
    B_w = W.IntSlider(value=200, min=100, max=2000, step=100, description="surrogates B",
                      style=STYLE)
    B_help = W.HTML(f"<span style='{HELP}'>more surrogates = finer p-values; "
                    "family-wise (FWER) claims need B in the thousands.</span>")
    run_btn = W.Button(description="3. Run analysis", button_style="success",
                       layout=W.Layout(width="200px"))
    settings_box = W.VBox(
        [W.HTML("<hr><b>Recommended method settings</b> — pre-set from your data; "
                "each shows why. Override if you wish, then Run."),
         null_w, null_help, lag_w, lag_help, B_w, B_help, run_btn],
        layout=W.Layout(display="none"))          # hidden until Inspect & advise
    results_out = W.Output()

    def _save_upload():
        if not upload.value:
            return None
        item = list(upload.value.values())[0] if isinstance(upload.value, dict) \
            else upload.value[0]
        content = item["content"]
        p = Path("uploaded_events.csv")
        p.write_bytes(content if isinstance(content, (bytes, bytearray))
                      else bytes(content))
        return str(p)

    def _on_upload(_):
        path = _save_upload()
        if not path:
            return
        state["path"] = path
        with open(path, newline="") as fh:
            reader = _csv.reader(fh)
            header = next(reader, [])
            row2 = next(reader, [])
        info = ("<b>Columns in your file:</b> "
                + ", ".join(f"<code>{c}</code>" for c in header)
                + f"<br><span style='{HELP}'>Set the three boxes below to match these "
                  "(defaults: observation / event / start).</span>")
        try:
            si = header.index(st_c.value) if st_c.value in header else 2
            v = float(row2[si])
            if v.is_integer() and abs(v) >= 1000:
                info += ("<br><b style='color:#b5342a'>Tip:</b> your start times look "
                         "like <b>milliseconds</b> — select <b>ms</b> above.")
        except Exception:
            pass
        cols_info.value = info

    upload.observe(_on_upload, names="value")

    def _data_quality(obs):
        """(exact-duplicate rows, fraction of consecutive events that are co-timed)."""
        dup = same = total = 0
        for o in obs:
            counts = Counter((t, e) for t, e in o.events)
            dup += sum(c - 1 for c in counts.values() if c > 1)
            ts = [t for t, _ in o.events]
            for i in range(1, len(ts)):
                total += 1
                same += (ts[i] == ts[i - 1])
        return dup, (same / total if total else 0.0)

    def _on_advise(_):
        with advice_out:
            clear_output()
            if not state.get("path"):
                state["path"] = _save_upload()
            if not state.get("path"):
                print("Upload a CSV first."); return
            obs = read_table(state["path"], observation=obs_c.value, event=ev_c.value,
                             start=st_c.value, time_unit=unit.value)
            rec = recommend(obs)
            for c in rec.choices:                 # pre-set the widgets from the data
                if c.option == "Null":
                    null_w.value = "profile" if "profile" in c.recommended.lower() else "rotation"
                if c.option == "Minimum lag":
                    lag_w.value = 1 if "min_lag = 1" in c.recommended else 0
            from IPython.display import display as _d, HTML
            _d(HTML(f"<b>Your data:</b> {len(obs)} observations, "
                    f"{sum(len(o.events) for o in obs)} events."))
            _d(HTML("<b>What the tool recommends for your data</b>, and why (in plain "
                    "terms):<ul>"
                    + "".join(f"<li style='margin-bottom:6px'>{c.plain}</li>"
                              for c in rec.choices) + "</ul>"))
            _d(HTML("<details><summary>Show the technical rationale (for your methods "
                    "section)</summary><pre style='white-space:pre-wrap;font-size:88%'>"
                    + "\n\n".join(f"[{c.option}]  ->  {c.recommended}\n{c.rationale}"
                                  for c in rec.choices) + "</pre></details>"))
            dup, cofrac = _data_quality(obs)
            msg = (f"<hr><b>Data-quality check</b><br>{cofrac:.0%} of consecutive events "
                   "share a timestamp. This is <b>normal for video/frame-coded data</b> — "
                   "different actions coded at the same video frame (e.g. an interception "
                   "and the challenge that caused it) — and is <b>not an error</b>. The "
                   "recommended 'genuine lag' setting handles it correctly.")
            if dup:
                msg += (f"<br><b style='color:#b5342a'>Worth checking:</b> {dup} exact "
                        "duplicate row(s) (identical observation, event and time) — these "
                        "may be accidental double-entries.")
            else:
                msg += ("<br>No exact duplicate rows found — the shared timestamps are all "
                        "genuine co-occurrences.")
            _d(HTML(msg))
        settings_box.layout.display = ""          # reveal step 3

    def _colored_table(rows):
        bg = {"r": "#e7f5ea", "b": "#fdf3e0", "c": "#f5f5f6"}
        head = ["pattern", "times seen", "timing", "reliability (q, lower = stronger)",
                "what it means"]
        h = ["<table style='border-collapse:collapse;font-size:90%;width:100%'>",
             "<tr>" + "".join(f"<th style='text-align:left;padding:5px 9px;"
                              f"border-bottom:2px solid #ccc'>{c}</th>" for c in head)
             + "</tr>"]
        for r in rows:
            q = r["fdr_q"]
            v = "r" if q <= 0.05 else "b" if q <= 0.10 else "c"
            cells = [r["pattern"], r["N"], r["critical_interval"], f"{q:.3g}",
                     r["interpretation"]]
            h.append(f"<tr style='background:{bg[v]}'>"
                     + "".join(f"<td style='padding:5px 9px;border-bottom:1px solid #eee'>"
                               f"{c}</td>" for c in cells) + "</tr>")
        h.append("</table>")
        return "".join(h)

    def _on_run(_):
        with results_out:
            clear_output()
            if not state.get("path"):
                print("Upload a CSV and click Inspect & advise first."); return
            from IPython.display import display as _d, HTML, Image
            _d(HTML("<p>Running… calibration with many surrogates can take a minute.</p>"))
            res = run_analysis(state["path"], observation=obs_c.value,
                               event=ev_c.value, start=st_c.value, time_unit=unit.value,
                               null=null_w.value, min_lag=lag_w.value, B=B_w.value)
            globals()["last"] = res.calibration    # tpattern.guided.last, for re-plotting
            clear_output()

            rows = patterns_table(res.calibration, ci_unit=res.ci_unit)
            robust = sum(1 for r in rows if r["fdr_q"] <= 0.05)
            border = sum(1 for r in rows if 0.05 < r["fdr_q"] <= 0.10)
            chance = len(rows) - robust - border
            _d(HTML(
                f"<h3>Results</h3><p>The tool found <b>{res.n_detected}</b> candidate "
                f"patterns and tested each against chance. <b>All {res.n_detected} are "
                "listed below — nothing is removed</b>; the verdict tells you which to "
                "trust:</p><ul>"
                f"<li>🟢 <b>{robust} robust</b> — statistically reliable; safe to report.</li>"
                f"<li>🟡 <b>{border} borderline</b> — near the threshold; treat with caution.</li>"
                f"<li>⚪ <b>{chance} likely chance</b> — not distinguishable from random.</li>"
                "</ul>"))
            if robust == 0 and B_w.value < 2000:
                _d(HTML(f"<p style='color:#b5342a'>Nothing reached 'robust' at "
                        f"B = {B_w.value} — borderline patterns need more surrogates. "
                        "Raise <b>surrogates B</b> toward 2000 and re-run before "
                        "concluding there is no signal.</p>"))

            _d(HTML("<p style='color:#5b6270;font-size:90%'>How to read the table: each "
                    "row is a pattern. <b>q</b> is the risk it is a fluke — the "
                    "false-discovery rate (FDR); lower is stronger, and below 0.05 "
                    "counts as robust. Rows are coloured 🟢&nbsp;reliable · "
                    "🟡&nbsp;borderline · ⚪&nbsp;likely chance.</p>"))
            _d(HTML(_colored_table(rows)))         # colour-coded results table

            dpath = res.files.get("dendrograms")
            if dpath and Path(dpath).exists():
                _d(HTML("<b>Pattern dendrograms</b> (top patterns):"))
                _d(Image(dpath))

            _d(HTML("<details><summary><b>Customise the figures &amp; table</b> "
                    "(click to expand)</summary><pre>"
                    "from tpattern import patterns_overview, pattern_dendrogram, patterns_table\n"
                    "import tpattern.guided as g\n"
                    "keep = [c.pattern for c in g.last.kept('fdr')]   # surviving patterns\n"
                    f"patterns_overview(keep, 'dendrograms.png', ci_unit='{res.ci_unit}', max_rows=8)\n"
                    f"pattern_dendrogram(keep[0], title='my title', ci_unit='{res.ci_unit}', outfile='one.png')\n"
                    f"patterns_table(g.last, 'table.csv', ci_unit='{res.ci_unit}')</pre></details>"))

            _d(HTML("<b>Methods</b> (paste into your write-up):"))
            print(res.methods)

            import shutil
            zpath = shutil.make_archive(res.outdir, "zip", res.outdir)
            try:
                from google.colab import files  # pragma: no cover
                files.download(zpath)
            except Exception:
                print(f"\nAll outputs saved to {res.outdir}/  (download: {zpath})")

    advise_btn.on_click(_on_advise)
    run_btn.on_click(_on_run)
    display(W.VBox([
        W.HTML("<h3>tpattern — guided analysis</h3>"
               "<p>Four steps: <b>upload</b> your events → <b>inspect</b> (see the "
               "recommendation) → the recommended <b>settings</b> appear → <b>run</b>.</p>"),
        upload, cols_info,
        W.HTML("<b>Column names</b> (change if your export differs):"),
        obs_c, ev_c, st_c, unit, unit_help,
        advise_btn, advice_out, settings_box, results_out]))
