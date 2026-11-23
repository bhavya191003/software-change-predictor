"""Phase 2 tests. Run python3 -m unittest discover -s tests -v."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.context_recommender import ContextRecommender, file_role, is_code_inspection_file


class RoleTests(unittest.TestCase):
    def test_file_roles(self):
        self.assertEqual(file_role('src/flask/app.py'), 'source')
        self.assertEqual(file_role('tests/test_app.py'), 'test')
        self.assertEqual(file_role('docs/quickstart.rst'), 'documentation')
        self.assertEqual(file_role('CHANGES.rst'), 'documentation')
        self.assertEqual(file_role('.github/workflows/tests.yml'), 'config')
        self.assertTrue(is_code_inspection_file('pyproject.toml'))
        self.assertFalse(is_code_inspection_file('CHANGES.rst'))

    def test_docs_excluded_for_every_comparable_method(self):
        model = ContextRecommender()
        for i in range(5):
            model.observe(['src/app.py', 'src/session.py', 'CHANGES.rst'], 1000. + i)
        for method in ContextRecommender.METHODS_CONTEXT:
            recs = model.recommend_code('src/app.py', 1006., method=method)
            self.assertTrue(recs)
            self.assertEqual([rec['file'] for rec in recs], ['src/session.py'])

    def test_abstention_and_no_self_recommendation(self):
        model = ContextRecommender()
        model.observe(['src/a.py'], 1000.)
        self.assertEqual(model.recommend_code('src/a.py', 1000.), [])
        self.assertEqual(model.recommend_code('unknown.py', 1000.), [])
        self.assertEqual(model.recommend_code('docs/intro.rst', 1000.), [])

    def test_test_filename_cue(self):
        model=ContextRecommender()
        for i in range(3):
            model.observe(['src/login.py', 'tests/test_login.py'], 1000. + i)
        recommendation=model.recommend_code('src/login.py', 1003.)[0]
        self.assertIn('matching test/source filename', recommendation['reason'])
        self.assertEqual(recommendation['role'], 'test')

    def test_temporal_without_future_commits(self):
        model=ContextRecommender()
        model.observe(['src/app.py', 'src/util.py'], 1000.)
        first = model.recommend_code('src/app.py', 1000., method='temporal_code')[0]
        self.assertEqual(first['historical_pair_commits'], 1)
        model.observe(['src/app.py', 'src/util.py'], 2000.)
        second = model.recommend_code('src/app.py', 2000., method='temporal_code')[0]
        self.assertEqual(second['historical_pair_commits'], 2)


if __name__ == '__main__':
    unittest.main()
