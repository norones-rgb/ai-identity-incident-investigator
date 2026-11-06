import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from identity_investigator.cli import main

SAMPLE = Path(__file__).parents[1] / 'samples/synthetic_identity_events.csv'


class CliTests(unittest.TestCase):
    def test_end_to_end_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'reports'
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main([str(SAMPLE), '--out', str(out)])
            self.assertEqual(exit_code, 0)
            self.assertTrue((out / 'incident-report.html').exists())
            self.assertTrue((out / 'incident-report.json').exists())
            self.assertTrue((out / 'incident-report.csv').exists())
            self.assertIn('Post-termination', (out / 'incident-report.html').read_text())

    def test_bad_file_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(Path(tmp) / 'missing.csv')]), 2)
