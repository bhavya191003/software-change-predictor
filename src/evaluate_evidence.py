"""Chronological evidence evaluation, diagnostics, and paired bootstrap intervals.

Run from the project root. Git source is read only at each event's first parent.
All validation/test events are replayed. Test results are exploratory because
this dataset has already been inspected during earlier method development.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

try:
    from src.cochange_recommender import load_commit_history
    from src.context_recommender import ContextRecommender, is_code_inspection_file
    from src.evaluate_dependency_phase3 import _selected_seed, _metrics
    from src.extract_historical_dependencies import _git, _index, imports_from_source
    from src.evidence_recommender import rank_evidence
except ModuleNotFoundError:
    from cochange_recommender import load_commit_history
    from context_recommender import ContextRecommender, is_code_inspection_file
    from evaluate_dependency_phase3 import _selected_seed, _metrics
    from extract_historical_dependencies import _git, _index, imports_from_source
    from evidence_recommender import rank_evidence


@lru_cache(maxsize=8192)
def _blob_imports(repo, blob, path, module_items):
    # Object IDs preserve historical content while allowing reuse across events.
    try:
        source = _git(Path(repo), 'show', blob)
        return {row['file']: row['evidence'] for row in
                imports_from_source(source, path, dict(module_items))}
    except (RuntimeError, SyntaxError, UnicodeDecodeError):
        return {}


def build_record(model, repo, event):
    seed = _selected_seed(event)
    parent = _git(repo, 'rev-parse', '--verify', event['commit_id'] + '^').strip()
    tree = _git(repo, 'ls-tree', '-r', '-z', parent).split('\0')
    blobs = {}
    for entry in filter(None, tree):
        metadata, path = entry.split('\t', 1)
        blobs[path] = metadata.split()[2]
    present = set(blobs)
    if seed not in present:
        raise ValueError('Seed absent from parent')
    index = _index(sorted(p for p in present if p.endswith('.py')))
    module_items = tuple(sorted(index.items()))
    def imports(path):
        if not path.endswith('.py'):
            return {}
        return _blob_imports(str(repo.resolve()), blobs[path], path, module_items)
    forward = imports(seed)
    # Rank every historical neighbor before filtering deleted paths. This avoids
    # losing viable candidates through truncation ahead of eligibility checks.
    methods = {}
    for name in ('static_code', 'temporal_code', 'role_aware_code'):
        methods[name] = [r for r in model.recommend_code(
            seed, event['timestamp'], method=name, top_k=max(1, len(model.files)))
            if r['file'] in present]
    temporal = {r['file']: r for r in methods['temporal_code']}
    pool = set(temporal) | set(forward)
    candidates = []
    for path in sorted(pool - {seed}):
        if path not in present or not is_code_inspection_file(path):
            continue
        row = temporal.get(path, {})
        linked = path in forward or seed in imports(path)
        candidates.append(dict(file=path, temporal=row.get('score', 0.0),
                               support=row.get('time_weighted_pair_support', 0.0),
                               pair_count=row.get('historical_pair_commits', 0),
                               import_link=linked))
    return dict(commit=event['commit_id'], timestamp=event['timestamp'], seed=seed,
                targets=sorted(p for p in event['files'] if p != seed and is_code_inspection_file(p)),
                targets_absent_from_parent=sorted(p for p in event['files'] if p != seed
                    and is_code_inspection_file(p) and p not in present),
                candidates=candidates, rankings=methods)


def predictions(record, weight, k):
    result = {name: [r['file'] for r in rows[:k]]
              for name, rows in record['rankings'].items()}
    result['evidence'] = [r['file'] for r in rank_evidence(
        record['candidates'], import_weight=weight, top_k=k)]
    additive = sorted(record['candidates'], key=lambda r:
        (-(r['temporal'] + .2 * r['import_link']), r['file']))
    result['additive_imports'] = [r['file'] for r in additive
                                 if r['temporal'] + .2 * r['import_link'] > 0][:k]
    return result


def bootstrap(records, baseline='temporal_code', repeats=2000):
    """Paired event resampling preserves comparison events, not temporal dependence."""
    if not records or repeats < 1:
        raise ValueError('Bootstrap requires records and positive repeats')
    names = list(records[0]['predictions'])
    rng = np.random.default_rng(42)
    counts = {}
    for name in names:
        counts[name] = np.array([[len(set(r['predictions'][name]) & set(r['targets'])),
                                 len(r['predictions'][name]), len(r['targets'])]
                                for r in records])
    samples = {name: [] for name in names}
    for _ in range(repeats):
        indices = rng.integers(0, len(records), len(records))
        for name in names:
            hits, total, truth = counts[name][indices].sum(axis=0)
            samples[name].append([hits / total if total else 0,
                                  hits / truth if truth else 0])
    result = {}
    for name in names:
        values = np.array(samples[name])
        delta = values - np.array(samples[baseline])
        result[name] = dict(precision_recall_95_interval=np.quantile(values, [.025, .975], axis=0).tolist(),
                           delta_vs_temporal_95_interval=np.quantile(delta, [.025, .975], axis=0).tolist())
    return result


def evaluate(repo, history_path, output, k=3):
    _git(repo, 'rev-parse', '--git-dir')
    history = load_commit_history(str(history_path))
    times = sorted({e['timestamp'] for e in history})
    if len(times) < 10 or k < 1:
        raise ValueError('Need >=10 distinct timestamps and k >= 1')
    validation_from, test_from = times[int(.7 * len(times))], times[int(.85 * len(times))]
    grouped = defaultdict(list)
    for event in history:
        grouped[event['timestamp']].append(event)
    model = ContextRecommender()
    records = {'validation': [], 'test': []}
    skipped = []
    for timestamp in times:
        for event in grouped[timestamp]:
            if timestamp < validation_from or len(event['files']) > 20 or not _selected_seed(event):
                continue
            phase = 'validation' if timestamp < test_from else 'test'
            try:
                record = build_record(model, repo, event)
                records[phase].append(record)
                if len(records[phase]) % 50 == 0:
                    print(f'{phase}: {len(records[phase])} events evaluated', flush=True)
            except (RuntimeError, ValueError, UnicodeDecodeError) as exc:
                skipped.append(dict(commit=event['commit_id'], phase=phase, reason=str(exc)))
        for event in grouped[timestamp]:
            model.observe(event['files'], timestamp)
    if not all(records.values()):
        raise ValueError('No usable validation or test events; check matching Git history')
    tuning = []
    for weight in (0.0, .1, .25, .5, 1.0, 2.0):
        validation = [{**r, 'predictions': predictions(r, weight, k)} for r in records['validation']]
        metric = _metrics(validation, 'evidence')
        p, recall = metric['precision'], metric['recall']
        f05 = 1.25*p*recall/(.25*p+recall) if p+recall else 0.0
        tuning.append(dict(weight=weight, f05=f05, **metric))
    selected = max(tuning, key=lambda row: (row['f05'], -row['weight']))['weight']
    test = [{**r, 'predictions': predictions(r, selected, k)} for r in records['test']]
    reports = [_metrics(test, name) for name in test[0]['predictions']]
    diagnostics = {}
    for name in ('additive_imports', 'evidence'):
        added_hits = added_misses = removed_hits = helped = harmed = 0
        for r in test:
            truth = set(r['targets'])
            baseline = set(r['predictions']['temporal_code'])
            current = set(r['predictions'][name])
            added_hits += len((current-baseline) & truth)
            added_misses += len((current-baseline)-truth)
            removed_hits += len((baseline-current) & truth)
            change = len(current & truth)-len(baseline & truth)
            helped += change > 0
            harmed += change < 0
        diagnostics[name] = dict(added_hits=added_hits, added_misses=added_misses,
                                  removed_hits=removed_hits, events_helped=helped, events_harmed=harmed)
    summary = dict(dataset=str(history_path), dataset_sha256=hashlib.sha256(history_path.read_bytes()).hexdigest(),
                   repository=str(repo), top_k=k, validation_events=len(records['validation']),
                   test_events=len(test), selected_import_weight=selected, tuning=tuning,
                   reports=reports, diagnostics=diagnostics, skipped=skipped,
                   unreachable_target_instances=sum(len(r['targets_absent_from_parent']) for r in test),
                   intervals=bootstrap(test),
                   caveats=['One repository; previously inspected test data makes this exploratory.',
                            'Event bootstrap assumes independent events and omits temporal dependence.',
                            'Same-commit labels are a proxy for inspection relevance.',
                            'All historical neighbors are eligible; candidate scope differs from Phase 3 pool 15.'])
    output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary, indent=2))
    (output/'events.json').write_text(json.dumps(test, indent=2))
    with (output/'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(reports[0]))
        writer.writeheader()
        writer.writerows(reports)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--input', default=Path('data/raw/commits.csv'), type=Path)
    parser.add_argument('--output', default=Path('results/evidence'), type=Path)
    parser.add_argument('--top-k', default=3, type=int)
    args = parser.parse_args()
    try:
        result = evaluate(args.repo, args.input, args.output, args.top_k)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: result[key] for key in ('validation_events', 'test_events',
                     'selected_import_weight', 'reports', 'diagnostics')}, indent=2))
