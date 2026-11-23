# Experiment 01 — Co-change recommendation prototype (November 2026)

## Research question

If a developer modifies one file in a software project, can Git history identify **other files worth inspecting**, without overwhelming developers with false recommendations?

This is **software change recommendation**, not defect prediction. Co-occurrence in a Git commit is a proxy for related work, not proof that another file needed modification.

## Methods under comparison

1. **Popularity:** recommend historically most frequently changed files.
2. **Static confidence:** co-change count with the chosen file divided by commit count for that file.
3. **Existing Broken Ripple:** at least three historical co-changes and static confidence at least 0.5.
4. **Temporal confidence:** recent history counts more; a commit loses half its weight every 365 days.
5. **Selective temporal prototype:** time-decayed pair evidence, shrinkage of weak pair histories, repeated-evidence weighting, and no recommendation below a validation-selected threshold.
6. **Fair gated baselines:** ordinary static or temporal confidence with an abstention threshold tuned on exactly the same validation set.

The fifth method is a research **candidate** assembled from known techniques, not an established original scientific result.

## Evaluation design

- Dataset: `data/raw/commits.csv` (5,549 original commits, Flask Git history).
- Split by **unique commit timestamps**: first 70% used as initial history, next 15% as validation, final 15% as test.
- Chronological replay: before each commit timestamp, recommend using only **earlier** events. Update history only after all commits sharing the same timestamp have been evaluated.
- Use a deterministic single file from each commit as known input. The other same-commit files are the *observed proxy* targets.
- Skip commits with more than 20 changed files (82 excluded from model updates); this avoids letting bulk commits dominate pair counts. Single-file commits are retained, and if a method recommends other files for one, those recommendations count as false alerts.
- `top_k=3`. Fit/select thresholds on validation only by maximizing F0.5 with at least 10% recommendation coverage. Do not change test thresholds to improve published numbers.
- Validation events: 843. Test events: 815. Ground-truth other-file instances in test: 1,882.

## Held-out test results

| Method | Precision | Recall | Coverage (events with >=1 suggestion) | False alerts / event |
|---|---:|---:|---:|---:|
| Popularity | 7.27% | 9.30% | 98.4% | 2.737 |
| Static co-change | 24.24% | 30.71% | 98.0% | 2.216 |
| Broken Ripple | 47.89% | 16.26% | 44.8% | 0.409 |
| Temporal confidence | 26.76% | 33.90% | 98.0% | 2.142 |
| Selective temporal (proposed candidate) | 41.47% | 24.28% | 66.9% | 0.791 |
| Static confidence with tuned gate | 40.89% | 23.38% | 65.5% | 0.780 |
| Temporal confidence with tuned gate | 41.59% | 26.41% | 71.8% | 0.856 |

**Interpretation:** The selective method is markedly more precise than recommending three temporal candidates indiscriminately, but it does **not** beat the fairly thresholded temporal baseline for precision or recall. The stronger claim "our new method outperforms existing methods" is **not supported**. Also, Broken Ripple has the highest precision but covers fewer events and recovers fewer related files.

## Limitations

- Only one repository; results may not generalize.
- Single-file / large commits, renames, bots, squashed commits, and coding conventions may affect measured relationships.
- Same-commit presence is not equivalent to real required inspection or developer time saved.
- Scores are **ranking measures**, not calibrated probabilities or percentages of correctness.
- The prototype does not incorporate actual code edits or current dependency structure.
- Confidence intervals and statistical significance are not yet reported; do not describe small differences as real improvements.
- Real-world use requires freshness checks and new Git history.

## Next research steps (before a paper)

1. **Literature map:** compare problem setting, datasets, methods, and known limitations of published co-change recommendation and change impact analysis.
2. **Find a genuinely differentiated contribution:** e.g. investigate context-conditioned co-change ranking, dependency-aware evidence, or explicit review-effort budgeting. This requires comparison with nearest prior methods, not a claim that reweighting known scores is automatically novel.
3. **Add repositories:** evaluate across at least three diverse open-source projects with chronological splits, without tuning hyperparameters on test histories.
4. **Strong baselines and ablation:** compare with static/dynamic rule mining, time-aware confidence with abstention, popularity, and individual components removed.
5. **Quantify trade-offs:** precision/recall at fixed review budget, alerts per commit, coverage, and statistical uncertainty; consider a small blinded developer assessment if feasible.
6. **Then** write the research question, hypothesis, contributions, threats to validity, and a paper that reports *all* results including failures.

## Reproduce the experiment

From the project root:

```bash
pip install -r requirements.txt
python src/evaluate_cochange.py
streamlit run app.py
```

Generated reports: `results/cochange/comparison.csv`, `validation_thresholds.csv`, `evaluation_summary.json`, and `test_examples.json`.
