"""Transparent, deterministic correlation rules. No remediation actions."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from .models import Event, Incident, make_incident

RULES = {
    "CONNECTOR_OUTAGE": "A connector was disabled and multiple downstream provisioning attempts failed.",
    "OFFBOARDING_GAP": "An identity recorded as terminated had subsequent successful access activity.",
    "AUTH_FAILURE_BURST": "Repeated authentication failures were followed by success.",
    "MFA_PRESSURE": "Repeated MFA denials were followed by an approval.",
    "DISABLED_ACCOUNT_SIGNIN": "A sign-in succeeded after an account-disable event.",
}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _events_for_user(events: list[Event]) -> dict[str, list[Event]]:
    result: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        if event.subject != "SYSTEM":
            result[event.subject].append(event)
    return result


def correlate(events: list[Event]) -> list[Incident]:
    """Return evidence-linked alerts, not assertions of intent or root cause."""
    incidents: list[Incident] = []
    ordered = sorted(events, key=lambda e: (e.timestamp, e.event_id))

    # Outage: one incident per disabled connector in an hour, >=3 linked failures.
    accounted_for: set[str] = set()
    for down in ordered:
        if down.action != "connector_disabled" or down.event_id in accounted_for:
            continue
        connector = down.metadata.get("connector")
        if not isinstance(connector, str) or not connector:
            continue
        failures = [e for e in ordered if e.action == "provisioning_failed"
                    and e.outcome == "failure"
                    and e.metadata.get("connector") == connector
                    and down.timestamp <= e.timestamp <= down.timestamp + timedelta(minutes=60)]
        if len(failures) < 3:
            continue
        accounted_for.add(down.event_id)
        incidents.append(make_incident(
            "CONNECTOR_OUTAGE", "Potential identity connector outage", "high", "high",
            "SYSTEM", RULES["CONNECTOR_OUTAGE"],
            "Verify connector health and queue state; assess affected identities and follow the approved restoration runbook.",
            [down, *failures],
        ))

    for subject, timeline in _events_for_user(ordered).items():
        # Termination followed by access, within 24 hours; incident is aggregated.
        for term in (e for e in timeline if e.action == "user_terminated" and e.outcome == "success"):
            later = [e for e in timeline if e.action in {"authentication_succeeded", "privileged_access_granted"}
                     and e.outcome == "success"
                     and term.timestamp < e.timestamp <= term.timestamp + timedelta(hours=24)]
            if later:
                sev = "critical" if any(e.action == "privileged_access_granted" for e in later) else "high"
                incidents.append(make_incident(
                    "OFFBOARDING_GAP", "Post-termination access detected", sev, "high",
                    subject, RULES["OFFBOARDING_GAP"],
                    "Confirm HR effective time and approved exceptions; verify deprovisioning and session revocation with asset owners.",
                    [term, *later],
                ))

        for success in (e for e in timeline if e.action == "authentication_succeeded" and e.outcome == "success"):
            failed = [e for e in timeline if e.action == "authentication_failed" and e.outcome == "failure"
                      and success.timestamp - timedelta(minutes=30) <= e.timestamp < success.timestamp]
            if len(failed) >= 5:
                incidents.append(make_incident(
                    "AUTH_FAILURE_BURST", "Authentication failure burst followed by success", "medium", "medium",
                    subject, RULES["AUTH_FAILURE_BURST"],
                    "Review device, IP, sign-in context and account ownership; do not assume malicious activity from counts alone.",
                    [*failed, success],
                ))

            disabled = [e for e in timeline if e.action == "account_disabled" and e.outcome == "success"
                        and success.timestamp - timedelta(hours=6) <= e.timestamp < success.timestamp]
            if disabled:
                incidents.append(make_incident(
                    "DISABLED_ACCOUNT_SIGNIN", "Successful sign-in after account disable", "high", "medium",
                    subject, RULES["DISABLED_ACCOUNT_SIGNIN"],
                    "Verify disable propagation, application sessions and identity mapping across source systems.",
                    [disabled[-1], success],
                ))

        for approval in (e for e in timeline if e.action == "mfa_approved" and e.outcome == "success"):
            denials = [e for e in timeline if e.action == "mfa_denied" and e.outcome == "failure"
                       and approval.timestamp - timedelta(minutes=20) <= e.timestamp < approval.timestamp]
            if len(denials) >= 5:
                incidents.append(make_incident(
                    "MFA_PRESSURE", "MFA denial burst followed by approval", "high", "medium",
                    subject, RULES["MFA_PRESSURE"],
                    "Confirm whether the user initiated the MFA flow; review MFA method, originating device and access context.",
                    [*denials, approval],
                ))

    # Guard against overlapping windows generating duplicate findings per rule/user.
    # Retain distinct incidents only when their evidence sets are disjoint.
    unique: list[Incident] = []
    evidence_seen: dict[tuple[str, str], set[str]] = defaultdict(set)
    for incident in sorted(incidents, key=lambda i: (SEVERITY_RANK[i.severity], i.start, i.incident_id)):
        key = (incident.rule_id, incident.subject)
        if set(incident.evidence).intersection(evidence_seen[key]):
            continue
        evidence_seen[key].update(incident.evidence)
        unique.append(incident)
    return unique
