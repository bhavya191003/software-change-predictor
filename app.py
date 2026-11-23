import os
import numpy as np
import joblib
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Software Change Predictor",
    layout="wide"
)

st.title("Software Change Predictor")
st.write(
    "Use Git history to recommend related files for developers to inspect "
    "and explore a baseline forecast of future file changes."
)

@st.cache_resource
def load_model():
    artifact = joblib.load("models/change_model.pkl")

    if isinstance(artifact, dict):
        model = artifact["model"]
        features = artifact.get("features", [
            "change_frequency",
            "change_velocity_30d",
            "days_since_last_change",
            "change_entropy"
        ])
        future_days = artifact.get("future_days", 30)
    else:
        model = artifact
        features = [
            "change_frequency",
            "change_velocity_30d",
            "days_since_last_change",
            "change_entropy"
        ]
        future_days = 30

    if not callable(getattr(model, "predict", None)):
        raise ValueError("Model artifact has no prediction method")
    if not isinstance(features, (list, tuple)) or not features or not all(isinstance(f, str) for f in features):
        raise ValueError("Model feature names must be a nonempty list")
    return model, list(features), future_days


try:
    model, features, future_days = load_model()
except Exception as error:
    st.error(f"Unable to load Change Prediction model: {error}")
    st.stop()


path = "data/processed/features.csv"

if not os.path.exists(path):
    st.error("Feature dataset not found.")
    st.stop()

try:
    df = pd.read_csv(path)
except (OSError, ValueError) as error:
    st.error(f"Unable to read feature dataset: {error}")
    st.stop()

required_columns = ["file"] + features

if any(col not in df.columns for col in required_columns):
    st.error("The feature dataset is missing required columns.")
    st.stop()

numeric_features = df[features].apply(pd.to_numeric, errors="coerce")
if not np.isfinite(numeric_features.to_numpy(dtype=float)).all():
    st.error("Feature dataset contains invalid or non-finite values. Regenerate the features.")
    st.stop()
files = df["file"].dropna().unique().tolist()

if not files:
    st.warning("No historical files available.")
    st.stop()


# Show the cutoff of the supplied history before any analysis controls.
snapshot_date = None
try:
    from src.history_data import read_history
    snapshot_history = read_history("data/raw/commits.csv")
    snapshot_date = snapshot_history["date"].max()
    st.info(
        f"Historical demo · included history ends {snapshot_date:%d %B %Y} (UTC). "
        "File paths refer to the analyzed repository's history, not this application's source files."
    )
except (OSError, ValueError) as error:
    st.warning(f"Unable to determine the historical snapshot date: {error}")
st.write(
    "**Start here:** choose a source, test, or configuration file you are editing, "
    "then request up to three related files to inspect. Explore historical evidence "
    "and comparison results below."
)
st.caption(
    "The supplied demo uses Flask history. It does not monitor a new commit or analyze "
    "an uploaded repository. Forecasting and recommendation methods run independently."
)

st.divider()
st.subheader("Related files to inspect — code, tests and configuration")
st.write(
    "Choose a source, test, or configuration file. This mode recommends only "
    "source/test/configuration files, rather than general documents or assets. "
    "This interactive mode uses file names, file roles and Git history. "
    "Historical Python import evidence is explored separately below."
)

