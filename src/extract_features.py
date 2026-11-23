
import numpy as np
import pandas as pd

from pathlib import Path
try:
    from src.history_data import read_history
except ModuleNotFoundError:
    from history_data import read_history

def extract_features(input_path="data/raw/commits.csv", output_path="data/processed/features.csv"):
    df = read_history(input_path)

    HISTORY_DAYS = 90
    latest_date = df["date"].max()
    history_start = latest_date - pd.Timedelta(days=HISTORY_DAYS)

    history = df[
        (df["date"] >= history_start) &
        (df["date"] < latest_date)
    ].copy()

    rows = []

    for file, group in history.groupby("file"):
        count = len(group)

        recent_count = (
            group["date"] >= latest_date - pd.Timedelta(days=30)
        ).sum()

        days_since_last = (
            latest_date - group["date"].max()
        ).total_seconds() / 86400

        ages = (
            (latest_date - group["date"]).dt.total_seconds()
            / 86400
        )

        bins = np.minimum((ages // 30).astype(int), 2)
        counts = np.bincount(bins, minlength=3)
        probabilities = counts[counts > 0] / counts.sum()
        entropy = -np.sum(probabilities * np.log2(probabilities))

        rows.append({
            "file": file,
            "change_frequency": count,
            "change_velocity_30d": recent_count,
            "days_since_last_change": days_since_last,
            "change_entropy": entropy
        })

    features = pd.DataFrame(rows)

    if features.empty:
        raise ValueError("No files found in the 90-day history window.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    features.to_csv(
        output_path,
        index=False
    )

    print("Feature extraction successful!")
    print(features.head())
    print("Total files analyzed:", len(features))

    return features


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/raw/commits.csv')
    parser.add_argument('--output', default='data/processed/features.csv')
    args = parser.parse_args()
    try:
        extract_features(args.input, args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
