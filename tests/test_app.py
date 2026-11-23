"""Exercise normal app actions and baseline artifact error handling."""
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class ApplicationTests(unittest.TestCase):
    def test_default_actions_and_evidence_example(self):
        app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        for label in ('Analyze File', 'Recommend related files', 'Recommend code-related files'):
            next(button for button in app.button if button.label == label).click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
        if (ROOT/'results/evidence/events.json').exists():
            examples = next(s for s in app.selectbox if s.key == 'evidence_example')
            examples.select(1).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)

    def test_missing_model_displays_error(self):
        source = (ROOT/'app.py').read_text().replace(
            'models/change_model.pkl', 'models/absent_model_for_test.pkl')
        app = AppTest.from_string(source).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertTrue(any('Unable to load' in error.value for error in app.error))


    def test_all_forecast_files_and_recommendation_modes(self):
        app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=60)
        for file in app.selectbox[0].options:
            app.selectbox[0].select(file)
            next(b for b in app.button if b.label == 'Analyze File').click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
        for key, label in [('research_method', 'Recommend related files'),
                           ('context_mode', 'Recommend code-related files')]:
            control = next(s for s in app.selectbox if s.key == key)
            for option in control.options:
                next(s for s in app.selectbox if s.key == key).select(option)
                next(b for b in app.button if b.label == label).click().run(timeout=60)
                self.assertFalse(app.exception)
                self.assertFalse(app.error)

    def test_corrupt_features_and_optional_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'broken.csv'
            path.write_text('')
            source = (ROOT/'app.py').read_text().replace('data/processed/features.csv', str(path))
            app = AppTest.from_string(source).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            source = (ROOT/'app.py').read_text().replace('results/evidence/summary.json', str(path))
            app = AppTest.from_string(source).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertTrue(any('evidence results' in w.value for w in app.warning))


if __name__ == '__main__':
    unittest.main()
