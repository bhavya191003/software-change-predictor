"""File-role-aware, code-inspection co-change recommendations (Phase 2 experiment).

This is a *candidate research feature* and NOT an established novel method.
Uses only historical Git file names and co-change counts. It does NOT inspect
source dependencies or establish that recommended changes are necessary.
Scores are relative ranking scores, not probabilities.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import math

try:
    from src.cochange_recommender import CochangeRecommender
except ModuleNotFoundError:
    from cochange_recommender import CochangeRecommender


CODE_ROLES = frozenset({'source', 'test', 'config'})


def file_role(filename: str) -> str:
    """Heuristic role classification based on filename/path only."""
    p = PurePosixPath(filename.lower().replace('\\', '/'))
    name = p.name
    parts = set(p.parts)
    suffix = p.suffix
    if (name in {'changes', 'changelog', 'readme', 'authors', 'license', 'contributing', 'news'}
        or suffix in {'.rst', '.md', '.markdown', '.txt', '.adoc'}
        or 'docs' in parts or 'doc' in parts or 'documentation' in parts):
        return 'documentation'
    if (name.startswith('test_') or name.endswith('_test.py') or name in {'conftest.py'}
        or 'tests' in parts or 'test' in parts or '__tests__' in parts):
        return 'test'
    if (name in {'dockerfile', 'makefile', 'tox.ini', 'pyproject.toml', 'setup.cfg',
                 'requirements.in', 'requirements.txt', 'setup.py'}
        or suffix in {'.yml', '.yaml', '.toml', '.ini', '.cfg', '.json', '.xml', '.env', '.lock'}
        or name in {'.gitignore', '.gitattributes', '.editorconfig'}
        or '.github' in parts):
        return 'config'
    if suffix in {'.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp',
                  '.h', '.hpp', '.go', '.rs', '.rb', '.php', '.sh', '.sql', '.scala',
                  '.kt', '.swift'}:
        return 'source'
    if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.ttf',
                  '.css', '.html', '.pdf', '.mp4'}:
        return 'asset'
    return 'other'


def is_code_inspection_file(filename: str) -> bool:
    return file_role(filename) in CODE_ROLES


def common_directory(seed: str, candidate: str) -> bool:
    return PurePosixPath(seed).parent == PurePosixPath(candidate).parent


def looks_like_related_test(seed: str, candidate: str) -> bool:
    """A weak name-based cue, not a verified test/code dependency."""
    if {file_role(seed), file_role(candidate)} != {'source', 'test'}:
        return False
    src = seed if file_role(seed) == 'source' else candidate
    test = candidate if file_role(candidate) == 'test' else seed
    src_stem = PurePosixPath(src).stem
    test_stem = PurePosixPath(test).stem
    return test_stem in {f'test_{src_stem}', f'{src_stem}_test', src_stem}


class ContextRecommender(CochangeRecommender):
    """Same history engine as V1, restricted to an explicitly defined task."""

    METHODS_CONTEXT = ('static_code', 'temporal_code', 'role_aware_code')

    def recommend_code(self, seed: str, timestamp: float, *, method: str = 'role_aware_code',
                       top_k: int = 3, threshold: float = 0.0) -> list[dict]:
        if not math.isfinite(timestamp) or not math.isfinite(threshold) or threshold < 0:
            raise ValueError('Require a finite timestamp and nonnegative finite threshold')
        if method not in self.METHODS_CONTEXT:
            raise ValueError(f'Unknown context method: {method}')
        if seed not in self.files or top_k < 1 or not is_code_inspection_file(seed):
            return []
        choices = []
        for candidate in self.neighbors.get(seed, ()):
            if not is_code_inspection_file(candidate):
                continue
            feat = self._features(seed, candidate, timestamp)
            if method == 'static_code':
                score = feat['historical_confidence']
                explanation = 'Historical directional co-change frequency'
            elif method == 'temporal_code':
                score = feat['temporal_confidence']
                explanation = 'Recent directional co-change frequency'
            else:
                # A simple, inspectable candidate to TEST rather than a claim of novelty.
                # Uses historical recency, repeated-pair shrinkage, and weak role/path cues.
                wp = self.pairs[tuple(sorted((seed, candidate)))].value_at(timestamp, self.half_life_days)
                reliability = wp / (wp + 2.0)
                directory_bonus = 0.12 if common_directory(seed, candidate) else 0.0
                test_bonus = 0.20 if looks_like_related_test(seed, candidate) else 0.0
                role_bonus = 0.08 if file_role(seed) == file_role(candidate) else 0.0
                score = feat['temporal_confidence'] * reliability * (1 + directory_bonus + test_bonus + role_bonus)
                evidence = []
                if directory_bonus:
                    evidence.append('same directory')
                if test_bonus:
                    evidence.append('matching test/source filename')
                if role_bonus:
                    evidence.append('same file role')
                explanation = ', '.join(evidence) if evidence else 'historical co-change evidence only'
            if score >= threshold and score > 0:
                choices.append({**feat, 'score': score, 'method': method,
                                'role': file_role(candidate),
                                'reason': f'{feat["historical_pair_commits"]} earlier joint commits; '
                                          f'candidate role: {file_role(candidate)}; {explanation}'})
        choices.sort(key=lambda item: (-item['score'], -item['historical_pair_commits'], item['file']))
        return choices[:top_k]
