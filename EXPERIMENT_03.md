# Experiment 03 — Historical import-assisted recommendations

## Question and implementation

Does adding direct Python import evidence improve time-aware co-change ranking for code inspection?

`src/evaluate_dependency_phase3.py` compares `temporal_code`, `role_aware_code`, and `history_plus_imports`. It reads each event's first-parent source tree, resolves internal Python imports, and adds a fixed 0.2 bonus where a forward or reverse import links a candidate to the seed. The temporal candidate pool has size 15. Direct imports can introduce additional candidates.

## Evaluation design

The test period starts at Unix timestamp 1656691552, selected at the 85% boundary of distinct historical timestamps. Each eligible event contains at most 20 files and has an eligible Python seed. The seed is selected deterministically from the commit ID. Targets are the other source, test, and configuration paths in that commit.

Predictions use earlier timestamp batches. History updates after all predictions for a timestamp. Earlier test events therefore become history for later events. Source relationships come from the event parent. All methods have a maximum of three suggestions and use zero score gates.

The supplied report selected all 362 eligible held-out events and evaluated 352. Six events lacked prior seed history and four seeds were absent from the parent tree. These ten events were skipped. The evaluated events contain 673 target file instances.

## Stored results

| Method | Correct / total suggestions | Precision | Recall | Coverage | False alerts / event |
|---|---|---|---|---|---|
| Temporal code | 194 / 1,044 | 18.58% | 28.83% | 99.43% | 2.4148 |
| Role-aware code | 195 / 1,044 | 18.68% | 28.97% | 99.43% | 2.4119 |
| History plus imports | 189 / 1,055 | 17.91% | 28.08% | 100.00% | 2.4602 |

Source artifacts are [summary.json](results/phase3/summary.json) and [comparison.csv](results/phase3/comparison.csv). [examples.json](results/phase3/examples.json) contains the first 25 evaluated records.

The import-assisted method produced fewer correct suggestions and more false alerts than both comparison methods on these events. The small role-aware advantage over temporal ranking has no reported uncertainty estimate. The methods share a maximum inspection budget, with slightly different realized recommendation totals.

## Metric definitions

Precision divides correct suggestions by all suggestions. Recall divides correct suggestions by all target file instances. Coverage measures the fraction of evaluated events receiving a suggestion. False alerts per event divides incorrect suggestions by the event count. Hit rate in the JSON report measures events with a correct suggestion among events having at least one target.

## Interpretation limits

Same-commit membership supplies a proxy for inspection relevance. Static imports omit dynamic and call-level relationships and can add irrelevant candidates. Reverse-import discovery is bounded by the candidate pool. Filtering candidates against the parent tree excludes paths introduced by the event, while such paths can still occur in the target labels.

The experiment uses one repository and Python seeds, skips cold-start events, and reports no confidence intervals. Its ungated evaluation and event selection differ from Phase 2's gated 623-event task. The saved report retains generic wording about a small sampled pilot, although its counts show that this run selected all 362 eligible events.

These results document the stored experiment. Reproduction requires the matching Git history clone. See [RUNNING.md](RUNNING.md) for commands.
