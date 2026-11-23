# Software Change Predictor project guide

This Python research prototype studies file changes using Flask Git history. It provides a Streamlit application and command-line experiments. The application starts with related-file inspection, followed by saved historical import evidence, the all-file experiment, and the separate forecast baseline. It displays the supplied history cutoff explicitly.

## Documentation

- [Validation report](VALIDATION_REPORT.md) records robustness fixes, full workflow checks, and verification boundaries.

- [Evidence-aware results](EVIDENCE_RESULTS.md) reports the new comparison and error analysis.

- [Implementation status](IMPLEMENTATION_STATUS.md) records the evidence-aware extension, verification, and remaining research work.

- [Architecture and data](ARCHITECTURE.md) describes modules, data contracts, and scoring.
- [Running and reproducing the project](RUNNING.md) provides setup and experiment commands.
- [Experiment 01](EXPERIMENT_01.md) reports all-file co-change recommendations.
- [Experiment 02](EXPERIMENT_02.md) reports code-focused recommendations.
- [Experiment 03](EXPERIMENT_03.md) reports the historical-import experiment.
- [Research direction](RESEARCH_DIRECTION.md) records the proposed research framing.
- [Existing README](README.MD) contains the original baseline guide and later additions.
- [Existing next steps](NEXT_STEPS.md) records planning through Phase 2. Phase 3 code and saved results are now also present.

## Capabilities

| Component | Input | Output | Entry point |
|---|---|---|---|
| Random Forest forecast | Four file-history features from a 90-day window | Binary estimate of change during the next 30 days and an uncalibrated model score | `app.py` |
| All-file co-change recommendation | A file being modified and earlier commit history | Up to three historically related file suggestions | `app.py`, `src/evaluate_cochange.py` |
| Code-focused recommendation | A source, test, or configuration file and earlier history | Ranked source, test, or configuration suggestions with evidence | `app.py`, `src/evaluate_context.py` |
| Import-assisted experiment | Historical Git clone, event commit, and Python seed | Rankings augmented by direct import relationships from the event parent | Phase 3 command-line scripts |

The Random Forest and recommendation engines run independently. The Streamlit application exposes the forecast and first two recommendation tasks. Phase 3 runs through the command line.

## Included snapshot

The checked-in CSV files contain 17,196 raw file-change records across 5,549 distinct commits, 12,448 labeled training observations, and 24 latest-window feature rows. Raw date strings range from April 2010 through October 2026. These counts describe the supplied files and can change when regenerated.

The project also includes `models/change_model.pkl`, generated CSV/JSON evaluation reports, `training_dataset.numbers`, and `phase3-results.zip`. Python scripts read the CSV datasets. The Numbers document and ZIP are accompanying artifacts.

## Reading the results

The forecast target is future file activity. Recommendation experiments use other files in the same historical commit as a proxy for inspection relevance. These targets measure different behavior.

Experiment 01's selective method records 41.47% precision and 24.28% recall. Its gated temporal baseline records 41.59% and 26.41%. Experiment 02's role-aware method records 36.47% precision and 21.69% recall, alongside 34.40% and 26.94% for its gated temporal baseline. Phase 3's import-assisted method records 17.91% precision and 28.08% recall on 352 evaluated events.

Each experiment defines its own event and candidate eligibility. Assess methods within the corresponding experiment. Ranking scores express historical evidence. Forecast scores are uncalibrated. Same-commit labels, one repository, and the absence of uncertainty estimates limit conclusions about developer benefit and generalization.
