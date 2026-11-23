"""Regression checks for supported imports and historical source boundaries."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evidence_recommender import rank_evidence
from src.evaluate_evidence import build_record, predictions, bootstrap
from src.context_recommender import ContextRecommender


class EvidenceTests(unittest.TestCase):
    def test_import_without_history_cannot_displace_supported_candidate(self):
        rows = [dict(file='a.py', temporal=.1, support=2, pair_count=2, import_link=False),
                dict(file='b.py', temporal=0, support=0, pair_count=0, import_link=True)]
        self.assertEqual([r['file'] for r in rank_evidence(rows, import_weight=2)], ['a.py'])

    def test_zero_weight_preserves_temporal_order_and_ties(self):
        rows = [dict(file='b.py', temporal=.5, support=3, pair_count=3, import_link=True),
                dict(file='a.py', temporal=.5, support=5, pair_count=5, import_link=False)]
        self.assertEqual(rank_evidence(rows)[0]['file'], 'a.py')
        self.assertEqual(rank_evidence(rows, import_weight=1)[0]['file'], 'b.py')
        self.assertNotIn('score', rows[0])

    def test_reject_invalid_parameters(self):
        with self.assertRaises(ValueError):
            rank_evidence([], top_k=0)
        with self.assertRaises(ValueError):
            rank_evidence([], import_weight=-1)

    def test_reads_parent_imports_and_filters_deleted_paths_before_ranking(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'test@example.com')
            git('config', 'user.name', 'Test')
            for name, content in [('a.py', 'import b\n'), ('b.py', ''), ('c.py', '')]:
                (repo/name).write_text(content)
            git('add', '.')
            git('commit', '-qm', 'initial')
            (repo/'a.py').write_text('import c\n')
            git('commit', '-qam', 'event')
            event = dict(commit_id=git('rev-parse', 'HEAD'), timestamp=2000,
                         files=['a.py'])
            model = ContextRecommender()
            model.observe(['a.py', 'b.py', 'deleted.py'], 1000)
            record = build_record(model, repo, event)
            rows = {r['file']:r for r in record['candidates']}
            self.assertTrue(rows['b.py']['import_link'])
            self.assertNotIn('c.py', rows)
            self.assertNotIn('deleted.py', rows)
            self.assertEqual(record['targets'], [])
            self.assertEqual(predictions(record, 0, 3)['evidence'], ['b.py'])

    def test_bootstrap_identical_methods_have_zero_delta(self):
        records = [dict(targets=['a'], predictions={'temporal_code':['a'], 'evidence':['a']})]
        result = bootstrap(records, repeats=10)
        self.assertEqual(result['evidence']['delta_vs_temporal_95_interval'], [[0,0],[0,0]])


if __name__ == '__main__':
    unittest.main()
