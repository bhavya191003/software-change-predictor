# Implementation status and verification

## Completed in this extension

- Added `src/evidence_recommender.py`. Direct imports strengthen temporal evidence in proportion to decayed joint support. Import-only candidates receive zero score. A zero import weight recovers temporal ranking.
- Added `src/evaluate_evidence.py`. It replays validation and test history chronologically, selects an import weight on validation, compares static, temporal, role-aware, additive-import, and support-conditioned rankings, and exports full event evidence.
- Removed candidate truncation before parent-tree eligibility filtering in the new evaluator. Every historical neighbor is considered before ranking. Direct imports can expand the additive baseline's candidate set.
- Included cold-start seeds when they exist in the parent tree. The supported method can abstain, and these cases count in its evaluation. Events whose seed is absent from the parent are reported as skipped.
- Added paired event bootstrap intervals and diagnostics recording useful suggestions added, irrelevant suggestions added, useful suggestions displaced, and events helped or harmed.
- Added an evidence report and historical example explorer to the Streamlit application. Replaced deprecated table-width arguments.
- Added unit and integration tests for ranking, historical source boundaries, default app actions, and missing model handling.
- Recorded direct package versions in `requirements-verified.txt`.

## Verification

The test command is `python3 -m unittest discover -s tests -v`. The expanded suite now contains 26 passing tests. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for the full workflow audit. All Python sources passed an in-memory compilation check.

The original co-change and context evaluation scripts were rerun using temporary output directories. Both generated comparison CSVs exactly matched the supplied files. The stored model and original datasets were preserved.

The Streamlit application was checked through its automated interaction API. Browser appearance has not been visually verified during this extension. Version recording captures the installed direct packages. A clean-environment installation has not been performed.

## Reproduce the extension

From the project root, use a clone containing the CSV's Git commits and parents.

```bash
python3 src/evaluate_evidence.py --repo ../flask-source-complete
python3 -m unittest discover -s tests -v
python3 -m streamlit run app.py
```

Optional arguments are `--input`, `--output`, and `--top-k`. The default output directory is `results/evidence`. Existing files in that output directory are replaced. Historical source extraction can take several minutes.

## Remaining research work

Multi-repository validation requires additional histories. An attempted clone of `pallets/itsdangerous` failed because the execution environment could not resolve `github.com`. The evaluator accepts a separate CSV and clone for each future repository run.

The available test period has already been inspected during project development. Validation-based weight selection prevents direct test-set optimization in this script, but final claims still require fresh temporal periods or external repositories. The bootstrap resamples individual events and assumes independence. Temporal block resampling and repeated chronological splits remain useful follow-up work.

A systematic comparison with published approaches and a developer usefulness study remain open. The present evaluation measures same-commit retrieval. Probability calibration, causal change impact, productivity benefits, and research novelty have not been established.
