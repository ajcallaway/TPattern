# Examples

- **`quickstart.py`** — no data needed. Plants a known pattern into noise and runs
  the full detect → calibrate → report pipeline.
  ```bash
  python examples/quickstart.py
  ```

- **`reproduce_worldcup.py`** — reproduces the published World Cup results from the
  data shipped in [`../data/`](../data/). Runs out of the box:
  ```bash
  python examples/reproduce_worldcup.py              # concordance, exclusion, concurrency (~5 s)
  python examples/reproduce_worldcup.py --calibrate  # also the surrogate null (~10 min)
  ```
  It regenerates: the tpattern-vs-THEME pattern counts by level; the interception
  exclusion divergence; the co-occurrence-vs-sequence analysis; and (with
  `--calibrate`) how many patterns survive the surrogate null under FDR. All seeded
  and deterministic.

  See [`../data/README.md`](../data/README.md) for the data's provenance and how it
  was derived.
