# Examples

- **`quickstart.py`** — runs anywhere, no data needed. Plants a known pattern into
  noise and runs the full detect → calibrate → report pipeline.
  ```bash
  python examples/quickstart.py
  ```

- **`reproduce_worldcup.py`** — the archived reproducibility script for the
  technical note (reproduces THEME concordance + surrogate calibration on the 2022
  World Cup shot-ending sequences). **Requires the THEME observation files**
  (`THEME_Goals/`, `THEME_NonGoals/`, `THEME_Saved/`), which are derived from PFF
  Sports event data and are **not redistributable**, so they are not included here.
  With the data placed alongside the script's expected paths it regenerates every
  number reported in the technical note.
