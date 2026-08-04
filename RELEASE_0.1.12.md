Readable names, and one reference for every setting and output.

### One reference, generated everywhere
`tpattern/reference.py` is now the single source for every setting and output column — each with **what it does, its range, the recommended value, and what higher or lower means**. From it come:
- `explain("min_lag")`, `explain_settings()`, `explain_columns()` in the package
- the new **`PARAMETERS.md`**
- the tutorial's settings and output-column tables
- the plain-language field labels in the Colab form

So the code, the paper and the notebook cannot drift (the same pattern as the data-check `CHECKS` registry).

### Readable output columns
The two opaque columns are renamed: `p_emp` → **`monte_carlo_p`**, `fwer_keep` → **`survives_fwer_holm`** (`fdr_q` and the rest were already legible). Internal `Calibrated` attributes are unchanged, and `patterns_table(sort=...)` still accepts the old names.

### Self-documenting Colab form
Every field in the Step-4 settings panel now shows a one-line plain-English description, so the checkboxes and numbers are no longer bare variable names.
