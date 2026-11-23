"""Validation of malformed histories and every available recommendation seed."""
import math
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.history_data import read_history
from src.cochange_recommender import CochangeRecommender, load_commit_history
from src.context_recommender import ContextRecommender, is_code_inspection_file
from src.train_change_model import train_model
from src.extract_features import extract_features
from src.evaluate_evidence import bootstrap


class PipelineTests(unittest.TestCase):
    def test_invalid_histories(self):
        samples = ['file,date\na.py,2020-01-01\n',
                   'commit_id,file,date\n',
                   'commit_id,file,date\na,a.py,invalid\n',
                   'commit_id,file,date\na,a.py,2020-01-01\na,b.py,2020-01-02\n']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'history.csv'
            for sample in samples:
                path.write_text(sample)
                with self.subTest(sample=sample), self.assertRaises(ValueError):
                    read_history(path)

    def test_duplicates_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'history.csv'
            path.write_text('commit_id,file,date\na,a.py,2020-01-01\na,a.py,2020-01-01\n')
            self.assertEqual(len(read_history(path)), 1)

    def test_failed_training_preserves_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = root/'history.csv'
            history.write_text('commit_id,file,date\na,a.py,2020-01-01\n')
            model, dataset = root/'model.pkl', root/'dataset.csv'
            model.write_bytes(b'existing model')
            dataset.write_text('existing dataset')
            with self.assertRaisesRegex(ValueError, 'Not enough historical'):
                train_model(history, model, dataset)
            self.assertEqual(model.read_bytes(), b'existing model')
            self.assertEqual(dataset.read_text(), 'existing dataset')
            with self.assertRaisesRegex(ValueError, 'No files found'):
                extract_features(history, root/'features.csv')

    def test_all_stored_seeds_and_methods(self):
        events = load_commit_history('data/raw/commits.csv')
        model = ContextRecommender()
        for event in events:
            model.observe(event['files'], event['timestamp'])
        timestamp = events[-1]['timestamp']
        for seed in list(model.files):
            for method in model.METHODS:
                rows = model.recommend(seed, timestamp, method=method)
                self.check_rows(seed, rows)
            for method in model.METHODS_CONTEXT:
                rows = model.recommend_code(seed, timestamp, method=method)
                self.check_rows(seed, rows)
                self.assertTrue(all(is_code_inspection_file(r['file']) for r in rows))

    def check_rows(self, seed, rows):
        files = [r['file'] for r in rows]
        self.assertLessEqual(len(files), 3)
        self.assertEqual(len(files), len(set(files)))
        self.assertNotIn(seed, files)
        self.assertTrue(all(math.isfinite(r['score']) and r['score'] > 0 for r in rows))

    def test_invalid_configuration(self):
        for half_life in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                CochangeRecommender(half_life_days=half_life)
        with self.assertRaises(ValueError):
            CochangeRecommender(max_commit_files=0)
        with self.assertRaises(ValueError):
            CochangeRecommender().observe(['a.py'], float('nan'))
        with self.assertRaises(ValueError):
            bootstrap([])

    def test_invalid_cli_inputs_produce_actionable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'empty.csv'
            path.write_text('commit_id,file,date\n')
            commands = [
                ['src/collect_data.py', str(Path(directory)/'missing')],
                ['src/train_change_model.py', '--input', str(path)],
                ['src/extract_features.py', '--input', str(path)],
                ['src/evaluate_cochange.py', '--input', str(path)],
                ['src/evaluate_context.py', '--input', str(path)],
            ]
            for args in commands:
                result = subprocess.run([sys.executable, *args], text=True, capture_output=True)
                with self.subTest(command=args[0]):
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertIn('error:', result.stderr)

    def test_git_paths_with_spaces_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'history.csv'
            path.write_text('commit_id,file,date\na, a.py ,2020-01-01\n')
            self.assertEqual(read_history(path).iloc[0]['file'], ' a.py ')
