"""Rank historical candidates with support-conditioned import evidence."""
from __future__ import annotations


def rank_evidence(candidates, *, import_weight=0.0, shrinkage=2.0, top_k=3):
    """Imports strengthen existing evidence in proportion to repeated support.

    A zero weight exactly recovers temporal ranking. Candidate rows must contain
    file, temporal score, decayed pair support, and an import_link boolean.
    Returned scores are ranking evidence, without probability calibration.
    """
    if import_weight < 0 or shrinkage < 0 or top_k < 1:
        raise ValueError('Require nonnegative weights and top_k >= 1')
    ranked = []
    for candidate in candidates:
        row = dict(candidate)
        support = row['support']
        reliability = support / (support + shrinkage) if support > 0 else 0.0
        row['score'] = row['temporal'] * (
            1 + import_weight * reliability * bool(row['import_link']))
        row['reason'] = (f"Temporal evidence {row['temporal']:.4f}; "
                         f"decayed joint support {support:.3f}; "
                         f"historical import link {bool(row['import_link'])}")
        if row['score'] > 0:
            ranked.append(row)
    return sorted(ranked, key=lambda r: (-r['score'], -r['pair_count'], r['file']))[:top_k]
