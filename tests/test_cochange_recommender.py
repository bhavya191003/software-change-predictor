"""Small checks of the co-change research prototype. Run with unittest discover."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cochange_recommender import CochangeRecommender


class CochangeTest(unittest.TestCase):
    def test_recommend_related_file_and_not_self(self):
        model = CochangeRecommender()
        model.observe(['a.py', 'b.py'], 1000.0)
        model.observe(['a.py', 'b.py'], 2000.0)
        model.observe(['a.py', 'b.py'], 3000.0)
        recs = model.recommend('a.py', 3000.0, method='static_confidence')
        self.assertEqual(recs[0]['file'], 'b.py')
        self.assertEqual(recs[0]['historical_pair_commits'], 3)
        self.assertNotIn('a.py', [x['file'] for x in recs])

    def test_abstain_without_history(self):
        model = CochangeRecommender()
        model.observe(['a.py'], 1000.0)
        self.assertEqual(model.recommend('new.py', 1000.0), [])
        self.assertEqual(model.recommend('a.py', 1000.0), [])

    def test_time_decay(self):
        model = CochangeRecommender(half_life_days=10.0)
        model.observe(['a.py', 'b.py'], 1000.0)
        first = model.pairs[('a.py','b.py')].value_at(1000., 10.)
        second = model.pairs[('a.py','b.py')].value_at(1000. + 10*86400., 10.)
        self.assertAlmostEqual(first, 1.0)
        self.assertAlmostEqual(second, 0.5)

    def test_chronological_update(self):
        model = CochangeRecommender()
        model.observe(['a.py'], 1000.0)
        with self.assertRaises(ValueError):
            model.observe(['b.py'], 999.0)

    def test_repeated_evidence_filter(self):
        model = CochangeRecommender()
        model.observe(['a.py', 'b.py'], 1000.0)
        self.assertEqual(model.recommend('a.py', 1000., method='selective_temporal'), [])
        self.assertEqual(len(model.recommend('a.py', 1000., method='static_confidence')), 1)


if __name__ == '__main__':
    unittest.main()
