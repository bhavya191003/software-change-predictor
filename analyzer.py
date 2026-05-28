import pandas as pd
import numpy as np
import math

def calculate_shannon_entropy(churn_list):
    total_churn = sum(churn_list)
    if total_churn == 0:
        return 0.0
        
    entropy = 0.0
    for churn in churn_list:
        if churn > 0:
            p_i = churn / total_churn
            entropy -= p_i * math.log2(p_i)
    return entropy

def calculate_change_velocity(dates):
    if not dates:
        return 0.0
        
    df = pd.DataFrame({'commits': 1}, index=pd.to_datetime(dates, utc=True))
    
    weekly_commits = df.resample('W').sum().fillna(0)
    
    if len(weekly_commits) <= 1:
        return float(weekly_commits['commits'].sum())
        
    ema = weekly_commits['commits'].ewm(span=4, adjust=False).mean()
    
    return float(ema.iloc[-1])

def generate_risk_metrics(file_data):
    processed_records = []
    
    for file_path, metrics in file_data.items():
        total_commits = len(metrics['commits'])
        total_churn = sum(metrics['churns'])
        unique_authors = len(metrics['authors'])
        entropy = calculate_shannon_entropy(metrics['churns'])
        
        velocity = calculate_change_velocity(metrics['commits'])
        
        bug_ratio = metrics['bug_fix_count'] / total_commits if total_commits > 0 else 0
        
        processed_records.append({
            'file_path': file_path,
            'commit_frequency': total_commits,
            'velocity': velocity,                 
            'total_churn': total_churn,
            'author_count': unique_authors,
            'entropy': entropy,
            'bug_ratio': bug_ratio
        })
        
    return pd.DataFrame(processed_records)

def compute_composite_risk(df):
    if df.empty:
        return df
        
    def normalize_column(col):
        min_val = col.min()
        max_val = col.max()
        if max_val - min_val == 0:
            return 0
        return (col - min_val) / (max_val - min_val)
        
    df['norm_entropy'] = normalize_column(df['entropy'])
    df['norm_frequency'] = normalize_column(df['commit_frequency'])
    df['norm_bug_ratio'] = normalize_column(df['bug_ratio'])
    df['norm_velocity'] = normalize_column(df['velocity']) 
    
    w_velocity = 0.35 
    w_entropy = 0.30
    w_bug_ratio = 0.25
    w_frequency = 0.10
    
    df['risk_score'] = (
        (w_entropy * df['norm_entropy']) +
        (w_frequency * df['norm_frequency']) +
        (w_bug_ratio * df['norm_bug_ratio']) +
        (w_velocity * df['norm_velocity']) 
    )
    
    df = df.sort_values(by='risk_score', ascending=False).reset_index(drop=True)
    return df