import csv
import io
import json
import unittest
from dataclasses import replace
from unittest.mock import patch
from pathlib import Path
from identity_investigator.ingest import parse_events
from identity_investigator.narrative import ai_payload, baseline_explanation, ollama_explanation
from identity_investigator.reporting import csv_report, html_report, json_report, report_data
from identity_investigator.rules import correlate

SAMPLE = Path(__file__).parents[1] / 'samples/synthetic_identity_events.csv'


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.events = parse_events(SAMPLE.read_bytes(), SAMPLE.name)
        self.incidents = correlate(self.events)

    def test_json_schema(self):
        data = report_data(self.events, self.incidents)
        parsed = json.loads(json_report(data))
        self.assertEqual(parsed['incident_count'], 5)
        self.assertTrue(parsed['read_only'])
        self.assertEqual(parsed['schema_version'], '1.0')

    def test_csv_rows_and_headers(self):
        rows = list(csv.DictReader(io.StringIO(csv_report(self.incidents))))
        self.assertEqual(len(rows), 5)
        self.assertEqual({r['rule_id'] for r in rows}, {i.rule_id for i in self.incidents})

    def test_csv_formula_injection_guard(self):
        injection = replace(self.incidents[0], subject='=HYPERLINK("https://bad.invalid")')
        rows = list(csv.DictReader(io.StringIO(csv_report([injection]))))
        self.assertTrue(rows[0]['subject'].startswith("'="))

    def test_html_escapes_adversarial_content(self):
        incident = replace(self.incidents[0], subject='<script>alert(1)</script>')
        rendered = html_report(report_data(self.events, [incident], {incident.incident_id:'<img src=x onerror=alert(1)>'}))
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img src=', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn("default-src 'none'", rendered)

    def test_model_receives_no_identifiers(self):
        payload = ai_payload(self.incidents[0])
        self.assertNotIn('subject', payload)
        self.assertNotIn('evidence', payload)
        self.assertNotIn('sources', payload)
        self.assertNotIn('@example.invalid', json.dumps(payload))
        self.assertTrue(baseline_explanation(self.incidents[0]).startswith('Observed pattern:'))

    def test_local_ai_never_receives_raw_identity_data(self):
        incident = next(i for i in self.incidents if i.rule_id == 'OFFBOARDING_GAP')

        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, *_): return b'{"response":"Possible session propagation delay; verify evidence."}'

        class FakeOpener:
            def open(self, request, timeout):
                self.request = request
                return FakeResponse()

        fake = FakeOpener()
        with patch('identity_investigator.narrative.build_opener', return_value=fake) as mocked:
            draft = ollama_explanation(incident, model='llama3.2:3b')
        self.assertIn('verify evidence', draft)
        self.assertEqual(fake.request.full_url, 'http://127.0.0.1:11434/api/generate')
        prompt = json.loads(fake.request.data.decode())['prompt']
        self.assertNotIn('synthetic.user07', prompt)
        self.assertNotIn('evt-', prompt)
        self.assertNotIn('@example.invalid', prompt)
        self.assertTrue(mocked.called)

    def test_model_name_guard(self):
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            ollama_explanation(self.incidents[0], model='https://external.invalid')
