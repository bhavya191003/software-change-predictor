"""Phase 2: chronological evaluation of *code-inspection* recommendations.

Fair comparison: same eligible files, seed selection, validation-only thresholds,
test commits, and at most three suggestions for ALL methods. Documentation/assets
are outside this particular task, and are excluded from both candidates AND labels.
This is not evidence of real developer time savings or impact causality.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

try:
    from src.cochange_recommender import load_commit_history
    from src.context_recommender import ContextRecommender, file_role, is_code_inspection_file
except ModuleNotFoundError:
    from cochange_recommender import load_commit_history
    from context_recommender import ContextRecommender, file_role, is_code_inspection_file

METHODS = ContextRecommender.METHODS_CONTEXT
GATES = [0.0, .025, .05, .075, .1, .125, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .7, .8]


def _seed(event):
    eligible = [f for f in event['files'] if is_code_inspection_file(f)]
    if not eligible:
        return None
    idx = int(hashlib.sha256(event['commit_id'].encode()).hexdigest()[:12], 16) % len(eligible)
    return sorted(eligible)[idx]


def _metric(records, method, threshold=0.0, top_k=3):
    tp = recs = possible = covered = hits = positive = 0
    for event in records:
        predictions = [p['file'] for p in event['predictions'][method]
                       if p['score'] >= threshold][:top_k]
        true = set(predictions) & event['target']
        tp += len(true)
        recs += len(predictions)
        possible += len(event['target'])
        covered += bool(predictions)
        positive += bool(event['target'])
        hits += bool(true) and bool(event['target'])
    n = len(records)
    return dict(events=n, relevant_file_instances=possible,
                true_recommendations=tp, false_recommendations=recs-tp,
                total_recommendations=recs,
                precision=round(tp/recs,4) if recs else 0.0,
                recall=round(tp/possible,4) if possible else 0.0,
                coverage=round(covered/n,4) if n else 0.0,
                hit_rate=round(hits/positive,4) if positive else 0.0,
                inspections_per_event=round(recs/n,4) if n else 0.0,
                false_alerts_per_event=round((recs-tp)/n,4) if n else 0.0)


def evaluate(path, output, *, half_life=365, max_commit_files=20, top_k=3):
    if top_k < 1 or max_commit_files < 1:
        raise ValueError('Recommendation and commit budgets must be positive')
    history = load_commit_history(path)
    if len({e['timestamp'] for e in history}) < 10:
        raise ValueError('Evaluation requires at least 10 distinct commit timestamps')
    timestamps = sorted({e['timestamp'] for e in history})
    validate_from = timestamps[int(0.70*len(timestamps))]
    test_from = timestamps[int(0.85*len(timestamps))]
    grouped = defaultdict(list)
    for event in history:
        grouped[event['timestamp']].append(event)
    model = ContextRecommender(half_life_days=half_life, max_commit_files=max_commit_files)
    records = {'validation':[], 'test':[]}
    for timestamp in timestamps:
        phase = 'train' if timestamp < validate_from else ('validation' if timestamp < test_from else 'test')
        batch = grouped[timestamp]
        if phase != 'train':
            for event in batch:
                if not 0 < len(event['files']) <= max_commit_files:
                    continue
                seed = _seed(event)
                if seed is None:
                    continue
                # Score larger list BEFORE gates to avoid dropping viable candidates
                # after rank/truncation. Same procedure for all three methods.
                predictions = {m: model.recommend_code(seed, timestamp, method=m,
                                top_k=top_k, threshold=0.0) for m in METHODS}
                records[phase].append({
                    'commit_id': event['commit_id'], 'known_file': seed,
                    'known_file_role': file_role(seed),
                    'target': {f for f in event['files'] if f != seed and is_code_inspection_file(f)},
                    'predictions': predictions,
                })
        for event in batch:
            model.observe(event['files'], timestamp)

    tuning = []
    gates = {}
    for method in METHODS:
        candidates = []
        for t in GATES:
            metrics = _metric(records['validation'], method, threshold=t, top_k=top_k)
            p, r = metrics['precision'], metrics['recall']
            f05 = (1.25*p*r/(.25*p+r)) if (.25*p+r) else 0.0
            tuning.append({'method':method, 'threshold':t, 'f0_5':round(f05,4),
                           'precision':p, 'recall':r, 'coverage':metrics['coverage']})
            candidates.append((t,f05,metrics))
        eligible = [c for c in candidates if c[2]['coverage'] >= .10]
        selected = max(eligible or candidates, key=lambda c: (c[1],c[2]['recall'],-c[0]))
        gates[method] = selected[0]

    reports = []
    for phase in ('validation','test'):
        for method in METHODS:
            reports.append({'phase':phase, 'method':method, 'threshold':gates[method],
                            **_metric(records[phase], method, gates[method], top_k)})
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    with (out/'comparison.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(reports[0]))
        writer.writeheader()
        writer.writerows(reports)
    with (out/'validation_thresholds.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(tuning[0]))
        writer.writeheader()
        writer.writerows(tuning)
    examples=[]
    for event in records['test']:
        preds = [p for p in event['predictions']['role_aware_code']
                 if p['score'] >= gates['role_aware_code']]
        if preds:
            examples.append({'known_file':event['known_file'],
                             'other_same_commit_code_files':sorted(event['target']),
                             'recommended':preds[:top_k]})
            if len(examples) == 10:
                break
    (out/'test_examples.json').write_text(json.dumps(examples,indent=2))
    summary={
        'task':'Code inspection: given one code/test/config file, recommend other code/test/config files from same historical commit',
        'not_evaluated':'documentation, non-code assets, actual code dependencies, real developer decisions',
        'source':'Git file paths and commit co-occurrence only',
        'dataset':path, 'original_commits':len(history),
        'validation_events':len(records['validation']), 'test_events':len(records['test']),
        'validation_start_utc_unix':validate_from, 'test_start_utc_unix':test_from,
        'half_life_days':half_life, 'max_commit_files':max_commit_files,
        'top_k':top_k, 'thresholds_tuned_on_validation_only':gates,
        'file_roles':'filename/path extension heuristics; imperfect',
        'caveat':'Same-commit cochanges are only a proxy for useful inspections. Scores are not probabilities.',
        'reports':reports,
    }
    (out/'evaluation_summary.json').write_text(json.dumps(summary,indent=2))
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='data/raw/commits.csv')
    parser.add_argument('--output', default='results/context')
    args=parser.parse_args()
    try:
        r=evaluate(args.input,args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Validation events: {r['validation_events']}; test events: {r['test_events']}")
    for m in r['reports']:
        print(f"{m['phase']:10} {m['method']:20} P={m['precision']:.3f} R={m['recall']:.3f} coverage={m['coverage']:.3f} alerts/event={m['false_alerts_per_event']:.3f} gate={m['threshold']:.3f}")
    print('Saved to',args.output)
