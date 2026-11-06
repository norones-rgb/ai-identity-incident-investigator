"""Optional interactive Streamlit interface. No external calls unless Ollama is selected."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from identity_investigator.ingest import InputError, parse_events
from identity_investigator.narrative import baseline_explanation, ollama_explanation
from identity_investigator.reporting import csv_report, html_report, json_report, report_data
from identity_investigator.rules import correlate

st.set_page_config(page_title="Identity Incident Investigator", page_icon="🔎", layout="wide")
st.title("🔎 Identity Incident Investigator")
st.caption("Read-only IAM security analytics • Evidence before AI • Portfolio demonstration")
st.warning("Use synthetic or expressly authorized test data only. Uploaded event data stays in this Streamlit process. Don't expose this demo publicly with real identity logs.")

left, right = st.columns([2, 1])
with left:
    upload = st.file_uploader("Load UTF-8 identity events (.csv / .json)", type=["csv", "json"])
with right:
    st.markdown("**Local explanation engine**")
    use_ai = st.checkbox("Enable local Ollama (opt-in)", value=False)
    model = st.text_input("Installed Ollama model", "llama3.2:3b", disabled=not use_ai)

if upload is not None:
    raw, filename = upload.getvalue(), upload.name
else:
    raw = (Path(__file__).parent / "samples" / "synthetic_identity_events.csv").read_bytes()
    filename = "synthetic_identity_events.csv"
    st.info("Showing bundled fictional incident data. Upload a dataset to replace it.")

try:
    events = parse_events(raw, filename)
    incidents = correlate(events)
except InputError as exc:
    st.error(f"Input validation failed: {exc}")
    st.stop()

metrics = st.columns(4)
metrics[0].metric("Events", len(events))
metrics[1].metric("Incidents", len(incidents))
metrics[2].metric("High / critical", sum(x.severity in ("high", "critical") for x in incidents))
metrics[3].metric("Systems", len({e.source for e in events}))

if incidents:
    st.subheader("Correlated incident patterns")
    st.dataframe([{"Incident": x.incident_id, "Severity": x.severity.upper(), "Rule": x.rule_id,
                   "Subject": x.subject, "Evidence events": len(x.evidence), "Confidence": x.confidence}
                  for x in incidents], hide_index=True, use_container_width=True)
    choice = st.selectbox("Inspect finding", options=range(len(incidents)),
                          format_func=lambda n: f"{incidents[n].severity.upper()} — {incidents[n].title}")
    incident = incidents[choice]
    st.markdown(f"### {incident.title}")
    st.write(incident.summary)
    st.markdown("**Analyst verification:** " + incident.recommendation)
    related = [e.to_dict() for e in events if e.event_id in incident.evidence]
    with st.expander(f"Evidence timeline ({len(related)} events)", expanded=True):
        st.dataframe([{k: row[k] for k in ("timestamp", "event_id", "source", "subject", "action", "outcome")}
                      for row in related], hide_index=True, use_container_width=True)
    st.markdown("**Narrative**")
    st.info(baseline_explanation(incident))
    if use_ai and st.button("Generate local AI draft for selected incident"):
        try:
            st.markdown("**Local model draft — analyst review required**")
            st.write(ollama_explanation(incident, model=model))
        except (RuntimeError, ValueError) as exc:
            st.error(str(exc))
else:
    st.success("No events matched the available correlation rules. This does not establish that identities are secure.")

payload = report_data(events, incidents, {i.incident_id: baseline_explanation(i) for i in incidents})
st.subheader("Export findings")
a, b, c = st.columns(3)
a.download_button("Download HTML report", html_report(payload), file_name="incident-report.html", mime="text/html")
b.download_button("Download JSON report", json_report(payload), file_name="incident-report.json", mime="application/json")
c.download_button("Download CSV report", csv_report(incidents), file_name="incident-report.csv", mime="text/csv")
st.caption("Five transparent detection rules. No live tenant connections, account changes, or background collection.")
