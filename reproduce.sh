#!/usr/bin/env bash
# reproduce.sh — set up tpattern and verify every reported result reproduces.
# Run from the repository root:   bash reproduce.sh
#
# Does NOT run the MATLAB derivation (data/derivation/) — that needs MATLAB and the
# raw PFF World Cup JSONs. The derived sequences ship in data/, so everything below
# reproduces from this repository alone.

set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/6  Python virtual environment =="
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip

echo "== 2/6  Install tpattern (with test + GUI extras) =="
pip install -q -e ".[test,gui]"

echo "== 3/6  Test suite (THEME reproduction + synthetic ground truth) =="
pytest -q

echo "== 4/6  Examples =="
python examples/quickstart.py                 # synthetic ground-truth demo (no data needed)
python examples/reproduce_worldcup.py         # concordance, exclusion, concurrency (~5 s)

echo "== 5/6  Full surrogate calibration on the real data (~10 min) =="
python examples/reproduce_worldcup.py --calibrate

echo "== 6/6  Null-choice validation (complementary blind spots; ~3-5 min) =="
python examples/validate_null_choice.py

echo ""
echo "Done. If all of the above passed, the repository reproduces the reported results."
