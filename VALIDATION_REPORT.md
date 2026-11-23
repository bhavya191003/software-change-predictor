# Project validation report

Verification was performed on 21 November 2026 using the supplied Flask dataset, the complete local Flask Git clone, and the installed dependency versions recorded in `requirements-verified.txt`.

## Fixes

- Added shared history validation for required columns, usable records, valid dates, duplicate commit/file rows, and consistent commit timestamps. Git paths retain their original spaces.
- Added clear checks for empty and insufficient evaluation histories, invalid time-decay settings, invalid timestamps, and invalid score thresholds.
- Made training and feature extraction importable without running the pipeline. Added configurable input/output paths to both scripts and configurable collection output.
- Delayed training dataset output until training and prediction succeed. A failed insufficient-data run preserves existing artifacts.
- Added argument parsing and actionable command-line input errors for collection, training, extraction, and evaluation.
- Added app handling for unreadable feature CSVs, non-finite feature values, malformed model metadata, damaged optional reports, and unreadable dataset previews.

## Completed checks

| Workflow | Verified result |
|---|---|
| Automated suite | 26 tests passing |
| Forecast UI | All 24 available files exercised |
| Recommendation UI | All four all-file modes and all three context modes exercised |
| Recommendation engines | All 642 stored paths exercised through five all-file and three context methods |
| Recommendation invariants | At most three unique suggestions, positive finite scores, self exclusion, and context candidate eligibility |
| Historical source access | Temporary Git repository test confirms parent imports are used |
| Invalid inputs | Empty, incomplete, malformed and inconsistent histories rejected with actionable errors |
| App failure cases | Missing model, corrupt features and corrupt evidence report handled without uncaught app exceptions |
| Git collection | 17,196 records from 5,549 commits collected to a separate output |
| Model training | 10,953 training rows and 1,495 test rows completed successfully |
| Feature extraction | All 24 snapshot rows regenerated |
| Processed dataset reproduction | Both generated DataFrames match the supplied processed datasets |
| Forecast model output | Finite probability scores summing to one for all snapshot files |
| Co-change evaluation | Saved comparison CSV reproduced exactly |
| Context evaluation | Saved comparison CSV reproduced exactly |
| Full Phase 3 evaluation | Saved comparison CSV reproduced exactly |
| Evidence-aware evaluation | Saved comparison CSV reproduced exactly |
| Dependency scripts | Historical import extractor and single-event demonstration completed |
| Standalone rule mining | Broken Ripple demonstration completed |
| Source syntax | Every Python source compiled in memory |

Retraining achieved ROC-AUC **0.634408**. This measures future file activity. Recommendation quality and research limitations remain documented in [EVIDENCE_RESULTS.md](EVIDENCE_RESULTS.md).

## Run verification

```bash
python3 -m unittest discover -s tests -v
```

The expanded suite includes normal workflows and regression checks. Full historical evaluations are separate commands documented in [RUNNING.md](RUNNING.md).

The following output options allow pipeline verification without replacing the supplied artifacts.

```bash
python3 src/collect_data.py /path/to/clone --output /tmp/commits-check.csv
python3 src/train_change_model.py --model /tmp/model-check.pkl --dataset /tmp/training-check.csv
python3 src/extract_features.py --output /tmp/features-check.csv
```

Training and feature commands use the supplied raw dataset by default. Add `--input /tmp/commits-check.csv` to use the newly collected history.

## Verification boundaries

All listed checks passed in the installed environment. This is bounded verification and cannot establish that every possible input or environment is error-free.

A Python server is listening on port 8501. Direct HTTP requests from the execution environment failed. The browser connector was unavailable and native Chrome inspection timed out, so visual browser operation remains unverified. The Streamlit interaction tests exercised the application directly.

GitHub DNS resolution failed on a fresh attempt, preventing collection of additional repositories. Multi-repository research validation remains pending. A fresh environment installation also remains unverified. Existing Streamlit resource caches still require restarting the app after regenerating artifacts, as described in the running guide.

Machine-readable results are in [summary.json](results/verification/summary.json).