try:
    import json
    from src.context_recommender import ContextRecommender, file_role, is_code_inspection_file
    @st.cache_resource
    def load_context_recommender():
        from src.cochange_recommender import load_commit_history
        context_history = load_commit_history("data/raw/commits.csv")
        cmodel = ContextRecommender(half_life_days=365, max_commit_files=20)
        for item in context_history:
            cmodel.observe(item["files"], item["timestamp"])
        return cmodel, context_history

    context_model, context_history = load_context_recommender()
    context_files = sorted(f for f in context_model.files if is_code_inspection_file(f))
    if context_files:
        context_default = context_files.index("src/flask/blueprints.py") if "src/flask/blueprints.py" in context_files else 0
        context_file = st.selectbox("File being edited (code-inspection task)", context_files,
                                    index=context_default, key="context_file")
        mode_labels = {
            "Role-aware temporal (experimental)": "role_aware_code",
            "Time-aware (fair baseline)": "temporal_code",
            "Static co-change (fair baseline)": "static_code",
        }
        selected_mode = st.selectbox("Code-inspection approach", tuple(mode_labels), key="context_mode")
        selected_method = mode_labels[selected_mode]
        context_report = "results/context/evaluation_summary.json"
        gates = {}
        if os.path.exists(context_report):
            with open(context_report, encoding="utf-8") as research_file:
                gates = json.load(research_file).get("thresholds_tuned_on_validation_only", {})
        if st.button("Recommend code-related files", type="primary", key="context_recommend"):
            if selected_method not in gates:
                st.warning("No validation-selected threshold found. Run python3 src/evaluate_context.py first.")
            else:
                candidate_recs = context_model.recommend_code(
                    context_file, context_history[-1]["timestamp"],
                    method=selected_method, top_k=3, threshold=gates[selected_method]
                )
                if not candidate_recs:
                    st.info("Not enough evidence to recommend a code/test/configuration file for this selection.")
                for idx, rec in enumerate(candidate_recs, start=1):
                    st.markdown(f"**{idx}. `{rec['file']}` — {rec['role']}**")
                    st.caption(rec['reason'])
                    st.write(f"Relative ranking score: {rec['score']:.3f} (not a probability)")
        st.caption(
            "The live example uses the entire supplied commit history. It is NOT an "
            "out-of-sample prediction. Test statistics below come from chronological "
            "historical replay and use same-commit code files as weak proxy labels."
        )
        with st.expander("Phase 2 — results on unseen historical code commits"):
            context_table = "results/context/comparison.csv"
            if os.path.exists(context_table):
                context_df = pd.read_csv(context_table)
                test_df = context_df[context_df['phase'] == 'test']
                shown = ['method', 'precision', 'recall', 'coverage', 'false_alerts_per_event']
                st.dataframe(test_df[shown], width="stretch", hide_index=True)
                st.caption(
                    "Only code/test/config candidates and target labels are included. "
                    "These numbers cannot be directly compared with V1's all-file task. "
                    "Improved precision with worse recall does NOT show overall superiority."
                )
            else:
                st.info("Run python3 src/evaluate_context.py to generate the Phase 2 results.")
    else:
        st.warning("No eligible source, test, or configuration files were found.")
except Exception as context_error:
    st.warning(f"Unable to display Phase 2: {context_error}")

st.divider()
st.subheader("Historical import evidence — examples and evaluation")
try:
    evidence_summary = "results/evidence/summary.json"
    if os.path.exists(evidence_summary):
        import json
        with open(evidence_summary, encoding="utf-8") as evidence_file:
            evidence_results = json.load(evidence_file)
        st.caption(
            f"Historical evaluation across {evidence_results['test_events']} events. "
            "Recommendations use history and source snapshots preceding each event."
        )
        st.write(
            "These are saved historical replay results, not analysis of the file selected above. "
            "Each method recommends at most three files per event, without a score gate in this comparison."
        )
        reports = pd.DataFrame(evidence_results["reports"])
        st.dataframe(reports, width="stretch", hide_index=True)
        precision_by_method = reports.set_index("method")["precision"]
        if all(name in precision_by_method for name in ("evidence", "temporal_code", "role_aware_code")):
            st.info(
                f"Evidence-aware precision: {precision_by_method['evidence']:.2%}; "
                f"temporal: {precision_by_method['temporal_code']:.2%}; "
                f"role-aware: {precision_by_method['role_aware_code']:.2%}. "
                "The evidence-aware method has not established an improvement over these baselines."
            )
        st.caption(
            "Evaluation uses one repository and same-commit files as proxy labels. "
            "The saved precision and recall difference intervals versus temporal ranking include zero. "
            "Generalization and developer usefulness remain unverified. "
            "Different experiment scopes and score gates mean their percentages should not be compared directly."
        )
        st.caption("Same-commit files provide proxy labels. Scores are relative ranking evidence.")
        events_path = "results/evidence/events.json"
        if os.path.exists(events_path):
            with open(events_path, encoding="utf-8") as events_file:
                evidence_events = json.load(events_file)
            if evidence_events:
                example_index = st.selectbox(
                    "Historical recommendation example", range(len(evidence_events)),
                    format_func=lambda i: f"{evidence_events[i]['seed']} ({evidence_events[i]['commit'][:8]})",
                    key="evidence_example")
                example = evidence_events[example_index]
                from src.evidence_recommender import rank_evidence
                suggestions = rank_evidence(
                    example["candidates"],
                    import_weight=evidence_results["selected_import_weight"],
                    top_k=evidence_results["top_k"])
                for suggestion in suggestions:
                    st.write(suggestion["file"])
                    st.caption(suggestion["reason"])
                if not suggestions:
                    st.info("No supported recommendation for this historical event.")
                with st.expander("Observed accompanying changes"):
                    st.write(example["targets"])
    else:
        st.info("Run python3 src/evaluate_evidence.py --repo /path/to/history-clone to generate evidence results.")
