"""Leakage-aware, interpretable co-change recommendations from Git commits.

A recommendation answers: given a file already being modified, which other files
are worth inspecting? Scores are relative ranking scores, NOT probabilities.

Prototype research method: decayed directional co-change evidence with shrinkage,
repeated-evidence weighting, and an optional abstention threshold. This is a
combination of established ideas, NOT a demonstrated novel scientific method.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
import math

try:
    from src.history_data import read_history
except ModuleNotFoundError:
    from history_data import read_history

SECONDS_PER_DAY = 86400.0


@dataclass
class TimedCount:
    total: int = 0
    weighted: float = 0.0
    last_seen: float | None = None

    def value_at(self, unix_seconds: float, half_life_days: float) -> float:
        if self.last_seen is None:
            return 0.0
        age_days = max(0.0, (unix_seconds - self.last_seen) / SECONDS_PER_DAY)
        return self.weighted * math.exp(-math.log(2.0) * age_days / half_life_days)

    def observe(self, unix_seconds: float, half_life_days: float) -> None:
        self.weighted = self.value_at(unix_seconds, half_life_days) + 1.0
        self.total += 1
        self.last_seen = unix_seconds


class CochangeRecommender:
    """Incrementally learns historical file-pair relationships, one commit at a time."""

    METHODS = ('popularity', 'static_confidence', 'broken_ripple',
               'temporal_confidence', 'selective_temporal')

    def __init__(self, half_life_days: float = 365.0, max_commit_files: int = 20):
        if not math.isfinite(half_life_days) or half_life_days <= 0:
            raise ValueError('half_life_days must be positive')
        if max_commit_files < 1:
            raise ValueError('max_commit_files must be positive')
        self.half_life_days = half_life_days
        self.max_commit_files = max_commit_files
        self.files: dict[str, TimedCount] = defaultdict(TimedCount)
        self.pairs: dict[tuple[str, str], TimedCount] = defaultdict(TimedCount)
        self.neighbors: dict[str, set[str]] = defaultdict(set)
        self.observed_commits = 0
        self.skipped_large_commits = 0
        self.last_observation: float | None = None

    def observe(self, files: list[str] | tuple[str, ...], timestamp: float) -> None:
        """Update only AFTER producing predictions for a commit at timestamp."""
        if not math.isfinite(timestamp):
            raise ValueError('timestamp must be finite')
        unique = sorted({f for f in files if isinstance(f, str) and f.strip()})
        if not unique:
            return
        if self.last_observation is not None and timestamp < self.last_observation:
            raise ValueError('Commit observations must be chronological')
        self.last_observation = timestamp
        if len(unique) > self.max_commit_files:
            self.skipped_large_commits += 1
            return
        self.observed_commits += 1
        for name in unique:
            self.files[name].observe(timestamp, self.half_life_days)
        for a, b in combinations(unique, 2):
            self.pairs[(a, b)].observe(timestamp, self.half_life_days)
            self.neighbors[a].add(b)
            self.neighbors[b].add(a)

    def _features(self, seed: str, candidate: str, timestamp: float) -> dict:
        pair = self.pairs[tuple(sorted((seed, candidate)))]
        source = self.files[seed]
        wp = pair.value_at(timestamp, self.half_life_days)
        ws = source.value_at(timestamp, self.half_life_days)
        static_conf = pair.total / source.total if source.total else 0.0
        recent_conf = min(1.0, wp / ws) if ws > 0 else 0.0
        # Conservative rule: downweight thin/single-commit evidence using
        # smoothed directional confidence and a repeated-evidence factor.
        # Neither this score nor the components are calibrated probabilities.
        smoothed = wp / (ws + 2.0)
        reliability = wp / (wp + 2.0)
        repeat_factor = min(1.0, pair.total / 3.0)
        selective_score = smoothed * reliability * repeat_factor
        return {
            'file': candidate,
            'historical_pair_commits': pair.total,
            'historical_seed_commits': source.total,
            'time_weighted_pair_support': round(wp, 3),
            'historical_confidence': round(static_conf, 4),
            'temporal_confidence': round(recent_conf, 4),
            'selective_score': round(selective_score, 5),
        }

    def recommend(self, seed: str, timestamp: float, *, method: str = 'selective_temporal',
                  top_k: int = 3, threshold: float = 0.0) -> list[dict]:
        if not math.isfinite(timestamp) or not math.isfinite(threshold) or threshold < 0:
            raise ValueError('Require a finite timestamp and nonnegative finite threshold')
        if method not in self.METHODS:
            raise ValueError(f'Unknown method {method}; expected {self.METHODS}')
        if seed not in self.files or top_k < 1:
            return []
        if method == 'popularity':
            ranked = [(f, float(s.total)) for f, s in self.files.items() if f != seed]
            ranked.sort(key=lambda x: (-x[1], x[0]))
            return [{'file': f, 'score': v, 'method': method,
                     'reason': f'Changed in {self.files[f].total} earlier commits'}
                    for f, v in ranked[:top_k]]
        ranked = []
        for candidate in self.neighbors.get(seed, ()):
            info = self._features(seed, candidate, timestamp)
            if method == 'static_confidence':
                score = info['historical_confidence']
            elif method == 'broken_ripple':
                if info['historical_pair_commits'] < 3 or info['historical_confidence'] < .5:
                    continue
                score = info['historical_confidence']
            elif method == 'temporal_confidence':
                score = info['temporal_confidence']
            else:
                if info['historical_pair_commits'] < 2:
                    continue
                score = info['selective_score']
                if score < threshold:
                    continue
            if score > 0:
                ranked.append((candidate, score, info))
        ranked.sort(key=lambda x: (-x[1], -x[2]['historical_pair_commits'], x[0]))
        return [{**info, 'score': score, 'method': method,
                 'reason': f'Changed together in {info["historical_pair_commits"]} earlier commits; '
                           f'{info["historical_seed_commits"]} earlier commits touched {seed}'}
                for candidate, score, info in ranked[:top_k]]


def load_commit_history(path: str) -> list[dict]:
    """Return timestamp-grouped commit events with deterministic paths/order.

    Commit IDs on exactly the same timestamp are not allowed to inform one
    another's recommendations: evaluation updates the history after each batch.
    """
    df = read_history(path)
    events = []
    for commit_id, part in df.groupby('commit_id', sort=False):
        events.append({'commit_id': str(commit_id),
                       'timestamp': float(part['date'].min().timestamp()),
                       'files': sorted(part['file'].astype(str).unique().tolist())})
    return sorted(events, key=lambda e: (e['timestamp'], e['commit_id']))
