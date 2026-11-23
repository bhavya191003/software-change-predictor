
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

from pathlib import Path
try:
    from src.history_data import read_history
except ModuleNotFoundError:
    from history_data import read_history

def train_model(input_path="data/raw/commits.csv", model_path="models/change_model.pkl", dataset_path="data/processed/training_dataset.csv"):
    # Load historical changes
    df = read_history(input_path)

    HISTORY_DAYS = 90
    FUTURE_DAYS = 30
    STEP_DAYS = 30

    start = df["date"].min() + pd.Timedelta(days=HISTORY_DAYS)
    end = df["date"].max() - pd.Timedelta(days=FUTURE_DAYS)

    rows = []
    current = start

    while current <= end:
        history_start = current - pd.Timedelta(days=HISTORY_DAYS)
        future_end = current + pd.Timedelta(days=FUTURE_DAYS)

        history = df[
            (df["date"] >= history_start) &
            (df["date"] < current)
        ]

        future = df[
            (df["date"] >= current) &
            (df["date"] < future_end)
        ]

        future_files = set(future["file"])

        for file, group in history.groupby("file"):
            count = len(group)

            # Changes during the most recent 30 days
            recent_count = (
                group["date"] >= current - pd.Timedelta(days=30)
            ).sum()

            # Days since last change
            days_since_last = (
                current - group["date"].max()
            ).total_seconds() / 86400

            # Entropy across the 3 historical 30-day periods
            ages = (
                (current - group["date"]).dt.total_seconds()
                / 86400
            )

            bins = np.minimum((ages // 30).astype(int), 2)
            counts = np.bincount(bins, minlength=3)
            probabilities = counts[counts > 0] / counts.sum()
            entropy = -np.sum(
                probabilities * np.log2(probabilities)
            )

            rows.append({
                "date": current,
                "file": file,
                "change_frequency": count,
                "change_velocity_30d": recent_count,
                "days_since_last_change": days_since_last,
                "change_entropy": entropy,
                "target": int(file in future_files)
            })

        current += pd.Timedelta(days=STEP_DAYS)

    dataset = pd.DataFrame(rows)


    if dataset.empty:
        raise ValueError("Not enough historical data to train.")

    if dataset['date'].nunique() < 2:
        raise ValueError('Training requires at least two time windows')

    # Split chronologically, not randomly
    dates = sorted(dataset["date"].unique())
    split_date = dates[int(len(dates) * 0.8)]

    train = dataset[dataset["date"] < split_date]
    test = dataset[dataset["date"] >= split_date]

    features = [
        "change_frequency",
        "change_velocity_30d",
        "days_since_last_change",
        "change_entropy"
    ]

    X_train = train[features]
    y_train = train["target"]

    X_test = test[features]
    y_test = test["target"]

    if y_train.nunique() < 2:
        raise ValueError("Training data needs both target classes.")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("\nMODEL TRAINING COMPLETED!")
    print("\nClassification Report:")
    print(classification_report(
        y_test, predictions, zero_division=0
    ))

    if y_test.nunique() == 2:
        probabilities = model.predict_proba(X_test)[:, 1]
        print("ROC-AUC:", roc_auc_score(
            y_test, probabilities
        ))

    # Save model and feature names
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(dataset_path).parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(dataset_path, index=False)

    joblib.dump({
        "model": model,
        "features": features,
        "history_days": HISTORY_DAYS,
        "future_days": FUTURE_DAYS
    }, model_path)

    print("\nModel saved to", model_path)
    print("Training examples:", len(train))
    print("Testing examples:", len(test))

    return model, dataset


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/raw/commits.csv')
    parser.add_argument('--model', default='models/change_model.pkl')
    parser.add_argument('--dataset', default='data/processed/training_dataset.csv')
    args = parser.parse_args()
    try:
        train_model(args.input, args.model, args.dataset)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
