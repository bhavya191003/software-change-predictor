"""
ML Prediction Engine — Software Change Predictor
Uses Random Forest to predict future defect risk from current metrics.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, Any, Optional
from .utils import setup_logger
from . import config

logger = setup_logger("predictor")

FEATURES = ['commit_frequency', 'velocity', 'total_churn', 'author_count', 'entropy', 'bug_ratio']
CATEGORY_MAP = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0}
REVERSE_MAP = {0: 'Low', 1: 'Medium', 2: 'High', 3: 'Critical'}


def train_risk_model(metrics_df: pd.DataFrame) -> Optional[RandomForestClassifier]:
    """
    Train a Random Forest classifier on the risk data.
    Returns None if there's not enough data or diversity to train.
    """
    if metrics_df.empty or len(metrics_df) < 5:
        logger.info("Not enough data to train ML model (need >= 5 files)")
        return None

    X = metrics_df[FEATURES].fillna(0)
    y = metrics_df['risk_category'].map(CATEGORY_MAP).fillna(0).astype(int)

    # Need at least 2 distinct classes to train a meaningful model
    unique_classes = y.nunique()
    if unique_classes < 2:
        logger.info(f"Only {unique_classes} risk class found — skipping ML training")
        return None

    logger.info(f"Training Random Forest on {len(X)} samples, {unique_classes} classes")

    model = RandomForestClassifier(
        n_estimators=config.ML_CONFIG['n_estimators'],
        random_state=config.ML_CONFIG['random_state']
    )
    model.fit(X, y)
    return model


def predict_future_risk(model: RandomForestClassifier, current_metrics: pd.Series) -> Dict[str, Any]:
    """Predict future risk for a single file using the trained model."""
    if model is None:
        return {'predicted_risk': 0.0, 'confidence': 0.0}

    X = pd.DataFrame([current_metrics[FEATURES].apply(pd.to_numeric, errors='coerce').fillna(0)])

    pred_class = int(model.predict(X)[0])
    prob = model.predict_proba(X)[0]

    # Map the predicted class back to a 0-1 risk score
    predicted_risk_score = pred_class / 3.0

    # Get the confidence for the predicted class
    # model.classes_ tells us which index corresponds to which class
    class_list = list(model.classes_)
    if pred_class in class_list:
        confidence = float(prob[class_list.index(pred_class)])
    else:
        confidence = 0.0

    return {
        'predicted_risk': predicted_risk_score,
        'confidence': confidence
    }


def calculate_trend(historical_velocity: float, current_velocity: float) -> str:
    """Determine if risk is increasing, decreasing, or stable based on velocity change."""
    if current_velocity == 0 and historical_velocity == 0:
        return "Stable"
    diff = current_velocity - historical_velocity
    threshold = max(0.1, current_velocity * 0.1)  # 10% relative threshold
    if diff > threshold:
        return "Increasing"
    elif diff < -threshold:
        return "Decreasing"
    return "Stable"


def generate_predictions(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Full prediction pipeline:
    1. Train a model on the current risk data
    2. Predict future risk for each file
    3. Calculate trend direction
    """
    logger.info("Generating future risk predictions...")
    if metrics_df.empty:
        return pd.DataFrame(columns=['file_path', 'predicted_risk', 'trend', 'confidence'])

    model = train_risk_model(metrics_df)

    predictions = []
    for _, row in metrics_df.iterrows():
        pred = predict_future_risk(model, row)
        # Compare current velocity against 80% of current (simulated historical)
        trend = calculate_trend(row['velocity'] * 0.8, row['velocity'])

        predictions.append({
            'file_path': row['file_path'],
            'predicted_risk': pred['predicted_risk'],
            'trend': trend,
            'confidence': pred['confidence']
        })

    return pd.DataFrame(predictions)
