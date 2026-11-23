
import os
import sys
import pandas as pd
from git import Repo
from git.exc import GitError

def collect_data(repo_path, output="data/raw/commits.csv"):
    repo = Repo(repo_path)
    records = []

    for commit in repo.iter_commits("HEAD"):
        if not commit.parents:
            continue

        changes = commit.parents[0].diff(commit)

        for change in changes:
            records.append({
                "commit_id": commit.hexsha,
                "date": commit.committed_datetime.isoformat(),
                "file": change.b_path or change.a_path,
                "change_type": change.change_type
            })

    if not records:
        raise ValueError('Repository has no non-root file changes')
    df = pd.DataFrame(records)

    from pathlib import Path
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    print("Data collected successfully!")
    print(df.head())

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect file changes from a local Git clone")
    parser.add_argument('repo')
    parser.add_argument('--output', default='data/raw/commits.csv')
    args = parser.parse_args()
    try:
        collect_data(args.repo, args.output)
    except (ValueError, OSError, GitError) as exc:
        parser.error(str(exc))
