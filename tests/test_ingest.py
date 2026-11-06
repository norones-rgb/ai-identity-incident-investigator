import io
import json
import unittest
from pathlib import Path
from identity_investigator.ingest import InputError, parse_events

SAMPLE = Path(__file__).parents[1] / 'samples/synthetic_identity_events.csv'


class IngestTests(unittest.TestCase):
    def test_csv_and_json_equivalent(self):
        csv_records = parse_events(SAMPLE.read_bytes(), SAMPLE.name)
        json_path = SAMPLE.with_suffix('.json')
        json_records = parse_events(json_path.read_bytes(), json_path.name)
        self.assertEqual([e.to_dict() for e in csv_records], [e.to_dict() for e in json_records])

    def test_reject_unsupported_extension(self):
        with self.assertRaises(InputError):
            parse_events(SAMPLE.read_bytes(), 'events.txt')

    def test_reject_unzoned_timestamp(self):
        data = json.loads(SAMPLE.with_suffix('.json').read_text())
        data['events'][0]['timestamp'] = '2026-11-03T08:05:00'
        with self.assertRaises(InputError):
            parse_events(json.dumps(data).encode(), 'events.json')

    def test_reject_duplicate_id(self):
        data = json.loads(SAMPLE.with_suffix('.json').read_text())
        data['events'][1]['event_id'] = data['events'][0]['event_id']
        with self.assertRaisesRegex(InputError, 'Duplicate'):
            parse_events(json.dumps(data).encode(), 'events.json')

    def test_reject_oversize(self):
        with self.assertRaisesRegex(InputError, 'exceeds'):
            parse_events(b'X' * (2 * 1024 * 1024 + 1), 'events.json')

    def test_reject_invalid_metadata(self):
        data = json.loads(SAMPLE.with_suffix('.json').read_text())
        data['events'][0]['metadata'] = 'invalid'
        with self.assertRaises(InputError):
            parse_events(json.dumps(data).encode(), 'events.json')

    def test_reject_invalid_outcome(self):
        data = json.loads(SAMPLE.with_suffix('.json').read_text())
        data['events'][0]['outcome'] = 'maybe'
        with self.assertRaises(InputError):
            parse_events(json.dumps(data).encode(), 'events.json')

    def test_sort_events_by_time(self):
        data = json.loads(SAMPLE.with_suffix('.json').read_text())
        data['events'].reverse()
        events = parse_events(json.dumps(data).encode(), 'events.json')
        self.assertEqual(events[0].event_id, 'evt-0001')
