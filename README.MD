# Software Change Predictor — related-file inspection research

This research prototype uses Flask Git history to recommend related files for developers to inspect when modifying a file. It compares temporal co-change, file-role and historical Python import evidence. A separate Random Forest baseline estimates file activity in a 30-day window after the included historical snapshot.

## What the app shows

1. **Related files to inspect:** choose a source, test or configuration file and request up to three suggestions using the included history.
2. **Historical import evidence:** explore saved replay examples and evaluation results. This section does not analyze the file selected in the interactive recommender.
3. **All-file experiment:** explore co-change suggestions across a wider file scope.
4. **Historical forecast baseline and datasets:** inspect the forecast, snapshot cutoff and source CSVs.

The app displays the cutoff derived from the supplied history (currently 30 October 2026). File paths belong to the analyzed Flask repository. The application does not monitor incoming commits or offer repository upload. Forecasting and recommendation engines operate independently.

Evidence-aware precision in the saved 354-event comparison is 18.49%, versus 18.58% for temporal and 18.68% for role-aware ranking. The evidence-aware method has not established an improvement. Same-commit files are proxy labels for inspection relevance; scores do not establish required edits or defects. External validation and developer usefulness assessment remain open.

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for the complete scope and [EVIDENCE_RESULTS.md](EVIDENCE_RESULTS.md) for evaluation limitations. The following sections document the baseline and research experiments.

## Contents
- `app.py`: Streamlit UI for file-level change prediction.
- `src/collect_data.py`: collect file modifications from a local Git repository.
- `src/train_change_model.py`: build sliding-window labels (90 days of history -> next 30 days) and train a Random Forest classifier.
- `src/extract_features.py`: create a file-level snapshot for prediction.
- `src/broken_ripple.py`: standalone co-change rule mining and related-file warning proof of concept.
- `data/raw/commits.csv`: existing sample commit history.
- `data/processed/training_dataset.csv`: training rows and future-change labels.
- `data/processed/features.csv`: latest extracted feature snapshot.
- `models/change_model.pkl`: existing change-prediction model artifact.

The separate code-upload, Python syntax-fixing, and missing secondary-model UI have been removed. The existing Random Forest pipeline and data are otherwise preserved.

## Setup

From the project root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

To regenerate the existing model and features from the stored Git history:

```bash
python src/train_change_model.py
python src/extract_features.py
```

To collect fresh history from a **locally cloned Git repository**, first run:

```bash
python src/collect_data.py /path/to/local/git/repository
```

Then retrain and extract features. **Warning:** collecting data replaces `data/raw/commits.csv` for that project.

## Input, target and output

The four historical inputs are `change_frequency`, `change_velocity_30d`, `days_since_last_change`, and `change_entropy`.
The training target is `1` if that file occurs in the subsequent 30-day Git history, otherwise `0`.
`predict()` returns `0`/`1`. `predict_proba()` returns an **uncalibrated model-estimated score** in `[0,1]`; the UI formats it as a percentage. This is *not* an empirically verified chance of change and does *not* indicate a defect.

## Research and interpretation limitations

- The history and latest snapshot in this archive are fixed; 'next 30 days' in the historical snapshot is not automatically relative to today's date. Fresh forecasts require collecting recent Git history and regenerating features.
- The snapshot currently covers only files changed during the recent 90-day history, not necessarily all files in the repository.
- Training/testing is split by unique time-window dates, not by number of rows.
- No probability calibration or multi-repository validation is included.
- Co-change mining is separate from the current Streamlit UI and must be assessed experimentally before using it to advise developers.
- Do not treat high change likelihood as proof of bugs, poor quality, or required work.
- Before publication, establish an explicit research question, compare prior work and strong baselines, and evaluate with temporal holdout tests across repositories.

This cleaned archive is a scoped starting point, **not a claim of publication-ready novelty**.

## NEW: Research prototype — file co-change recommendations

The original 30-day Random Forest change forecast remains available as a baseline. The Streamlit interface now includes a **Co-Change Recommendation** section: choose a file already being modified to see up to 3 other files to inspect. Scores are **relative evidence scores, not probabilities**.

This prototype is *not defect prediction*, does *not automatically change code*, and does *not currently establish publication-level novelty*.

```bash
python src/evaluate_cochange.py
streamlit run app.py
```

Research method: `src/cochange_recommender.py`  
Leakage-aware historical evaluation: `src/evaluate_cochange.py`  
Detailed methodology/results/limitations: `EXPERIMENT_01.md`  
Generated reports: `results/cochange/`

**Research caution:** Initial results show that the experimental selective method does not outperform a fairly thresholded temporal-confidence baseline on precision and recall. Rework the proposed innovation and test across more repositories before claiming superiority.


## Research Phase 2 — Code-focused recommendations

The project includes a second **experimental** recommender for source, test, and configuration file inspection. It compares static co-change, time-aware co-change, and a role-aware temporal candidate using exactly the same code-focused evaluation task. The new method uses file paths/names, not actual source dependencies. It does **not** contain defect prediction.

```bash
python3 src/evaluate_context.py
python3 -m unittest discover -s tests -v
python3 -m streamlit run app.py
```

Read `EXPERIMENT_02.md` for the precise task and results. Phase 2 and Experiment 01 measure different scopes; their precision values cannot be compared directly. The new method has higher precision but lower recall than the gated time-aware baseline on the tested Flask history, and novelty has **not** been established.
