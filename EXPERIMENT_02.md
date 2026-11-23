# Experiment 02 — Code-inspection recommendations (Phase 2)

## Simple explanation

If a developer is editing a source-code file, such as `src/flask/app.py`, should the system recommend source, test, and configuration files worth reviewing, rather than automatically treating a release-notes file as a code dependency?

This experiment tests a narrowly defined **code-inspection task**. It does not assert that documentation never matters: documentation is simply outside this particular task. The original all-files recommender remains available in the app.

## What is implemented

- **File-role detection** (`src/context_recommender.py`): filename/path rules classify `source`, `test`, `config`, `documentation`, `asset`, or `other`. This is a heuristic; it does not parse code or imports.
- **Code-only candidate set**: source, test, and config files can be recommended. The selected seed must also be in that set.
- **Fair code-only baselines**: static directional co-change confidence (`static_code`) and time-decayed confidence (`temporal_code`) run on the **same eligible candidates and same test cases** as the new method.
- **Experimental role-aware method** (`role_aware_code`): temporal co-change confidence, shrinkage for sparse evidence, plus modest boosts for files in the same directory, similarly named test/source pairs, and same-role pairs. All coefficients are fixed by design, *not fitted* or claimed optimal.
- **Explanations**: show historical joint commits and filename/path cues. Scores are relative, **not probabilities**.

This is an experimental combination of established heuristics, **not yet a demonstrated novel scientific contribution**. It does not model imports, semantic code relationships, or developer intent.

## How the evaluation was done

- Data: same Flask Git history as Experiment 01 (`data/raw/commits.csv`).
- Partition by **unique commit timestamps**: first 70% historical training, next 15% validation, final 15% held-out test.
- Predict before updating the model at each timestamp. All commits with identical timestamps are predicted before they enter history.
- In a test commit, choose one eligible source/test/config path deterministically as the known seed; other eligible files in that same commit are the weak proxy targets.
- Exclude commits larger than 20 files, just as V1 does. Commits without eligible files cannot be used for this task. Single-eligible-file commits remain and can generate false alerts.
- Maximum 3 suggestions for every method. Thresholds for **all three** methods selected using validation data only (maximize F0.5, at least 10% coverage).
- **Validation:** 506 eligible events. **Held-out test:** 623 eligible events.

## Held-out results — code-inspection task only

| Method | Precision | Recall | Coverage | False alerts/event |
|---|---:|---:|---:|---:|
| Static co-change (gated) | 31.9% | 13.4% | 34.0% | 0.401 |
| Temporal co-change (gated) | 34.4% | **26.9%** | 62.0% | 0.722 |
| Experimental role-aware temporal (gated) | **36.5%** | 21.7% | 53.0% | 0.531 |

**Interpretation:** Role-aware gained approximately 2.1 precision percentage points vs. the gated temporal baseline, but lost about 5.2 recall points. It also covered fewer events, and produced fewer false alerts. This is a **trade-off**, not evidence that the proposed algorithm is consistently better. No statistical confidence interval or significance test has been computed.

**Do not compare these numbers directly to Experiment 01.** The eligible inputs and outputs are intentionally different: Experiment 01 concerns all files, whereas Experiment 02 specifically concerns source/test/configuration inspection.

## Key limitations

1. Same-commit membership is not proof of causal dependency or need for inspection.
2. File roles are inferred from names/paths; some classifications will be wrong.
3. Same-directory and matching test names are proxies, not actual verified code dependencies.
4. Only one software project has been studied. Publication claims need broader testing and a literature comparison.
5. Selection thresholds are tuned on one validation period, and the model updates as historical commits arrive. Other time splits may yield different conclusions.
6. No confidence intervals or developer utility study yet. Fewer alerts are not necessarily fewer wasted developer minutes.
7. The saved Random Forest still predicts whether a file may change in a future window; it has **not** been integrated into Phase 2. Treat the two analyses as separate.

## Run

From the project root:

```bash
python3 src/evaluate_context.py
python3 -m unittest discover -s tests -v
python3 -m streamlit run app.py
```

The context evaluation writes `results/context/comparison.csv`, `validation_thresholds.csv`, `evaluation_summary.json` and `test_examples.json`. Open the **Phase 2 — Code-focused recommendation** section in Streamlit. Start with `src/flask/blueprints.py` (which can recommend `src/flask/app.py` in this snapshot). You can also choose `src/flask/app.py`; the system may abstain when all eligible candidate scores fall below its validation-selected threshold. The documentation file `CHANGES.rst` is never offered in this *code-inspection* task.

## What to research next

1. Document what is genuinely distinct from published file-role and change-impact recommender methods; do not assert novelty from file-extension filtering alone.
2. Add **structural evidence** from real repository source code (e.g., import edges or package/module references), and verify the source snapshots correspond to the commit time in each test event. Avoid using the latest repository structure for historical test commits.
3. Ablate each component (recency, evidence shrinkage, directory proximity, test-name matching, role alignment) against **equally gated** baselines.
4. Use multiple repositories, confidence intervals, multiple time splits, review-effort budgets, and perhaps developer feedback.
