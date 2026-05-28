from pydriller import Repository
import re

def mine_repository(repo_path):
    print(f"Starting to mine repository: {repo_path}...")
    file_data = {}
    
    # Simple heuristic to identify bug-fixing commits
    bug_keywords = re.compile(r'\b(fix|bug|issue|close|resolve|error)\b', re.IGNORECASE)
    
    count = 0
    # We traverse the commits. PyDriller handles downloading the history automatically.
    for commit in Repository(repo_path).traverse_commits():
     
        is_bug_fix = bool(bug_keywords.search(commit.msg))
        
        for modification in commit.modified_files:
            file_path = modification.new_path or modification.old_path
            
            # Filter out non-code files
            if not file_path or not file_path.endswith(('.py', '.cpp', '.h', '.java', '.js', '.ts')):
                continue
                
            if file_path not in file_data:
                file_data[file_path] = {
                    'commits': [],
                    'churns': [],
                    'authors': set(),
                    'bug_fix_count': 0
                }
                
            churn = modification.added_lines + modification.deleted_lines
            
            # Record the metrics for this specific file
            file_data[file_path]['commits'].append(commit.committer_date)
            file_data[file_path]['churns'].append(churn)
            file_data[file_path]['authors'].add(commit.author.email)
            
            if is_bug_fix:
                file_data[file_path]['bug_fix_count'] += 1
                
    print(f"\nAnalyzed {count - 1} commits. Found {len(file_data)} modified source files.")
    return file_data

# --- TEST RUNNER ---
if __name__ == "__main__":
    # We will test this on the popular Python web framework, Flask
    test_url = "https://github.com/pallets/flask.git"
    
    # Run our extraction function
    data = mine_repository(test_url)
    
    # Print out the stats for the first 3 files we found to prove it works
    print("\n--- Sample File Metrics Extracted ---")
    for i, (file, stats) in enumerate(data.items()):
        if i >= 3: 
            break
        print(f"File: {file}")
        print(f"  Total Commits (in this window): {len(stats['commits'])}")
        print(f"  Total Churn (Lines changed): {sum(stats['churns'])}")
        print(f"  Unique Authors: {len(stats['authors'])}")
        print(f"  Bug Fixes: {stats['bug_fix_count']}\n")