except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
    st.warning(f"Unable to read evidence results: {error}")



st.divider()
st.subheader("Additional experiment — all-file co-change recommendations")
st.write(
    "Select a file that a developer is already editing. The prototype analyzes "
    "older Git commits and recommends up to three other files worth inspecting. "
    "A recommendation is not proof that another file requires modification."
)

@st.cache_resource
def load_recommender():
    from src.cochange_recommender import CochangeRecommender, load_commit_history
    history = load_commit_history("data/raw/commits.csv")
    researcher = CochangeRecommender(half_life_days=365, max_commit_files=20)
    for event in history:
        researcher.observe(event["files"], event["timestamp"])
    return researcher, history

try:
    recommender, history = load_recommender()
    selectable_files = sorted(recommender.files)
    if selectable_files:
        seed_file = st.selectbox(
            "File the developer has modified", selectable_files, key="research_seed_file"
        )
        approach = st.selectbox(
            "Recommendation approach",
            ("Selective time-aware (research prototype)",
             "Traditional historical co-change",
             "Time-aware co-change",
             "Broken Ripple rules"),
            key="research_method"
        )
        method_map = {
            "Selective time-aware (research prototype)": "selective_temporal",
            "Traditional historical co-change": "static_confidence",
            "Time-aware co-change": "temporal_confidence",
            "Broken Ripple rules": "broken_ripple",
        }
        approach_method = method_map[approach]
        # The selective threshold was selected using the historical validation period.
        # Baselines can also be gated: see src/evaluate_cochange.py.
        threshold = 0.25 if approach_method == "selective_temporal" else 0.0
        if st.button("Recommend related files", type="primary", key="research_run"):
            findings = recommender.recommend(
                seed_file, history[-1]["timestamp"],
                method=approach_method, top_k=3, threshold=threshold,
            )
            if not findings:
                st.info("Not enough historical evidence to recommend another file for this input.")
            else:
                st.write(f"Suggested inspections for **{seed_file}**:")
                for number, finding in enumerate(findings, 1):
                    st.markdown(f"**{number}. `{finding['file']}`**")
                    st.caption(finding["reason"])
                    st.write(f"Relative model score: {finding['score']:.3f} (not a probability)")
                st.caption(
                    "These suggestions use all commits in the supplied Git snapshot. "
                    "They are for demonstration, NOT out-of-sample evaluation results."
                )
        st.caption(
            "For reproducible, leakage-aware evaluation on held-out commits, "
            "run: python src/evaluate_cochange.py. The selective threshold was "
            "selected on validation data, not test data."
        )
    else:
        st.info("No suitable historical files found for co-change analysis.")
except Exception as exc:
    st.warning(f"Unable to load experimental co-change component: {exc}")

st.divider()
try:
    with st.expander("Research results — unseen historical commits"):
        research_csv = "results/cochange/comparison.csv"
        if os.path.exists(research_csv):
            scores_df = pd.read_csv(research_csv)
            display = scores_df[scores_df["phase"] == "test"].copy()
            columns = ["method", "precision", "recall", "coverage", "false_alerts_per_event"]
            st.dataframe(display[columns], width="stretch", hide_index=True)
            st.caption(
                "Results are from held-out Git commits, using same-commit files as a proxy for "
                "relatedness. A selective approach has NOT yet shown consistent improvement "
                "over a thresholded time-aware baseline."
            )
        else:
            st.info("To generate results, run python src/evaluate_cochange.py")
