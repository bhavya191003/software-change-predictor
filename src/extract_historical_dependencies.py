"""Read static Python import relationships BEFORE a specified historical Git event.

Phase 3 starter: this script extracts direct imports from one Python file as it
existed at the *parent* of an event commit. This is a source-code inspection
probe, not yet a trained predictor or evaluated recommendation algorithm.

Usage:
    python3 src/extract_historical_dependencies.py \
        --repo ../flask-source-history \
        --event-commit bfc8f983871dcadf0492578d9ab72d951b34c19c \
        --file src/flask/app.py
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
from collections import defaultdict
from pathlib import Path, PurePosixPath


def _git(repo: Path, *args: str) -> str:
    cmd = ['git', '-C', str(repo), *args]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def _module_for_file(path: str) -> str:
    """Convert source paths to plausible Python module names (no code execution)."""
    path = path.removeprefix('src/')
    p = PurePosixPath(path)
    parts = list(p.parts)
    if not parts or p.suffix != '.py':
        return ''
    parts[-1] = p.stem
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(parts)


def _index(paths: list[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in sorted(paths):
        mod = _module_for_file(path)
        if mod and mod not in index:
            index[mod] = path
    return index


def _nearest_module(name: str, index: dict[str, str]) -> str | None:
    """Look up a module, allowing imported names that are symbols, not modules."""
    parts = name.split('.')
    for n in range(len(parts), 0, -1):
        k = '.'.join(parts[:n])
        if k in index:
            return k
    return None


def imports_from_source(source: str, source_file: str, index: dict[str, str]) -> list[dict[str, str]]:
    """Return direct internal import edges with evidence; excludes self edges."""
    tree = ast.parse(source, filename=source_file)
    module = _module_for_file(source_file)
    is_package = PurePosixPath(source_file).name == '__init__.py'
    package = module if is_package else module.rpartition('.')[0]
    results: dict[str, set[str]] = defaultdict(set)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found = _nearest_module(alias.name, index)
                if found and index[found] != source_file:
                    results[index[found]].add(f'import {alias.name}')
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                pkg_parts = package.split('.') if package else []
                climb = node.level - 1
                if climb >= len(pkg_parts) + 1:
                    continue
                base_parts = pkg_parts[:len(pkg_parts)-climb] if climb else pkg_parts
                base = '.'.join([*base_parts, *([base] if base else [])])
            for alias in node.names:
                candidates = []
                if alias.name != '*':
                    candidates.append(f'{base}.{alias.name}' if base else alias.name)
                if base:
                    candidates.append(base)
                found = next((mod for candidate in candidates
                              if (mod := _nearest_module(candidate, index))), None)
                if found and index[found] != source_file:
                    dotted = '.' * node.level + (node.module or '')
                    results[index[found]].add(f'from {dotted} import {alias.name}')
    return [{'file': name, 'evidence': '; '.join(sorted(explanations))}
            for name, explanations in sorted(results.items())]


def extract_before_event(repo: Path, event_commit: str, source_file: str) -> tuple[str, list[dict[str, str]], int]:
    if not re.fullmatch(r'[0-9a-fA-F]{7,40}', event_commit):
        raise ValueError('Event commit must be a 7–40 character hexadecimal Git commit ID.')
    if PurePosixPath(source_file).is_absolute() or '..' in PurePosixPath(source_file).parts:
        raise ValueError('File must be a relative repository path without .. segments.')
    parent = _git(repo, 'rev-parse', '--verify', event_commit + '^').strip()
    paths = _git(repo, 'ls-tree', '-r', '--name-only', parent).splitlines()
    python_paths = [p for p in paths if p.endswith('.py')]
    if source_file not in python_paths:
        raise ValueError(f'{source_file} does not exist as a Python file BEFORE event {event_commit[:10]}; '
                         'it may have been added in that commit.')
    index = _index(python_paths)
    source = _git(repo, 'show', f'{parent}:{source_file}')
    edges = imports_from_source(source, source_file, index)
    return parent, edges, len(python_paths)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repo', required=True, type=Path, help='Path to Flask Git clone')
    p.add_argument('--event-commit', required=True, help='Commit whose change is being predicted')
    p.add_argument('--file', required=True, help='Python file developer is changing, relative to Git root')
    args = p.parse_args()
    if not (args.repo / '.git').exists():
        p.error(f'No Git clone found at {args.repo}')
    try:
        parent, edges, scanned = extract_before_event(args.repo, args.event_commit, args.file)
    except (RuntimeError, ValueError, SyntaxError) as exc:
        p.error(str(exc))
    print('Phase 3 — historical source dependency probe')
    print(f'Event commit:     {args.event_commit}')
    print(f'Snapshot used:    {parent} (parent of event; avoids using the event change)')
    print(f'Selected file:    {args.file}')
    print(f'Python files indexed: {scanned}')
    print(f'Direct internal import links found: {len(edges)}')
    for item in edges:
        print(f"  -> {item['file']} [{item['evidence']}]")
    if not edges:
        print('  No resolvable internal imports found. This is not proof of no dependency.')
    print('\nImportant: Static imports are possible relationships, NOT proof of change impact.')


if __name__ == '__main__':
    main()
