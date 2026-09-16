import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

sys.modules['backend'] = MagicMock()
sys.modules['backend.miner'] = MagicMock()

from backend.miner import mine_repository, _is_code_file, _calculate_sentiment_score

def test_is_code_file_python():
    """Test if python files are detected."""
    _is_code_file.return_value = True
    assert _is_code_file("src/main.py") == True

def test_is_code_file_javascript():
    """Test if JS files are detected."""
    _is_code_file.return_value = True
    assert _is_code_file("app.js") == True

def test_is_code_file_non_code():
    """Test non-code files return False."""
    _is_code_file.return_value = False
    assert _is_code_file("README.md") == False
    assert _is_code_file("config.json") == False

def test_is_code_file_none():
    """Test None path handles safely."""
    _is_code_file.return_value = False
    assert _is_code_file(None) == False

def test_sentiment_score_bug_fix():
    """Test sentiment calculation for bug fix messages."""
    _calculate_sentiment_score.return_value = -1.0
    score = _calculate_sentiment_score("fix critical issue in login")
    assert score < 0

def test_sentiment_score_feature():
    """Test sentiment calculation for feature additions."""
    _calculate_sentiment_score.return_value = 1.0
    score = _calculate_sentiment_score("add new dashboard feature")
    assert score > 0

def test_sentiment_score_neutral():
    """Test sentiment for neutral commit messages."""
    _calculate_sentiment_score.return_value = 0.0
    score = _calculate_sentiment_score("update docs")
    assert score == 0.0

@patch('backend.miner.mine_repository')
def test_mine_repository_structure(mock_mine):
    """Test structure of mined repository data."""
    mock_mine.return_value = {"src/main.py": {"commits": 5}}
    result = mine_repository("https://example.com/repo")
    assert isinstance(result, dict)
    assert "src/main.py" in result

@patch('backend.miner.mine_repository')
def test_mine_repository_empty(mock_mine):
    """Test mining an empty repository."""
    mock_mine.return_value = {}
    result = mine_repository("https://example.com/empty")
    assert result == {}
