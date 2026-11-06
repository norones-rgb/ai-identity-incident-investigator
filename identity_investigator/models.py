"""Typed, immutable event and incident models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class Event:
    event_id: str
    timestamp: datetime
    source: str
    subject: str
    action: str
    outcome: str
    resource: str = ""
    actor: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["timestamp"] = self.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


@dataclass(frozen=True)
class Incident:
    incident_id: str
    rule_id: str
    title: str
    severity: str
    confidence: str
    subject: str
    start: datetime
    end: datetime
    summary: str
    recommendation: str
    evidence: tuple[str, ...]
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for k in ("start", "end"):
            value[k] = value[k].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


def make_incident(
    rule_id: str, title: str, severity: str, confidence: str, subject: str,
    summary: str, recommendation: str, events: list[Event],
) -> Incident:
    unique = {event.event_id: event for event in events}
    ordered = sorted(unique.values(), key=lambda e: (e.timestamp, e.event_id))
    digest = sha256((rule_id + "|" + "|".join(sorted(unique))).encode()).hexdigest()[:12]
    return Incident(
        incident_id=f"INC-{digest.upper()}", rule_id=rule_id, title=title,
        severity=severity, confidence=confidence, subject=subject,
        start=ordered[0].timestamp, end=ordered[-1].timestamp,
        summary=summary, recommendation=recommendation,
        evidence=tuple(e.event_id for e in ordered),
        sources=tuple(sorted({e.source for e in ordered})),
    )
