Getting started, and templates to adapt.

The 0.1.10–0.1.12 releases made the tool forgiving (plain-language data checks), temporal (occurrence timing reported by default), and self-documenting (readable columns, one reference behind `explain()` and `PARAMETERS.md`). 0.1.13 makes it easy to **start**.

### A starting point for your own research
`new_analysis()` writes a heavily commented starter script — load, inspect, `recommend()`, configure, calibrate, report — with every line to change marked `# <-- EDIT` and a pointer to `explain()` for each setting. Three variants:

- `new_analysis()` — **basic**: one group, detect → calibrate → report
- `new_analysis(template="two_groups")` — compare two groups (odds ratios + forest plot)
- `new_analysis(template="null_choice")` — core vs shell (which null a pattern survives)

All three also ship under `examples/`.

### README rewritten around the user
A one-minute *Getting started* (install → `new_analysis()` → edit → run) and a *What you get* summary of the recent developments: forgiving data import, the chance model, temporal reporting, readable output, the single reference behind `explain()`/`PARAMETERS.md`, and the shared figure style.
