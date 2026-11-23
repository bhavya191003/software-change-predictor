"""Chronological offline evaluation of file co-change recommendation.

Assumption: one file from a historical commit is known; remaining files in the
same commit are held out as a weak proxy for files to inspect. Same-commit
co-change does NOT establish necessity or causality.

During evaluation, the recommender is updated only AFTER making predictions
for all commits at a timestamp. Threshold is chosen on validation ONLY.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from cochange_recommender import CochangeRecommender, load_commit_history

METHODS = CochangeRecommender.METHODS
GATES = [0.0, .005, .01, .02, .03, .04, .05, .075, .10, .125, .15, .2, .25, .3, .4]
PROBABILITY_LIKE_GATES = [0.0, .05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9]


def known_file(event):
    files = event['files']
    idx = int(hashlib.sha256(event['commit_id'].encode()).hexdigest()[:12], 16) % len(files)
    return files[idx]


def score_events(events, *, method, threshold=0.0):
    tp = recs = possible = covered = n_positive_events = hits = 0
    n = len(events)
    for item in events:
        candidates = [r for r in item['predictions'][method] if r['score'] >= threshold]
        target_set = item['target']
        selected = [r['file'] for r in candidates]
        correct = len(target_set.intersection(selected))
        tp += correct
        recs += len(selected)
        possible += len(target_set)
        covered += bool(selected)
        n_positive_events += bool(target_set)
        hits += bool(target_set) and bool(correct)
    fp = recs - tp
    # Utility assumes 1 true recommendation is worth 1, false alert costs .25.
    # A defined experimental objective; NOT a proven developer-time saving.
    utility = (tp - 0.25 * fp) / max(1, n)
    return {
        'events': n,
        'relevant_file_instances': possible,
        'true_recommendations': tp,
        'false_recommendations': fp,
        'total_recommendations': recs,
        'precision': round(tp / recs, 4) if recs else 0.0,
        'recall': round(tp / possible, 4) if possible else 0.0,
        'event_hit_rate': round(hits / n_positive_events, 4) if n_positive_events else 0.0,
        'coverage': round(covered / n, 4) if n else 0.0,
        'inspections_per_event': round(recs / n, 4) if n else 0.0,
        'false_alerts_per_event': round(fp / n, 4) if n else 0.0,
        'utility_per_event': round(utility, 4),
    }


def replay(events, *, half_life, k, max_commit_files):
    # Split by DISTINCT timestamps so all commits in an identical timestamp
    # batch belong to the same phase and are scored before observing the batch.
    distinct = sorted({event['timestamp'] for event in events})
    val_start = distinct[int(.70 * len(distinct))]
    test_start = distinct[int(.85 * len(distinct))]
    model = CochangeRecommender(half_life_days=half_life, max_commit_files=max_commit_files)
    records = {'validation': [], 'test': []}
    by_ts = defaultdict(list)
    for e in events:
        by_ts[e['timestamp']].append(e)
    for timestamp in distinct:
        batch = by_ts[timestamp]
        phase = ('train' if timestamp < val_start else
                 'validation' if timestamp < test_start else 'test')
        if phase != 'train':
            for event in batch:
                files = event['files']
                if len(files) > max_commit_files or not files:
                    continue
                seed = known_file(event)
                # Cold-start seeds cannot be scored; retain as a no-rec case.
                output = {method: model.recommend(seed, timestamp, method=method, top_k=k)
                          for method in METHODS}
                records[phase].append({
                    'commit_id': event['commit_id'],
                    'timestamp': timestamp,
                    'known_file': seed,
                    'target': set(files) - {seed},
                    'predictions': output,
                    'cold_start': seed not in model.files,
                })
        # All commits sharing this timestamp are observed after all predictions.
        for event in batch:
            model.observe(event['files'], event['timestamp'])
    return records, model, {'validation_start_utc': val_start, 'test_start_utc': test_start}


def evaluate(path, out_dir, *, half_life=365, k=3, max_commit_files=20):
    if k < 1 or max_commit_files < 1:
        raise ValueError('Recommendation and commit budgets must be positive')
    events = load_commit_history(path)
    if len({e['timestamp'] for e in events}) < 10:
        raise ValueError('Evaluation requires at least 10 distinct commit timestamps')
    records, model, split = replay(events, half_life=half_life, k=k,
                                   max_commit_files=max_commit_files)
    # Learn abstention gates ONLY from validation. Give traditional baselines
    # the same ability to abstain: otherwise fewer alerts is an unfair win.
    # Target: maximize F0.5 (prioritize precision) with >=10% coverage.
    gate_details = []
    def tuning(method, candidates):
        evaluations = []
        for gate in candidates:
            m = score_events(records['validation'], method=method, threshold=gate)
            p, r = m['precision'], m['recall']
            f_half = (1 + .5 ** 2) * p * r / (.5 ** 2 * p + r) if p + r else 0.0
            evaluations.append((gate, f_half, m))
            gate_details.append({'method': method, 'threshold': gate, 'f0_5': round(f_half, 4),
                                 'precision': m['precision'], 'recall': m['recall'],
                                 'coverage': m['coverage']})
        eligible = [row for row in evaluations if row[2]['coverage'] >= .10]
        return max(eligible or evaluations, key=lambda t: (t[1], t[2]['recall'], -t[0]))[0]

    selected_gates = {
        'static_confidence_gated': tuning('static_confidence', PROBABILITY_LIKE_GATES),
        'temporal_confidence_gated': tuning('temporal_confidence', PROBABILITY_LIKE_GATES),
        'selective_temporal': tuning('selective_temporal', GATES),
    }
    # Include ungated methods to show the cost of producing recommendations.
    evaluated = list(METHODS) + ['static_confidence_gated', 'temporal_confidence_gated']
    reports = []
    for phase in ('validation', 'test'):
        for method in evaluated:
            base_method = method.removesuffix('_gated')
            gate = selected_gates.get(method, 0.0)
            metric = score_events(records[phase], method=base_method, threshold=gate)
            reports.append({'phase': phase, 'method': method, 'threshold': gate, **metric})
    threshold = selected_gates['selective_temporal']
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=reports[0].keys())
        writer.writeheader()
        writer.writerows(reports)
    with (output / 'validation_thresholds.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['method', 'threshold', 'f0_5', 'precision', 'recall', 'coverage'])
        writer.writeheader()
        writer.writerows(gate_details)
    examples = []
    for e in records['test']:
        recs = [v for v in e['predictions']['selective_temporal'] if v['score'] >= threshold]
        if recs:
            examples.append({'commit_id': e['commit_id'], 'known_file': e['known_file'],
                             'actual_other_files': sorted(e['target']),
                             'recommendations': recs})
        if len(examples) >= 10:
            break
    (output / 'test_examples.json').write_text(json.dumps(examples, indent=2))
    summary = {
        'task': 'Given one known file changed in a commit, suggest other same-commit files',
        'ground_truth_caveat': 'Same-commit membership is only a proxy for needed inspections.',
        'history_source': path,
        'total_original_commits': len(events),
        'ignored_oversized_commits': model.skipped_large_commits,
        'eligible_validation_events': len(records['validation']),
        'eligible_test_events': len(records['test']),
        'validation_cold_start_fraction': round(sum(x['cold_start'] for x in records['validation'])/max(1,len(records['validation'])),4),
        'test_cold_start_fraction': round(sum(x['cold_start'] for x in records['test'])/max(1,len(records['test'])),4),
        'half_life_days': half_life,
        'max_commit_files': max_commit_files,
        'top_k': k,
        'threshold_selected_on_validation': threshold,
        'all_thresholds_selected_on_validation': selected_gates,
        'split_unix_seconds': split,
        'method_details': {
            'popularity': 'historical commit frequency of candidate file',
            'static_confidence': 'pair count / seed file count',
            'broken_ripple': 'static confidence with >=3 pairs and >=0.5 confidence',
            'temporal_confidence': '365-day half-life weighted pair / weighted seed count',
            'selective_temporal': 'decayed pair support shrunk for weak evidence; >=2 pair commits; validation-gated score',
            'static_confidence_gated': 'static confidence with a threshold tuned on validation',
            'temporal_confidence_gated': 'temporal confidence with a threshold tuned on validation',
        },
        'reports': reports,
    }
    (output / 'evaluation_summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='data/raw/commits.csv')
    parser.add_argument('--output', default='results/cochange')
    parser.add_argument('--half-life-days', type=float, default=365.)
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--max-commit-files', type=int, default=20)
    args = parser.parse_args()
    try:
        result = evaluate(args.input, args.output, half_life=args.half_life_days,
                          k=args.top_k, max_commit_files=args.max_commit_files)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    for m in result['reports']:
        print(f'{m["phase"]:10} {m["method"]:20} '
              f'P={m["precision"]:.3f} R={m["recall"]:.3f} '
              f'coverage={m["coverage"]:.3f} alerts/event={m["false_alerts_per_event"]:.3f}')
    print('Threshold selected on validation:', result['threshold_selected_on_validation'])
    print('Saved results to', args.output)
