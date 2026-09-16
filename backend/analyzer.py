import pandas as pd
import numpy as np
import math
from typing import List, Dict, Any
from datetime import datetime, timezone
from .utils import setup_logger, classify_risk
from . import config

logger = setup_logger("analyzer")

def calculate_shannon_entropy(churn_list: List[int]) -> float:
    """Calculate Shannon entropy for a list of file churns."""
    total_churn = sum(churn_list)
    if total_churn == 0:
        return 0.0
    entropy = 0.0
    for churn in churn_list:
        if churn > 0:
            p_i = churn / total_churn
            entropy -= p_i * math.log2(p_i)
    return entropy

def calculate_change_velocity(dates: List[datetime]) -> float:
    """Calculate exponential moving average of weekly commits."""
    if not dates:
        return 0.0
    dates_utc = [d if d.tzinfo else d.replace(tzinfo=timezone.utc) for d in dates]
    df = pd.DataFrame({'commits': 1}, index=pd.to_datetime(dates_utc, utc=True))
    weekly_commits = df.resample('W').sum().fillna(0)
    if len(weekly_commits) <= 1:
        return float(weekly_commits['commits'].sum())
    ema = weekly_commits['commits'].ewm(span=4, adjust=False).mean()
    return float(ema.iloc[-1])

def calculate_gini_coefficient(churn_list: List[int]) -> float:
    """Calculate Gini coefficient to measure inequality in change sizes."""
    if not churn_list:
        return 0.0
    sorted_churn = np.sort(np.array(churn_list, dtype=np.float64))
    n = len(churn_list)
    if n == 0 or np.sum(sorted_churn) == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((np.sum((2 * index - n  - 1) * sorted_churn)) / (n * np.sum(sorted_churn)))

def calculate_dev_experience(authors: set, total_repo_authors: int) -> float:
    """Simple metric: ratio of unique authors editing this file vs total repo authors."""
    if total_repo_authors == 0:
        return 0.0
    return len(authors) / total_repo_authors

def generate_risk_metrics(file_data: Dict[str, Any]) -> pd.DataFrame:
    """Generate base metrics dataframe from raw mined file data."""
    logger.info("Generating risk metrics...")
    processed_records = []
    
    all_authors = set()
    for metrics in file_data.values():
        all_authors.update(metrics['authors'])
    total_repo_authors = len(all_authors)
    
    now = datetime.now(timezone.utc)
    
    for file_path, metrics in file_data.items():
        total_commits = len(metrics['commits'])
        total_churn = sum(metrics['churns'])
        unique_authors = len(metrics['authors'])
        entropy = calculate_shannon_entropy(metrics['churns'])
        velocity = calculate_change_velocity(metrics['commits'])
        gini = calculate_gini_coefficient(metrics['churns'])
        dev_exp = calculate_dev_experience(metrics['authors'], total_repo_authors)
        bug_ratio = metrics['bug_fix_count'] / total_commits if total_commits > 0 else 0
        
        # Weight commits in the last 30 days as 2x
        recent_commits = sum(1 for d in metrics['commits'] if (now - (d if d.tzinfo else d.replace(tzinfo=timezone.utc))).days <= 30)
        recency_score = recent_commits / total_commits if total_commits > 0 else 0
        
        processed_records.append({
            'file_path': file_path, 
            'commit_frequency': total_commits, 
            'velocity': velocity,
            'total_churn': total_churn, 
            'author_count': unique_authors,
            'entropy': entropy, 
            'bug_ratio': bug_ratio,
            'gini_coefficient': gini,
            'recency_score': recency_score,
            'dev_exp': dev_exp
        })
        
    logger.info(f"Generated metrics for {len(processed_records)} files.")
    return pd.DataFrame(processed_records)

def compute_composite_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the composite risk score using configured weights."""
    logger.info("Computing composite risk scores...")
    if df.empty:
        return df
        
    def normalize_column(col):
        min_val = col.min()
        max_val = col.max()
        if max_val - min_val == 0:
            return pd.Series(0.0, index=col.index)
        return (col - min_val) / (max_val - min_val)
        
    df['norm_entropy'] = normalize_column(df['entropy'])
    df['norm_frequency'] = normalize_column(df['commit_frequency'])
    df['norm_bug_ratio'] = normalize_column(df['bug_ratio'])
    df['norm_velocity'] = normalize_column(df['velocity'])
    
    w = config.RISK_WEIGHTS
    
    df['risk_score'] = (
        (w['entropy'] * df['norm_entropy']) + 
        (w['frequency'] * df['norm_frequency']) +
        (w['bug_ratio'] * df['norm_bug_ratio']) + 
        (w['velocity'] * df['norm_velocity'])
    )
    
    df['risk_category'] = df['risk_score'].apply(classify_risk)
    
    df = df.sort_values(by='risk_score', ascending=False).reset_index(drop=True)
    return df
