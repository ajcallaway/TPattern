# tpattern 0.1.15 — release runbook (2026-11-07)

Copy-paste, top to bottom. Everything runs from the repo root:

    cd ~/Documents/Research/tpattern

Already done for you: `pyproject.toml`, `tpattern/__init__.py` at 0.1.15;
`CITATION.cff` bumped 0.1.9 -> 0.1.15 and re-dated; `r/DESCRIPTION` 0.1.14 -> 0.1.15;
CHANGELOG 0.1.15 re-dated 2026-09-01 -> 2026-11-07.
`CITATION.cff`'s `doi:` is the **concept** DOI (verified: it redirects to the latest
record), so it is correct as-is and must not be changed per version.

---

## Step 1 — gate: tests must pass

    python3 -m pytest -q

Do not continue if anything fails.

---

## Step 2 — keep the logs out, commit the evidence

    printf '\n# run logs (the JSONs are the evidence, the logs are noise)\nresults/*.log\n' >> .gitignore

    git add .gitignore CHANGELOG.md CITATION.cff pyproject.toml r/DESCRIPTION \
            tpattern/__init__.py tpattern/significance.py \
            examples/validate_synthetic.py examples/validate_null_choice.py \
            examples/by_all.py examples/verify_theme_inputs.py \
            results/by_all.json results/null2000.json results/null_choice_B2000.json \
            results/pooled_Goals.json results/pooled_NonGoals.json results/pooled_DefRecovery.json

    git status --short          # check nothing unexpected is staged

Note: `results/valsynth_B2000.json` is deliberately left out — that run is still
going. Add it in a follow-up commit once it finishes.

    git commit -m "$(cat <<'EOF'
0.1.15: dependence-robust FDR (Benjamini-Yekutieli), per-analysis false-positive rate

- significance: add fdr_q_by and _benjamini_yekutieli(); kept("fdr_by"/"by")
- validate_synthetic: false-positive rate per analysis over independent null
  datasets, not per pattern over dependent within-dataset patterns; --B/--K/--nulls
  flags; write to results/ rather than /tmp
- validate_null_choice: --B flag, results/ output
- examples: by_all.py (per-group calibration, resumable) and
  verify_theme_inputs.py (proves tpattern and THEME were fed identical input:
  all 2,138 sequences match)
- results/: the JSON backing the validation paper's tables
- CITATION.cff, r/DESCRIPTION version bumps

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"

---

## Step 3 — tag and push

    git tag -a v0.1.15 -m "tpattern 0.1.15: dependence-robust FDR (Benjamini-Yekutieli)"
    git push origin main
    git push origin v0.1.15

---

## Step 4 — GitHub release (this is what fires Zenodo)

No `gh` CLI on this machine, so in the browser:

<https://github.com/ajcallaway/TPattern/releases/new?tag=v0.1.15>

- Tag: `v0.1.15` (it will already exist)
- Title: `v0.1.15 — dependence-robust FDR`
- Body: paste the `## 0.1.15` block from `CHANGELOG.md`
- **Publish release**

---

## Step 5 — PyPI

    rm -rf dist/ build/ *.egg-info
    python3 -m build
    python3 -m twine check dist/*
    python3 -m twine upload dist/tpattern-0.1.15*

There is no `~/.pypirc`, so twine will prompt. Username `__token__`, password is the
PyPI API token (`pypi-...`). Then confirm:

    curl -s https://pypi.org/pypi/tpattern/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"

Should print `0.1.15`.

---

## Step 6 — Zenodo version DOI -> the paper

Within a few minutes of Step 4, a new version record should appear under
<https://doi.org/10.5281/zenodo.21397543> (the concept DOI, which always resolves to
the newest version). Open it and copy the **version** DOI shown on that record,
i.e. `10.5281/zenodo.<new-number>` — not the concept DOI.

If no new record appears, the GitHub->Zenodo webhook is off: switch the TPattern repo
on at <https://zenodo.org/account/settings/github/> and re-publish the release.

Then paste that version DOI over the **RED placeholder** in §5 / Availability of
`TPattern_ValidationPaper_v9.docx`. Tell me the number and I will do the paste and
clear the RED.

---

## Step 7 — THEME input deposit (separate Zenodo upload, its own DOI)

New upload at <https://zenodo.org/uploads/new>:

- Files: `THEME_Edu_v6_inputs.zip`, `README_THEME_inputs.md`, `vvt_reference.vvt`
  from `.../3_Temporal/ToSubmit/SUBMISSION/Validation/THEME_deposit/`
- Type: Dataset
- Title: `THEME Edu v6 input files for the World Cup 2022 T-pattern analysis`
- Creator: Callaway, Andrew (ORCID 0000-0003-0987-9608, Bournemouth University)
- Licence: whatever the PFF data agreement permits for derived event sequences —
  **check this before publishing, it is the one thing here that is not reversible**
- Related identifier: `10.5281/zenodo.21397543`, relation "is supplement to"

Publish, then give me the dataset DOI for the Availability section.

---

## Step 8 — publications.html

The `DEFAULT_PAPERS` seed is already updated with the three tpattern records. Your
browser still shows the old set from `localStorage`. Either reseed (clear the paper
data in the app — back up first, it wipes in-browser edits) or make the same three
additions through the app's New-paper dialog.

---

## What this unblocks

Priority action 1 of the peer review. Steps 4-7 turn five statements in the
manuscript that currently say the software and inputs "are deposited" from false
into true, and give Table 1 its only verification path.
