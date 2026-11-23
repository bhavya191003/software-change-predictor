# Setup and experiment reproduction

Run commands from the directory containing `app.py`. Use Python 3.10 or newer for the source syntax and a Git installation for repository collection and Phase 3. Dependencies in `requirements.txt` have no version pins.

## Install and start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The supplied model and datasets allow the application to use the included snapshot immediately. Select a historical file and use **Analyze File** for the forecast. The co-change and Phase 2 sections provide related-file inspection suggestions. The dataset explorer displays the included CSVs.

## Regenerate the forecast artifacts

```bash
python3 src/train_change_model.py
python3 src/extract_features.py
```

These commands replace the processed training dataset, serialized model, and feature snapshot. Training needs enough history for 90-day inputs and 30-day labels, multiple cutoff dates, and both target classes in training.

To replace the raw history with data from another local clone, run the following first. Substitute the repository path.

```bash
python3 src/collect_data.py /path/to/local/git/repository
```

Collection overwrites `data/raw/commits.csv`. Regenerate model, features, and evaluation reports together after changing its source repository.

## Reproduce Phase 1 and Phase 2

```bash
python3 src/evaluate_cochange.py
python3 src/evaluate_context.py
python3 -m unittest discover -s tests -v
```

Evaluation replaces the corresponding files under `results/cochange/` and `results/context/`. Both scripts accept `--input` and `--output` to use separate datasets or report directories. The co-change evaluator also accepts `--half-life-days`, `--top-k`, and `--max-commit-files`.

## Reproduce Phase 3

A local clone containing the commits referenced by the CSV and their parent trees is required. The stored result used a clone recorded as `../flask-source-complete`. Substitute your actual clone path.

Run a default sample of up to 40 eligible events first.

```bash
python3 src/evaluate_dependency_phase3.py --repo /path/to/flask-clone
```

The saved report selected all 362 eligible events with a maximum of three recommendations, pool size 15, and bonus 0.2. Reproduce those settings with the matching history.

```bash
python3 src/evaluate_dependency_phase3.py \
  --repo /path/to/flask-clone \
  --max-events 0 --top-k 3 --pool-size 15 --dependency-bonus 0.2
```

Use `--output` to preserve the supplied Phase 3 reports. Full replay reads many historical Git objects and can take time.

Inspect one event using the example commit referenced by the scripts.

```bash
python3 src/extract_historical_dependencies.py \
  --repo /path/to/flask-clone \
  --event-commit bfc8f983871dcadf0492578d9ab72d951b34c19c \
  --file src/flask/app.py

python3 src/phase3_dependency_demo.py \
  --repo /path/to/flask-clone \
  --event-commit bfc8f983871dcadf0492578d9ab72d951b34c19c \
  --file src/flask/app.py
```

## Resolve common startup issues

| Symptom | Action |
|---|---|
| Missing model or incompatible serialized estimator | Install dependencies and regenerate the model in that environment |
| Missing features or required columns | Regenerate features from the intended raw history |
| Missing validation-selected Phase 2 threshold | Run `src/evaluate_context.py` |
| Git cannot resolve an event or parent | Use a clone containing the CSV's historical commits and parents |
| Seed absent in the parent snapshot | Choose an existing historical Python file or review the evaluator's skipped-event report |
| Updated artifacts do not appear in the app | Restart Streamlit to reload cached resources |

Dependency versions and the original training environment are unrecorded, so installing current packages can change artifact compatibility or regenerated results.

## Evidence-aware extension

```bash
python3 src/evaluate_evidence.py --repo /path/to/flask-clone
```

The evaluator selects its import weight on validation history and writes comparisons, per-event evidence, diagnostics, and paired bootstrap intervals under `results/evidence/`. The Streamlit application displays the generated evaluation and historical examples. See [EVIDENCE_RESULTS.md](EVIDENCE_RESULTS.md) for measured results and [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for remaining work.

`requirements-verified.txt` records the direct package versions used for verification. It can be installed with `python3 -m pip install -r requirements-verified.txt`. A clean installation using those pins has not been verified.
