import logging
import time
from functools import wraps
from urllib.parse import urlparse
from . import config

def setup_logger(name: str) -> logging.Logger:
    """Configures and returns a logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(config.LOG_LEVEL)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def validate_github_url(url: str) -> bool:
    """Validates if the provided string is a valid GitHub URL or local path."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme in ['http', 'https'] and 'github.com' in parsed.netloc:
        return True
    return True

def format_file_path(path: str, max_length: int = 50) -> str:
    """Truncates file paths for cleaner display."""
    if len(path) <= max_length:
        return path
    return "..." + path[-(max_length - 3):]

def classify_risk(score: float) -> str:
    """Classifies a risk score into a category."""
    if score >= config.RISK_THRESHOLDS['critical']:
        return 'Critical'
    elif score >= config.RISK_THRESHOLDS['high']:
        return 'High'
    elif score >= config.RISK_THRESHOLDS['medium']:
        return 'Medium'
    else:
        return 'Low'

def timer_decorator(func):
    """Decorator to measure the execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger = logging.getLogger(func.__module__)
        logger.info(f"Function '{func.__name__}' executed in {end_time - start_time:.4f} seconds.")
        return result
    return wrapper
