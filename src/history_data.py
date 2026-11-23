"""Validated CSV loading shared by training and recommendation workflows."""
import pandas as pd


def read_history(path):
    frame = pd.read_csv(path)
    required = {'commit_id', 'file', 'date'}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f'History is missing columns: {sorted(missing)}')
    frame = frame.dropna(subset=sorted(required)).copy()
    for column in ('commit_id', 'file'):
        frame[column] = frame[column].astype(str)
    frame = frame[(frame['commit_id'].str.strip() != '') & (frame['file'].str.strip() != '')]
    frame['date'] = pd.to_datetime(frame['date'], utc=True, errors='coerce')
    if frame['date'].isna().any():
        raise ValueError('History contains invalid dates')
    if frame.empty:
        raise ValueError('History contains no usable file changes')
    inconsistent = frame.groupby('commit_id')['date'].nunique()
    if (inconsistent > 1).any():
        raise ValueError('Each commit must have one timestamp')
    return frame.drop_duplicates(['commit_id', 'file']).sort_values('date')
