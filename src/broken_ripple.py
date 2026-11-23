
import pandas as pd
from collections import Counter, defaultdict
from itertools import combinations

# Load historical Git commit data
df = pd.read_csv("data/raw/commits.csv")
df = df.dropna(subset=["commit_id", "file"])

# Group files by commit
commits = df.groupby("commit_id")["file"].apply(
    lambda x: sorted(set(x))
)

# Count how often each file changes
file_counts = Counter()

# Count how often two files change together
pair_counts = Counter()

for files in commits:
    for file in files:
        file_counts[file] += 1

    for file_a, file_b in combinations(files, 2):
        pair_counts[(file_a, file_b)] += 1

# Build historical relationships
relationships = defaultdict(list)

MIN_SUPPORT = 3
MIN_CONFIDENCE = 0.5

for (file_a, file_b), count in pair_counts.items():

    if count < MIN_SUPPORT:
        continue

    confidence_ab = count / file_counts[file_a]
    confidence_ba = count / file_counts[file_b]

    if confidence_ab >= MIN_CONFIDENCE:
        relationships[file_a].append(
            (file_b, confidence_ab)
        )

    if confidence_ba >= MIN_CONFIDENCE:
        relationships[file_b].append(
            (file_a, confidence_ba)
        )


def detect_broken_ripple(changed_files):
    changed_files = set(changed_files)
    warnings = {}

    for file in changed_files:
        for related_file, confidence in relationships.get(file, []):

            if related_file not in changed_files:
                warnings[(file, related_file)] = confidence

    return warnings


# Test with a real historical file relationship
if relationships:
    test_file = next(iter(relationships))
    print("Testing changed file:", test_file)

    warnings = detect_broken_ripple([test_file])

    for (file_a, file_b), score in warnings.items():
        print(
            f"WARNING: {file_b} often changes with {file_a}. "
            f"Broken Ripple Score: {score:.2f}"
        )
else:
    print("No strong co-change relationships found.")
