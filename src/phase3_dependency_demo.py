"""Phase 3 EXPLORATORY example: compare co-change-only with import-assisted ranking.

This is a SINGLE historical-event demonstration, NOT a research evaluation or a
claim of novelty. Uses Git import relationships from the parent of an event.
It does not use the event's changed-file list until printing a retrospective check.

Usage (from your Version 2 project root):
    python3 src/phase3_dependency_demo.py \
      --repo ../flask-source-history \
      --event-commit bfc8f983871dcadf0492578d9ab72d951b34c19c \
      --file src/flask/app.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from src.cochange_recommender import load_commit_history
    from src.context_recommender import ContextRecommender, is_code_inspection_file
    from src.extract_historical_dependencies import (
        _git, _index, imports_from_source,
    )
except ModuleNotFoundError:
    from cochange_recommender import load_commit_history
    from context_recommender import ContextRecommender, is_code_inspection_file
    from extract_historical_dependencies import _git, _index, imports_from_source


def _imports(repo: Path, revision: str, path: str, index: dict[str, str], present: set[str]) -> dict[str, str]:
    """Parse internal imports in file at revision. Return target -> evidence."""
    if path not in present or not path.endswith('.py'):
        return {}
    try:
        source = _git(repo, 'show', f'{revision}:{path}')
        return {d['file']: d['evidence'] for d in imports_from_source(source, path, index)}
    except (RuntimeError, SyntaxError, UnicodeDecodeError) as exc:
        # Historical source might be unparsable, deleted, or not locally available.
        print(f'  Note: dependency scan skipped for {path}: {exc}', file=sys.stderr)
        return {}


def compare(repo: Path, history_file: Path, event_commit: str, seed: str,
            *, top_k: int = 3, pool_size: int = 30, dependency_bonus: float = .20) -> dict:
    if not re.fullmatch(r'[0-9a-fA-F]{7,40}', event_commit):
        raise ValueError('Commit ID must be 7–40 hexadecimal characters')
    if top_k < 1 or pool_size < top_k or not 0 <= dependency_bonus <= 1:
        raise ValueError('Use top-k >= 1, pool-size >= top-k, dependency-bonus between 0 and 1')
    data = load_commit_history(str(history_file))
    exact = [e for e in data if e['commit_id'].startswith(event_commit)]
    if len(exact) != 1:
        raise ValueError(f'Expected one event in dataset matching {event_commit}; got {len(exact)}')
    event = exact[0]
    if seed not in event['files']:
        raise ValueError(f'{seed} was not changed in selected event; choose a changed file')
    if not is_code_inspection_file(seed):
        raise ValueError('Choose source, test, or configuration file as seed')

    # Import facts come from the parent Git tree, strictly before this event.
    parent = _git(repo, 'rev-parse', '--verify', f'{event["commit_id"]}^').strip()
    paths = _git(repo, 'ls-tree', '-r', '--name-only', parent).splitlines()
    present = set(paths)
    idx = _index([p for p in paths if p.endswith('.py')])
    if seed not in present:
        raise ValueError('Seed file does not exist in the pre-event source tree')

    # History is observed strictly before event timestamp. Records at same
    # timestamp are excluded so same-time commits cannot reveal event answers.
    model = ContextRecommender(half_life_days=365, max_commit_files=20)
    used = 0
    for earlier in data:
        if earlier['timestamp'] >= event['timestamp']:
            break
        model.observe(earlier['files'], earlier['timestamp'])
        used += 1
    timestamp = event['timestamp']
    if seed not in model.files:
        raise ValueError('No earlier history for selected file; cannot compare baseline')

    # A common candidate pool is formed from the strongest temporal co-change
    # candidates PLUS direct imports from the seed. Dependencies need not have
    # appeared in earlier joint commits.
    historical = model.recommend_code(seed, timestamp, method='temporal_code',
                                      top_k=pool_size, threshold=0)
    recent_scores = {row['file']: float(row['score']) for row in historical}
    imports_seed = _imports(repo, parent, seed, idx, present)
    candidates = set(recent_scores) | set(imports_seed)
    candidates = {c for c in candidates if c in present and c != seed
                  and is_code_inspection_file(c)}
    # Reverse imports are checked only for these candidates, not every file in
    # the repository. Consequently this is an exploratory partial dependency view.
    rows = []
    for candidate in sorted(candidates):
        forward = imports_seed.get(candidate)
        reverse = _imports(repo, parent, candidate, idx, present).get(seed)
        structural = int(bool(forward or reverse))
        temporal = recent_scores.get(candidate, 0.0)
        # This fixed bonus is an experimental heuristic, not a learned weight,
        # not an estimated probability, and not tuned against the event labels.
        score = temporal + dependency_bonus * structural
        evidence = []
        if forward:
            evidence.append(f'{seed} imports {candidate} ({forward})')
        if reverse:
            evidence.append(f'{candidate} imports {seed} ({reverse})')
        if not evidence:
            evidence.append('no resolved direct import in checked direction(s)')
        rows.append({'file':candidate,'temporal_score':temporal,
                     'combined_score':score,'has_import_link':bool(structural),
                     'evidence':'; '.join(evidence)})

    temporal_ranked = sorted([r for r in rows if r['temporal_score'] > 0],
                             key=lambda r: (-r['temporal_score'],r['file']))[:top_k]
    combined_ranked = sorted([r for r in rows if r['combined_score'] > 0],
                             key=lambda r: (-r['combined_score'],r['file']))[:top_k]
    # ONLY for retrospective demonstration. Never fed into score selection.
    targets = {p for p in event['files'] if p != seed and is_code_inspection_file(p)}
    return {'event':event['commit_id'],'event_date':event['timestamp'],
            'seed':seed,'parent':parent,'history_commits':used,
            'candidate_count':len(rows),'same_commit_code_files':sorted(targets),
            'temporal':temporal_ranked,'combined':combined_ranked,
            'dependency_bonus':dependency_bonus,
            'scope_note':'Direct static imports only; reverse scan limited to candidate pool.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--event-commit',required=True)
    parser.add_argument('--file',required=True)
    parser.add_argument('--history',type=Path,default=Path('data/raw/commits.csv'))
    parser.add_argument('--top-k',type=int,default=3)
    parser.add_argument('--pool-size',type=int,default=30)
    parser.add_argument('--dependency-bonus',type=float,default=.20)
    args=parser.parse_args()
    try:
        r = compare(args.repo,args.history,args.event_commit,args.file,
                    top_k=args.top_k,pool_size=args.pool_size,
                    dependency_bonus=args.dependency_bonus)
    except (RuntimeError,ValueError,FileNotFoundError) as exc:
        parser.error(str(exc))
    print('\nPHASE 3: HISTORICAL DEPENDENCY-ASSISTED DEMO')
    print('Event:',r['event'])
    print('Seed:',r['seed'])
    print('Source snapshot:',r['parent'],'(parent; before event)')
    print('Prior history commits used:',r['history_commits'])
    print('Candidate files checked:',r['candidate_count'])
    print('\nA) TIME-AWARE CO-CHANGE ONLY')
    for i,row in enumerate(r['temporal'],1):
        print(f"  {i}. {row['file']}  score={row['temporal_score']:.3f}")
    if not r['temporal']:
        print('  No historical recommendation')
    print('\nB) EXPERIMENTAL HISTORY + IMPORT LINK')
    for i,row in enumerate(r['combined'],1):
        print(f"  {i}. {row['file']}  score={row['combined_score']:.3f}  import_link={row['has_import_link']}")
        print(f"     Evidence: {row['evidence']}")
    if not r['combined']:
        print('  No recommendation')
    print('\nRETROSPECTIVE CHECK (not used to generate rankings)')
    print('Other code/test/config files in the event:',r['same_commit_code_files'])
    print('\nThis is one example, NOT a statistical result. Imported files might not need modification.')
    print('To establish improvement we must evaluate many held-out commits fairly.')

if __name__ == '__main__':
    main()
