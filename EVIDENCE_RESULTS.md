# Evidence-aware recommendation results

The extension was evaluated on the included Flask history using 382 validation events and 354 test events. Validation selected an import weight of 1.0 from 0, 0.1, 0.25, 0.5, 1, and 2 by F0.5. Each method returns at most three suggestions. These are ungated comparisons.

## Results

| Method | Correct suggestions | Total suggestions | Precision | Recall |
|---|---|---|---|---|
| static_code | 172 | 1044 | 16.48% | 25.52% |
| temporal_code | 194 | 1044 | 18.58% | 28.78% |
| role_aware_code | 195 | 1044 | 18.68% | 28.93% |
| evidence | 193 | 1044 | 18.49% | 28.64% |
| additive_imports | 189 | 1059 | 17.85% | 28.04% |

The revised method recovered four more target instances than the additive-import baseline and one fewer than temporal co-change. Role-aware ranking recovered 195 target instances. The revised method therefore remains an experimental candidate.

## Error analysis

| Method | Useful additions | Irrelevant additions | Useful suggestions displaced | Events helped | Events harmed |
|---|---|---|---|---|---|
| additive_imports | 21 | 204 | 26 | 12 | 15 |
| evidence | 15 | 127 | 16 | 9 | 10 |

Additions and displacements are relative to temporal ranking on the same events. An event is helped or harmed when its correct-suggestion count increases or decreases. Other events can have changed rankings without a net change in correct suggestions.

## Uncertainty

The paired 2,000-resample event bootstrap gives a 95% precision-difference interval of -0.86 to 0.76 percentage points for the revised method versus temporal ranking. Its recall-difference interval is -1.36 to 1.13 points. Both include zero.

The bootstrap assumes independent events. Sequential commits can be related, so these intervals omit temporal dependence. The result is exploratory because this repository and test period have already been inspected in earlier development.

## Eligibility and comparability

Eight test events and four validation events were skipped because their selected seeds were absent from the parent tree. Cold-start seeds present in that tree were retained. Eighteen test target instances refer to paths absent from the parent tree, which candidates cannot retrieve. They remain in the recall denominator.

The evaluator considers every historical code neighbor before filtering against the parent tree. This changes the earlier Phase 3 pool of 15 and yields a different event count. Compare the methods within this new run. The original Phase 1 and Phase 2 comparison CSVs were separately reproduced exactly.

## Artifacts and verification

- [Full summary and intervals](results/evidence/summary.json)
- [Comparison table](results/evidence/comparison.csv)
- [Per-event candidates, evidence, and predictions](results/evidence/events.json)
- [Implementation and remaining work](IMPLEMENTATION_STATUS.md)

Run `python3 src/evaluate_evidence.py --repo ../flask-source-complete` to reproduce. Run `python3 -m unittest discover -s tests -v` for the automated suite. The Streamlit page includes the comparison and a historical example selector.

## Still pending

External-repository validation is blocked by unavailable GitHub DNS in the execution environment. Fresh holdouts, repeated temporal splits, temporal block intervals, published-method comparisons, and developer usefulness assessment remain research work. A clean-environment dependency installation and visual browser inspection also remain unverified.
