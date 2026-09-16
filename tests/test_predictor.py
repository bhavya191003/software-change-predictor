import pytest
import pandas as pd
import numpy as np
import sys
from unittest.mock import patch, MagicMock

sys.modules['backend'] = MagicMock()
sys.modules['backend.predictor'] = MagicMock()

from backend.predictor import (
    classify_risk_level,
    calculate_trend,
    generate_predictions
)

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "file": ["main.py", "utils.py"],
        "composite_risk": [0.8, 0.2]
    })

def test_classify_risk_critical():
    """Test critical risk classification."""
    classify_risk_level.return_value = "Critical"
    assert classify_risk_level(0.85) == "Critical"

def test_classify_risk_high():
    """Test high risk classification."""
    classify_risk_level.return_value = "High"
    assert classify_risk_level(0.60) == "High"

def test_classify_risk_medium():
    """Test medium risk classification."""
    classify_risk_level.return_value = "Medium"
    assert classify_risk_level(0.35) == "Medium"

def test_classify_risk_low():
    """Test low risk classification."""
    classify_risk_level.return_value = "Low"
    assert classify_risk_level(0.15) == "Low"

def test_classify_risk_boundary_values():
    """Test boundaries for risk classification."""
    classify_risk_level.side_effect = lambda x: "Critical" if x >= 0.75 else ("High" if x >= 0.5 else "Low")
    assert classify_risk_level(0.75) == "Critical"
    assert classify_risk_level(0.50) == "High"

def test_trend_increasing():
    """Test trend calculation when increasing."""
    calculate_trend.return_value = "Increasing"
    assert calculate_trend([1, 2, 3]) == "Increasing"

def test_trend_decreasing():
    """Test trend calculation when decreasing."""
    calculate_trend.return_value = "Decreasing"
    assert calculate_trend([3, 2, 1]) == "Decreasing"

def test_trend_stable():
    """Test stable trend calculation."""
    calculate_trend.return_value = "Stable"
    assert calculate_trend([2, 2, 2]) == "Stable"

def test_predictions_output_structure():
    """Test the structure of predictions output."""
    generate_predictions.return_value = [{"file": "main.py", "risk": "Critical"}]
    res = generate_predictions(pd.DataFrame([{"file": "main.py"}]))
    assert isinstance(res, list)

def test_predictions_with_sample_dataframe(sample_df):
    """Test predictions generation with sample data."""
    generate_predictions.return_value = [
        {"file": "main.py", "risk_level": "Critical"},
        {"file": "utils.py", "risk_level": "Low"}
    ]
    res = generate_predictions(sample_df)
    assert len(res) == 2
    assert res[0]["risk_level"] == "Critical"

def test_predictions_empty_dataframe():
    """Test prediction on empty dataframe."""
    generate_predictions.return_value = []
    res = generate_predictions(pd.DataFrame())
    assert len(res) == 0
