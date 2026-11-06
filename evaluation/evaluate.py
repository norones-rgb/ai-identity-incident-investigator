"""Reproduce the synthetic incident-fixture results; Python standard library only."""
from __future__ import annotations

import json
from pathlib import Path

from identity_investigator.ingest import parse_events
from identity_investigator.rules import correlate

ROOT = Path(__file__).resolve().parents[1]


def signature(rule_id: str, subject: str, evidence: object) -> tuple[str, str, frozenset[str]]:
    return (rule_id, subject, frozenset(evidence))


def main() -> int:
    truth = json.loads((ROOT / "evaluation/ground_truth.json").read_text(encoding="utf-8"))
    data_path = ROOT / truth["dataset"]
    events = parse_events(data_path.read_bytes(), data_path.name)
    expected = {signature(x["rule_id"], x["subject"], x["evidence"]) for x in truth["expected_incidents"]}
    found = {signature(x.rule_id, x.subject, x.evidence) for x in correlate(events)}
    tp, fp, fn = len(found & expected), len(found - expected), len(expected - found)
    negative = set(truth["negative_control_event_ids"])
    controls = [event for event in events if event.event_id in negative]
    control_findings = correlate(controls)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    result = {
        "label": "Synthetic fixture exact-signature match (NOT production performance)",
        "events": len(events), "expected": len(expected), "found": len(found),
        "true_positive": tp, "extra_findings": fp, "missed_findings": fn,
        "fixture_precision": round(precision, 4), "fixture_recall": round(recall, 4),
        "negative_control_events": len(controls),
        "negative_control_findings": len(control_findings),
        "matches_expected": (fp == 0 and fn == 0 and len(control_findings) == 0),
        "limitations": "Small authored synthetic fixture; cannot infer real-world detection accuracy."
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matches_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
