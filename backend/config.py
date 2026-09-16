import os

# API Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# Mining Configuration
SUPPORTED_EXTENSIONS = ('.py', '.cpp', '.h', '.java', '.js', '.ts', '.go', '.rs')

# Risk Analysis Weights
RISK_WEIGHTS = {
    'velocity': 0.35,
    'entropy': 0.30,
    'bug_ratio': 0.25,
    'frequency': 0.10
}

# Risk Thresholds
RISK_THRESHOLDS = {
    'critical': 0.8,
    'high': 0.6,
    'medium': 0.3,
}

# ML Prediction Config
ML_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'n_estimators': 100
}

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
