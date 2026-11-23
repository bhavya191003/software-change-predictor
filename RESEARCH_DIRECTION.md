# Possible Research Direction (Proposal — Not a Novelty Claim)

## Problem
A developer edits a group of files but wants a short, justified list of other files worth inspecting for accompanying or delayed changes. Full-repository manual inspection is expensive; a generic yes/no future-file-change prediction does not directly answer this question.

## Proposed study
Compare (A) independent change propensity estimated from prior Git history, (B) directional co-change rules, and (C) an integrated, time-aware, explainable **top-K file recommendation** system triggered by a real incoming change. Consider evaluating one additional specific component, such as calibrated uncertainty gating or effort-aware recommendation budgets, after checking the literature.

## Inputs and truth
- At each cutoff `t`: only history **strictly before t**, and the files actually modified by the initiating commit or review.
- Recommend candidate *other* files to inspect.
- Clearly define ground truth, e.g. whether candidates are changed during the same completed work item or a carefully defined subsequent horizon. These are different targets; do not mix them.
- Handle file renames, inactive files, large mechanical commits, and dependencies carefully.

## Evaluation
- Use multiple repositories and rolling chronological splits, with a separate validation period for all tuning.
- Compare against frequency-only, recency-only, top co-change confidence, logistic regression, Random Forest propensity alone, and existing recommendation approaches when feasible.
- Report Precision@K, Recall@K, MRR/NDCG, coverage, and inspections per true related file. If claiming probabilities, additionally measure Brier score and calibration plots.
- Include ablations and confidence intervals/uncertainty, and report negative results.

## Literature to investigate before asserting originality
- FCP2Vec, Applied Sciences (2023): https://www.mdpi.com/2076-3417/13/11/6453
- Temporal graphs for change propagation, Information and Software Technology (2024): https://www.sciencedirect.com/science/article/pii/S0950584923002239
- Predicting co-change probability using historical metadata, IET Software (2020): https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/iet-sen.2019.0368
- Software change-proneness prediction based on deep learning, Scientific Reports (2026): https://www.nature.com/articles/s41598-026-64123-5

Novelty and publication suitability must be determined by a fuller systematic related-work review and a credible empirical contribution, not by combining already known techniques or changing the project title.
