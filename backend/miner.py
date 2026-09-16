from pydriller import Repository
import re
from typing import Dict, Any, Optional
from datetime import datetime
from .utils import setup_logger, timer_decorator
from . import config

logger = setup_logger("miner")

@timer_decorator
def mine_repository(repo_path: str, since: Optional[datetime] = None, to: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Mines a git repository using PyDriller to extract commit metrics.
    Adds co-change detection and sentiment scoring for commit messages.
    """
    logger.info(f"Starting to mine repository: {repo_path}...")
    file_data = {}
    
    # Sentiment keyword lists (basic heuristic)
    positive_keywords = re.compile(r'\b(improve|fix|optimize|refactor|clean|add)\b', re.IGNORECASE)
    negative_keywords = re.compile(r'\b(bug|issue|error|fail|crash|revert|broken)\b', re.IGNORECASE)
    bug_keywords = negative_keywords
    
    count = 0
    try:
        repo = Repository(repo_path, since=since, to=to)
        for commit in repo.traverse_commits():
            count += 1
            if count % 100 == 0:
                logger.info(f"Processed {count} commits...")
                
            is_bug_fix = bool(bug_keywords.search(commit.msg))
            
            # Sentiment score: +1 for positive, -1 for negative
            pos_matches = len(positive_keywords.findall(commit.msg))
            neg_matches = len(negative_keywords.findall(commit.msg))
            sentiment_score = pos_matches - neg_matches
            
            modified_files_in_commit = []
            
            for modification in commit.modified_files:
                file_path = modification.new_path or modification.old_path
                if not file_path or not file_path.endswith(config.SUPPORTED_EXTENSIONS):
                    continue
                
                modified_files_in_commit.append(file_path)
                
                if file_path not in file_data:
                    file_data[file_path] = {
                        'commits': [], 
                        'churns': [], 
                        'authors': set(), 
                        'bug_fix_count': 0,
                        'co_changes': {},
                        'sentiment_scores': []
                    }
                    
                churn = modification.added_lines + modification.deleted_lines
                file_data[file_path]['commits'].append(commit.committer_date)
                file_data[file_path]['churns'].append(churn)
                file_data[file_path]['authors'].add(commit.author.email)
                file_data[file_path]['sentiment_scores'].append(sentiment_score)
                
                if is_bug_fix:
                    file_data[file_path]['bug_fix_count'] += 1

            # Register co-changes
            for file in modified_files_in_commit:
                for co_file in modified_files_in_commit:
                    if file != co_file:
                        file_data[file]['co_changes'][co_file] = file_data[file]['co_changes'].get(co_file, 0) + 1
                        
    except Exception as e:
        logger.error(f"Error mining repository {repo_path}: {str(e)}")
        
    logger.info(f"Analyzed {count} commits. Found {len(file_data)} modified source files.")
    return file_data
