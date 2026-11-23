"""Phase 3 pilot: chronological, equal-budget evaluation with historical imports.

This is exploratory, not publication-grade validation. It evaluates the same
held-out historical Git events with three recommenders:
  * Time-aware co-change (existing Phase 2 baseline)
  * Role-aware co-change (existing Phase 2 candidate)
  * Time-aware co-change plus direct static imports (Phase 3 candidate)

Important safeguards:
  - Git source is read from the PARENT of each test event.
  - Git history at or after the same event timestamp is not used in rankings.
  - Every approach uses the same eligible code/test/config labels, events,
    and maximum top-k recommendation count.
  - No hyperparameters are tuned on held-out events. The bonus is fixed.
  - Recommendations are not claims of required code modifications.

Run from project root:
    python3 src/evaluate_dependency_phase3.py --repo ../flask-source-history

Start with --max-events 40 for a manageable smoke test; zero evaluates all
eligible held-out Python-seed events (may take significant time on a Mac).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    from src.cochange_recommender import load_commit_history
    from src.context_recommender import ContextRecommender, is_code_inspection_file
    from src.extract_historical_dependencies import _git, _index
    from src.phase3_dependency_demo import _imports
except ModuleNotFoundError:
    from cochange_recommender import load_commit_history
    from context_recommender import ContextRecommender, is_code_inspection_file
    from extract_historical_dependencies import _git, _index
    from phase3_dependency_demo import _imports

METHODS = ('temporal_code', 'role_aware_code', 'history_plus_imports')


def _selected_seed(event: dict) -> str | None:
    """Fixed, reproducible seed choice; cannot use target files to rank."""
    eligible = sorted(p for p in event['files'] if p.endswith('.py')
                      and is_code_inspection_file(p))
    if not eligible:
        return None
    i = int(hashlib.sha256(event['commit_id'].encode()).hexdigest()[:12], 16)
    return eligible[i % len(eligible)]


def _choose_events(events: list[dict], max_events: int) -> set[str]:
    """Sample test events before producing any recommendations or using labels."""
    if max_events == 0 or len(events) <= max_events:
        return {e['commit_id'] for e in events}
    # Deterministic pseudo-random sample spread across whole test interval.
    ranked = sorted(events, key=lambda e:
                    hashlib.sha256(('phase3-v1-'+e['commit_id']).encode()).hexdigest())
    return {e['commit_id'] for e in ranked[:max_events]}


def _rank_candidates(model: ContextRecommender, repo: Path, event: dict,
                     seed: str, top_k: int, pool_size: int,
                     bonus: float) -> dict[str, list[str]]:
    timestamp = event['timestamp']
    # The source tree must PRECEDE the target event.
    parent = _git(repo, 'rev-parse', '--verify', event['commit_id'] + '^').strip()
    paths = _git(repo, 'ls-tree', '-r', '--name-only', parent).splitlines()
    present = set(paths)
    if seed not in present:
        raise ValueError('Seed absent from event parent (newly added or renamed)')
    index = _index([p for p in paths if p.endswith('.py')])

    temporal_raw = model.recommend_code(seed, timestamp, method='temporal_code',
                                        top_k=pool_size, threshold=0)
    role_raw = model.recommend_code(seed, timestamp, method='role_aware_code',
                                    top_k=pool_size, threshold=0)
    temporal = {row['file']: float(row['score']) for row in temporal_raw
                if row['file'] in present}
    imports_seed = _imports(repo, parent, seed, index, present)
    candidates = (set(temporal) | set(imports_seed)) - {seed}
    candidates = {p for p in candidates if p in present and is_code_inspection_file(p)}

    # Compare three methods for the exact same historical event and candidate
    # constraints. Reverse imports are searched only for pool candidates,
    # matching the scope of the earlier single-commit demonstration.
    scores = []
    for candidate in candidates:
        forward = candidate in imports_seed
        reverse = seed in _imports(repo, parent, candidate, index, present)
        scores.append((candidate,
                       temporal.get(candidate, 0.0) + bonus * int(forward or reverse)))
    combined = [p for p, score in sorted(scores, key=lambda x: (-x[1], x[0]))
                if score > 0][:top_k]
    return {
        'temporal_code': [r['file'] for r in temporal_raw
                          if r['file'] in present][:top_k],
        'role_aware_code': [r['file'] for r in role_raw
                            if r['file'] in present][:top_k],
        'history_plus_imports': combined,
    }


def _metrics(records: list[dict], method: str) -> dict:
    correct = total = relevant = covered = hit = positive = 0
    for r in records:
        predicted = set(r['predictions'][method])
        truth = set(r['targets'])
        correct += len(predicted & truth)
        total += len(predicted)
        relevant += len(truth)
        covered += bool(predicted)
        positive += bool(truth)
        hit += bool(predicted & truth) if truth else 0
    n = len(records)
    return {
        'method': method, 'events': n, 'total_recommendations': total,
        'correct_recommendations': correct, 'actual_related_file_instances': relevant,
        'precision': round(correct / total, 4) if total else 0.0,
        'recall': round(correct / relevant, 4) if relevant else 0.0,
        'coverage': round(covered / n, 4) if n else 0.0,
        'hit_rate': round(hit / positive, 4) if positive else 0.0,
        'false_alerts_per_event': round((total-correct)/n, 4) if n else 0.0,
        'inspections_per_event': round(total/n, 4) if n else 0.0,
    }


def evaluate(repo: Path, input_path: Path, out: Path, *, top_k: int = 3,
             pool_size: int = 15, max_events: int = 40,
             dependency_bonus: float = .20, max_commit_files: int = 20) -> dict:
    if top_k < 1 or pool_size < top_k or max_events < 0 or not 0 <= dependency_bonus <= 1:
        raise ValueError('Require top-k>=1, pool-size>=top-k, max-events>=0, 0<=bonus<=1')
    if not (repo / '.git').exists():
        raise FileNotFoundError(f'Cannot find Git repository at {repo}')
    history = load_commit_history(str(input_path))
    if len({e['timestamp'] for e in history}) < 10:
        raise ValueError('Evaluation requires at least 10 distinct commit timestamps')
    times = sorted({e['timestamp'] for e in history})
    test_from = times[int(.85 * len(times))]
    eligible = [e for e in history if e['timestamp'] >= test_from
                and 0 < len(e['files']) <= max_commit_files
                and _selected_seed(e)]
    selected = _choose_events(eligible, max_events)
    grouped = defaultdict(list)
    for e in history:
        grouped[e['timestamp']].append(e)

    model = ContextRecommender(half_life_days=365, max_commit_files=max_commit_files)
    records = []
    skipped = []
    for timestamp in times:
        batch = grouped[timestamp]
        for event in batch:
            if event['commit_id'] not in selected:
                continue
            seed = _selected_seed(event)
            if seed not in model.files:
                skipped.append({'commit':event['commit_id'], 'reason':'No previous history for seed'})
                continue
            try:
                preds = _rank_candidates(model, repo, event, seed, top_k,
                                         pool_size, dependency_bonus)
            except (RuntimeError, ValueError, UnicodeDecodeError) as exc:
                skipped.append({'commit': event['commit_id'], 'reason': str(exc)[:220]})
                continue
            targets = sorted(p for p in event['files'] if p != seed
                             and is_code_inspection_file(p))
            records.append({'commit': event['commit_id'], 'seed':seed,
                            'targets':targets, 'predictions':preds})
        # Never observe same-timestamp commits before predicting their batch.
        for event in batch:
            model.observe(event['files'], timestamp)

    reports = [_metrics(records, method) for method in METHODS]
    out.mkdir(parents=True, exist_ok=True)
    with (out/'comparison.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(reports[0]))
        writer.writeheader()
        writer.writerows(reports)
    (out/'examples.json').write_text(json.dumps(records[:25], indent=2))
    summary = {
        'scope': 'Exploratory test: Python seed, eligible source/test/config same-commit labels',
        'source_history':str(repo), 'dataset':str(input_path),
        'test_start_unix':test_from, 'eligible_held_out_events':len(eligible),
        'sampled_events':len(selected), 'evaluated_events':len(records),
        'skipped_events':skipped, 'top_k':top_k, 'candidate_pool':pool_size,
        'dependency_bonus_fixed_in_advance':dependency_bonus,
        'methods':list(METHODS), 'reports':reports,
        'caveats': [
            'Same-commit co-change is a weak proxy for inspection relevance.',
            'The source tree for each event is the event parent, not the present-day repository.',
            'Static imports miss dynamic/call-level dependencies and may give false links.',
            'Reverse imports are checked only inside a limited candidate pool.',
            'Sampling Python-seed events limits generalizability.',
            'A single repository, a small pilot and an arbitrary fixed bonus do not establish novelty.',
            'This top-k comparison is ungated and cannot be directly compared with earlier gated scores.',
        ],
    }
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--input', type=Path, default=Path('data/raw/commits.csv'))
    p.add_argument('--output', type=Path, default=Path('results/phase3'))
    p.add_argument('--max-events', type=int, default=40,
                   help='Deterministic sample size; 0 means all eligible held-out events')
    p.add_argument('--top-k', type=int, default=3)
    p.add_argument('--pool-size', type=int, default=15)
    p.add_argument('--dependency-bonus', type=float, default=.2)
    args = p.parse_args()
    try:
        result = evaluate(args.repo, args.input, args.output, top_k=args.top_k,
                          pool_size=args.pool_size, max_events=args.max_events,
                          dependency_bonus=args.dependency_bonus)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        p.error(str(exc))
    print(f"Selected {result['sampled_events']} historical test events; "
          f"evaluated {result['evaluated_events']}; "
          f"skipped {len(result['skipped_events'])}.")
    for r in result['reports']:
        print(f"{r['method']:24} P={r['precision']:.3f} R={r['recall']:.3f} "
              f"coverage={r['coverage']:.3f} "
              f"false alerts/event={r['false_alerts_per_event']:.3f}")
    print('Results written to:', args.output)
    print('CAUTION: This is an exploratory evaluation, not demonstrated research novelty.')


if __name__ == '__main__':
    main()