except (OSError, ValueError, KeyError) as error:
    st.warning(f"Unable to read co-change results: {error}")

st.divider()
st.subheader("Baseline — historical file-change forecast")

if snapshot_date is not None:
    st.caption(
        f"Forecast cutoff: {snapshot_date:%d %B %Y} (UTC). "
        f"Window ends {snapshot_date + pd.Timedelta(days=future_days):%d %B %Y} (UTC). "
        "This is a historical baseline; the window does not start today."
    )
selected_file = st.selectbox(
    "Choose a software file to analyze",
    files, key="forecast_file"
)

file_data = df[df["file"] == selected_file].iloc[0]

X = pd.DataFrame(
    [file_data[features]],
    columns=features
)

X = X.apply(pd.to_numeric, errors="coerce").fillna(0)

st.subheader("Features from the included 90-day history window")
st.write(f"Selected File: **{selected_file}**")
st.dataframe(X, width="stretch")


if st.button("Analyze File", type="primary"):

    st.divider()
    st.subheader("Change Prediction Results")

    try:
        model_features = list(
            getattr(model, "feature_names_in_", features)
        )

        missing_features = [
            feature for feature in model_features
            if feature not in X.columns
        ]

        if missing_features:
            st.error(
                f"Missing model features: {missing_features}"
            )
            st.stop()

        model_input = X.reindex(columns=model_features)

        prediction = model.predict(model_input)[0]

        if prediction == 1:
            st.success(
                f"This file is predicted to change "
                f"during the {future_days}-day window after the included snapshot."
            )
        else:
            st.info(
                f"This file is not predicted to change "
                f"during the {future_days}-day window after the included snapshot."
            )

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(model_input)[0]
            classes = list(model.classes_)

            if 1 in classes:
                change_probability = probabilities[
                    classes.index(1)
                ]

                st.metric(
                    "Model change score (uncalibrated)",
                    f"{change_probability:.2%}"
                )

        st.caption(
            "The percentage is an uncalibrated Random Forest score, "
            "not a verified real-world probability. The forecast "
            "window starts at the Git history snapshot date, not "
            "automatically at today's date."
        )

    except Exception as error:
        st.error(f"Prediction error: {error}")

st.divider()
st.subheader("Project Datasets Explorer")

tab1, tab2, tab3 = st.tabs([
    "Labeled ML Training Dataset",
    "Raw Git Commits (commits.csv)",
    "Latest included historical snapshot (features.csv)"
])

def read_preview(path):
    try:
        return pd.read_csv(path)
    except (OSError, ValueError) as error:
        st.warning(f"Unable to read dataset {path}: {error}")
        return pd.DataFrame()


with tab1:
    train_path = "data/processed/training_dataset.csv"
    if os.path.exists(train_path):
        train_df = read_preview(train_path)
        st.write(f"Total Labeled Observations: **{len(train_df)}** rows (split chronologically by time-window date)")
        st.caption("Each row is one file at one historical cutoff, not a distinct file or commit. Preview shows the first 500 rows.")
        st.dataframe(train_df.head(500), width="stretch")
    else:
        st.info("Run python3 src/train_change_model.py to generate training_dataset.csv.")

with tab2:
    raw_path = "data/raw/commits.csv"
    if os.path.exists(raw_path):
        raw_df = read_preview(raw_path)
        st.write(f"Total Raw Commit Records: *{len(raw_df)}* rows from pallets/flask repository")
        st.dataframe(raw_df.head(500), width="stretch")

with tab3:
    st.write(f"Files active in the included 90-day history window: *{len(df)}* files")
    st.dataframe(df, width="stretch")


st.divider()

st.subheader("About This Project")

st.write(
    "This research prototype studies which related files a developer should inspect "
    "when modifying a file. It compares temporal co-change, file-role and historical "
    "Python import evidence using Flask Git history. A separate Random Forest baseline "
    f"forecasts file activity over {future_days} days after the included snapshot. "
    "Recommendations support inspection; they do not establish required changes or defects."
)
