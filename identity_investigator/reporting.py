"""Portable reports with HTML and CSV injection safeguards."""
from __future__ import annotations

import csv
import html
import io
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Mapping
from .models import Event, Incident


def report_data(events: list[Event], incidents: list[Incident], narratives: Mapping[str, str] | None = None) -> dict:
    narratives = narratives or {}
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "read_only": True,
        "input_event_count": len(events),
        "incident_count": len(incidents),
        "by_severity": dict(Counter(i.severity for i in incidents)),
        "incidents": [dict(i.to_dict(), narrative=narratives.get(i.incident_id, "")) for i in incidents],
    }


def json_report(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _safe_csv(value: object) -> str:
    """Prevent spreadsheet formula execution on open, including leading whitespace."""
    string = str(value)
    if string.lstrip().startswith(("=", "+", "-", "@")) or string.startswith(("\t", "\r", "\n")):
        return "'" + string
    return string


def csv_report(incidents: list[Incident]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["incident_id", "rule_id", "severity", "confidence", "subject", "title",
                     "start_utc", "end_utc", "evidence_count", "event_ids", "sources", "summary", "recommendation"])
    for incident in incidents:
        fields = [incident.incident_id, incident.rule_id, incident.severity, incident.confidence,
                  incident.subject, incident.title, incident.start.isoformat(), incident.end.isoformat(),
                  len(incident.evidence), ";".join(incident.evidence), ";".join(incident.sources),
                  incident.summary, incident.recommendation]
        writer.writerow([_safe_csv(x) for x in fields])
    return stream.getvalue()


def html_report(payload: dict) -> str:
    e = lambda x: html.escape(str(x), quote=True)
    rows = []
    for item in payload["incidents"]:
        severity = item["severity"] if item["severity"] in {"critical", "high", "medium", "low"} else "low"
        evidence = ", ".join(map(str, item["evidence"]))
        narrative = item.get("narrative") or "Not requested. The findings above come from deterministic correlation rules."
        rows.append(f'''<article class="incident">
  <header><span class="tag {severity}">{e(severity.upper())}</span><span class="rule">{e(item['rule_id'])}</span></header>
  <h2>{e(item['title'])}</h2>
  <p class="meta"><strong>Subject:</strong> {e(item['subject'])} &nbsp; <strong>Confidence:</strong> {e(item['confidence'])} &nbsp; <strong>Window:</strong> {e(item['start'])} – {e(item['end'])}</p>
  <p>{e(item['summary'])}</p><p><strong>Next verification:</strong> {e(item['recommendation'])}</p>
  <details><summary>Evidence ({len(item['evidence'])} events)</summary><p>{e(evidence)}</p><p>Sources: {e(', '.join(item['sources']))}</p></details>
  <details><summary>Analyst narrative</summary><p>{e(narrative)}</p></details>
</article>''')
    body = "\n".join(rows) if rows else '<p class="empty">No patterns matched the enabled rules.</p>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Identity Incident Investigation — Synthetic Demo</title>
<style>
:root{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#f1f3f8;background:#111827}}
*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1080px;margin:auto;padding:40px 22px 80px}}
.hero{{padding:30px;border:1px solid #364152;border-radius:14px;background:linear-gradient(110deg,#1f2937,#111827)}}
h1{{font-size:clamp(1.65rem,4vw,2.5rem);margin:0 0 10px}}.eyebrow{{color:#b3c0d6;font-size:.75rem;letter-spacing:.15em;text-transform:uppercase}}
.sub{{color:#b8c1cd;line-height:1.55}}.stats{{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}}
.stat{{background:#1d2939;border:1px solid #364152;border-radius:10px;min-width:170px;flex:1;padding:16px}}.num{{font-size:2rem;font-weight:700;display:block}}.stat small{{color:#c3cbd6}}
h2{{font-size:1.15rem;margin:10px 0}}.incident{{margin:16px 0;padding:23px;background:#1b2432;border:1px solid #394557;border-radius:12px;line-height:1.55}}
.incident header{{display:flex;gap:10px;align-items:center}}.tag{{display:inline-block;border-radius:4px;padding:3px 9px;font-size:.72rem;font-weight:800;letter-spacing:.04em;color:#fff}}
.critical{{background:#9f253c}}.high{{background:#a54d22}}.medium{{background:#8a6a1a}}.low{{background:#325b68}}
.rule{{color:#afbbc9;font-size:.76rem;letter-spacing:.04em}}.meta{{font-size:.85rem;color:#b8c6d5}}.incident p{{overflow-wrap:anywhere}}details{{border-top:1px solid #3c4857;margin-top:12px;padding-top:12px}}summary{{cursor:pointer;color:#d6e4fa}}
footer{{color:#a6b0c0;font-size:.82rem;margin-top:24px}}.empty{{padding:24px;background:#263248;border-radius:8px}}
</style></head><body><main><section class="hero"><div class="eyebrow">IAM Security Engineering / Portfolio Demo</div>
<h1>Identity Incident Investigator</h1><p class="sub">Read-only correlation across identity systems. Deterministic evidence first; optional local AI hypotheses. This sample report uses fictional data.</p></section>
<section class="stats"><div class="stat"><span class="num">{e(payload['input_event_count'])}</span><small>Events ingested</small></div>
<div class="stat"><span class="num">{e(payload['incident_count'])}</span><small>Incident patterns</small></div>
<div class="stat"><span class="num">{e(payload['by_severity'].get('high', 0) + payload['by_severity'].get('critical', 0))}</span><small>High / critical</small></div></section>
<h2>Evidence-backed findings</h2>{body}
<footer>Generated {e(payload['generated_at_utc'])} · Analyst verification required · No access changes performed · Synthetic data only</footer>
</main></body></html>'''
