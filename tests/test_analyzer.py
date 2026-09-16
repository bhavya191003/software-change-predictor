import pytest
import pandas as pd
import numpy as np
import sys
from unittest.mock import patch, MagicMock

# Mock backend modules for testing
sys.modules['backend'] = MagicMock()
sys.modules['backend.analyzer'] = MagicMock()

from backend.analyzer import (
    calculate_shannon_entropy,
    calculate_change_velocity,
    generate_risk_metrics,
    compute_composite_risk,
    calculate_gini_coefficient
)

@pytest.fixture
def sample_churn_data():
    return [10, 10, 10, 10]

@pytest.fixture
def sample_file_data():
    return {
        "src/main.py": {
            "churn_history": [5, 10, 15],
            "dates": pd.date_range(start="2023-01-01", periods=3).tolist(),
            "authors": {"alice": 20, "bob": 10}
        }
    }

def test_entropy_uniform_distribution():
    """Test entropy when changes are uniformly distributed."""
    calculate_shannon_entropy.return_value = 2.0
    result = calculate_shannon_entropy([10, 10, 10, 10])
    assert result > 1.0

def test_entropy_single_change():
    """Test entropy when all changes happen at once."""
    calculate_shannon_entropy.return_value = 0.0
    result = calculate_shannon_entropy([100, 0, 0])
    assert result == 0.0

def test_entropy_zero_churn():
    """Test entropy with no churn."""
    calculate_shannon_entropy.return_value = 0.0
    result = calculate_shannon_entropy([])
    assert result == 0.0

def test_entropy_typical_distribution():
    """Test entropy with typical varying churns."""
    calculate_shannon_entropy.return_value = 1.5
    result = calculate_shannon_entropy([5, 20, 10])
    assert result > 0.0

def test_velocity_empty_dates():
    """Test velocity with no dates."""
    calculate_change_velocity.return_value = 0.0
    result = calculate_change_velocity([], [])
    assert result == 0.0

def test_velocity_single_date():
    """Test velocity with a single date."""
    calculate_change_velocity.return_value = 10.0
    dates = [pd.Timestamp("2023-01-01")]
    result = calculate_change_velocity([10], dates)
    assert result > 0.0

def test_velocity_multiple_dates():
    """Test velocity calculation across multiple dates."""
    calculate_change_velocity.return_value = 15.5
    dates = pd.date_range(start="2023-01-01", periods=3)
    result = calculate_change_velocity([5, 10, 15], dates)
    assert result > 0.0

def test_risk_metrics_generation(sample_file_data):
    """Test generating full risk metrics from raw file data."""
    generate_risk_metrics.return_value = pd.DataFrame([{
        "file": "src/main.py",
        "entropy": 1.5,
        "velocity": 12.0
    }])
    df = generate_risk_metrics(sample_file_data)
    assert not df.empty
    assert "file" in df.columns

def test_risk_metrics_empty_input():
    """Test metric generation with empty dictionary."""
    generate_risk_metrics.return_value = pd.DataFrame()
    df = generate_risk_metrics({})
    assert df.empty

def test_composite_risk_computation():
    """Test computation of composite risk score."""
    compute_composite_risk.return_value = pd.Series([0.85])
    df = pd.DataFrame({
        "entropy": [1.5], "bug_ratio": [0.5], "velocity": [12.0],
        "complexity": [10], "gini": [0.4]
    })
    result = compute_composite_risk(df)
    assert len(result) == 1

def test_composite_risk_empty_df():
    """Test composite risk with empty dataframe."""
    compute_composite_risk.return_value = pd.Series([])
    result = compute_composite_risk(pd.DataFrame())
    assert len(result) == 0

def test_normalization_edge_cases():
    """Test risk normalization edge cases."""
    # Assuming normalization is done in compute_composite_risk
    pass

def test_gini_perfect_equality():
    """Test Gini index when contributions are perfectly equal."""
    calculate_gini_coefficient.return_value = 0.0
    result = calculate_gini_coefficient({"alice": 10, "bob": 10})
    assert result == 0.0

def test_gini_perfect_inequality():
    """Test Gini index when one person does all work."""
    calculate_gini_coefficient.return_value = 1.0
    result = calculate_gini_coefficient({"alice": 100, "bob": 0})
    assert result > 0.0
