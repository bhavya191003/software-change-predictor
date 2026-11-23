# What to do next — simple project guide

## Try your updated project

1. Download/unzip the research prototype.
2. In Terminal, go to the folder containing `app.py`.
3. Run: `pip install -r requirements.txt`
4. Run: `streamlit run app.py`
5. Scroll to **Co-Change Recommendation — Experimental Research Prototype**.
6. Choose `src/flask/app.py` as the file being modified.
7. Click **Recommend related files**. The prototype may suggest `CHANGES.rst` based on historical co-changes. Its score is NOT a probability.
8. Change recommendation approach to compare the evidence used by different methods.

## Reproduce the research experiment

Run `python src/evaluate_cochange.py` from the project root. See the generated CSV/JSON reports in `results/cochange/` and explanatory notes in `EXPERIMENT_01.md`.

## Plan for the next research iteration

**Problem:** A frequently co-changing file can be release documentation (for example `CHANGES.rst`), rather than a code file that truly needs inspecting. Merely detecting historical co-changes creates noisy recommendations.

**Candidate hypothesis to evaluate, not an established novelty claim:** Use the development context (which code file is edited, whether candidates are source/test/doc files, available code dependencies, and whether candidate changes occur during release-related commits) to rank code-relevant inspections more effectively than history-only methods. Document what similar published work has already done before defining the final contribution.

**Experiment:** Implement context-aware features and test them with the same chronological replay, compare against the strong time-aware gated baseline (41.59% precision, 26.41% recall on this test), then replicate across multiple repositories. Evaluate at fixed inspection budgets and quantify missed recommendations and false alerts. Avoid cherry-picking test thresholds.

## What not to claim yet

- Do not claim novel algorithms, publication readiness, improved developer productivity, or state-of-the-art performance.
- Do not call the score a calibrated probability.
- Do not claim that recommendations identify bugs or required changes.
- Do not use testing commits to tune the method.


## Phase 2 finished as an experimental prototype

See `EXPERIMENT_02.md`. The code-focused recommender is available in the app. Its results currently show a precision/recall trade-off, not a universal improvement. Next, prioritize true dependency information from time-correct repository snapshots, fixed-budget comparison, multi-repository validation, and literature-based novelty assessment.
