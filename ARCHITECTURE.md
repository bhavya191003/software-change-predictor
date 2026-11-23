# Architecture and data reference

## Data flow

```text
Local Git clone
    -> src/collect_data.py
    -> data/raw/commits.csv
         -> src/train_change_model.py -> training_dataset.csv + change_model.pkl
         -> src/extract_features.py -> features.csv
         -> chronological replay evaluators -> results/*
         -> in-memory co-change recommenders

change_model.pkl + features.csv + raw history + selected reports -> app.py
Historical Git parent snapshots + raw history -> Phase 3 experiments
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit forecast, recommendation controls, result tables, and dataset explorer |
| `src/collect_data.py` | Traverse commits reachable from HEAD, compare against each first parent, skip root commits, and save file-change records |
| `src/extract_features.py` | Build the latest 90-day file-history snapshot |
| `src/train_change_model.py` | Generate rolling labels, split by window date, train and serialize a Random Forest |
| `src/cochange_recommender.py` | Load chronological events, maintain decayed file/pair counts, and rank all-file candidates |
| `src/context_recommender.py` | Infer file roles and rank eligible code-inspection candidates |
| `src/evaluate_cochange.py` | Replay all-file recommendations and select validation gates |
| `src/evaluate_context.py` | Replay code-focused methods and select validation gates |
| `src/extract_historical_dependencies.py` | Parse Python import relationships from a specified event's parent snapshot |
| `src/phase3_dependency_demo.py` | Compare history and import-assisted suggestions for one historical event |
| `src/evaluate_dependency_phase3.py` | Compare three methods on held-out Python-seed events |
| `src/broken_ripple.py` | Standalone rule-mining demonstration |

## Data contracts

| Artifact | Fields or contents |
|---|---|
| `data/raw/commits.csv` | `commit_id`, `date`, `file`, `change_type` |
| `data/processed/features.csv` | `file`, `change_frequency`, `change_velocity_30d`, `days_since_last_change`, `change_entropy` |
| `data/processed/training_dataset.csv` | Feature columns plus `date`, `file`, and binary `target` |
| `models/change_model.pkl` | Dictionary containing `model`, ordered `features`, `history_days`, and `future_days` |
| `results/cochange/`, `results/context/` | `comparison.csv`, `validation_thresholds.csv`, `evaluation_summary.json`, `test_examples.json` |
| `results/phase3/` | `comparison.csv`, `summary.json`, `examples.json` |

Dates are parsed as UTC. Feature and event loaders remove duplicate commit/file pairs. Paths identify files directly, so renames do not receive a persistent cross-path identity.

## Forecast features and training

At cutoff t, history covers [t minus 90 days, t). Frequency counts file commits in that interval. Velocity counts those in its final 30 days. Recency measures fractional days since the most recent change. Entropy measures the distribution of changes across three 30-day age bins using base-2 logarithms.

Training advances cutoffs by 30 days. The target is 1 when the file appears in [t, t plus 30 days), otherwise 0. Only files active in the history window get rows. The first 80% of unique window dates form training and the remainder form testing.

The classifier uses 100 trees, maximum depth 10, balanced class weights, and random seed 42. Training prints a classification report and ROC-AUC when both test classes occur. The latest feature snapshot anchors its cutoff at the maximum recorded date and excludes records exactly at that cutoff.

## Recommendation scoring

The history engine counts files and unordered pairs, with directional confidence obtained by dividing pair count by seed count. Weighted counts decay exponentially with a default 365-day half-life. Commits exceeding 20 files are skipped during updates.

- `popularity` ranks candidates by historical file count.
- `static_confidence` uses pair count divided by seed count.
- `broken_ripple` requires at least three joint commits and confidence of at least 0.5.
- `temporal_confidence` divides decayed pair support by decayed seed support.
- `selective_temporal` multiplies decayed pair support divided by decayed seed support plus 2, decayed pair support divided by itself plus 2, and a repeat factor capped at three joint commits. It requires at least two joint commits.

Context methods restrict seeds and candidates to source, test, or configuration roles. `static_code` and `temporal_code` reuse confidence features. `role_aware_code` multiplies temporal confidence by a support reliability factor and additive boosts of 0.12 for a shared directory, 0.20 for matching source/test names, and 0.08 for a shared role.

Phase 3 adds a fixed import bonus to temporal scores for candidates linked by forward or reverse imports. Candidate generation combines a bounded temporal pool and the seed's direct internal imports. Reverse imports are checked within that candidate set. Source is read using Git and parsed with Python AST.

## Application behavior

The application loads its model and feature snapshot before rendering recommendations. Missing or invalid baseline artifacts stop the page. It supports both a dictionary model artifact and a legacy bare estimator.

Recommenders are cached Streamlit resources built from the complete stored history. The all-file selective UI uses a fixed 0.25 gate. Phase 2 reads its gates from `results/context/evaluation_summary.json`. Restart Streamlit after regenerating history or model files to refresh cached resources.

## Existing checks

`tests/test_cochange_recommender.py` covers related-file ranking, self exclusion, abstention, time decay, chronological updates, and repeated evidence. `tests/test_context_recommender.py` covers role rules, documentation filtering, abstention, test-name evidence, and history updates. The suite contains ten tests. Phase 3 and the complete Streamlit workflow have no dedicated tests in this snapshot.
