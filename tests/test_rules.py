import unittest
from pathlib import Path
from identity_investigator.ingest import parse_events
from identity_investigator.rules import correlate

SAMPLE = Path(__file__).parents[1] / 'samples/synthetic_identity_events.csv'


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.events = parse_events(SAMPLE.read_bytes(), SAMPLE.name)
        self.incidents = correlate(self.events)

    def test_expected_scenarios(self):
        self.assertEqual(len(self.incidents), 5)
        self.assertEqual({x.rule_id for x in self.incidents}, {
            'CONNECTOR_OUTAGE', 'OFFBOARDING_GAP', 'AUTH_FAILURE_BURST',
            'MFA_PRESSURE', 'DISABLED_ACCOUNT_SIGNIN',
        })

    def test_offboarding_privilege_is_critical(self):
        incident = next(x for x in self.incidents if x.rule_id == 'OFFBOARDING_GAP')
        self.assertEqual(incident.severity, 'critical')
        self.assertEqual(len(incident.evidence), 3)

    def test_no_false_positive_on_benign_signin(self):
        self.assertFalse(any(x.subject.endswith('user14@example.invalid') for x in self.incidents))
        self.assertFalse(any(x.subject.endswith('user15@example.invalid') for x in self.incidents))

    def test_incident_identifiers_are_deterministic(self):
        self.assertEqual([x.incident_id for x in correlate(self.events)],
                         [x.incident_id for x in correlate(list(reversed(self.events)))])

    def test_rule_does_not_fire_without_evidence(self):
        self.assertEqual(correlate(self.events[-4:]), [])

    def test_missing_connector_link_does_not_trigger(self):
        unrelated = [e for e in self.events if e.action != 'connector_disabled']
        self.assertFalse(any(i.rule_id == 'CONNECTOR_OUTAGE' for i in correlate(unrelated)))
