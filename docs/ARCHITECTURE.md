# Architecture and design decisions

## Pipeline

1. **Ingestion** accepts UTF-8 `.csv` / `.json` (2 MiB, 10,000 events). It validates required fields, rejects malformed metadata and duplicate IDs, parses timezone-aware timestamps, and sorts events into UTC.
2. **Normalization** creates immutable `Event` models. All sources are deliberately synthetic and follow one normalized schema. Future vendor adapters should produce these models without changing detection rules.
3. **Correlation** uses five readable rules with explicit thresholds and time windows. Each `Incident` embeds the exact `event_id` values supporting it and deterministic content-derived IDs. An analyst can reproduce alerts from the same file.
4. **Explanation** produces a deterministic, audit-friendly narrative by default. A local Ollama LLM can optionally draft a concise hypothesis from **only** low-detail statistical and rule descriptions. LLM output is neither classified as truth nor used by a rule.
5. **Reports** render a standalone offline HTML page (no JS, no external assets), JSON with a documented schema version, and CSV with spreadsheet-formula guards. All data derived from a file is escaped in HTML.

## Design boundaries

- **No cloud AI by default.** The only model endpoint is a fixed loopback address and requires opt-in. Use model calls only on a trusted host, not in a public shared Streamlit deployment.
- **No mutation connectors.** This MVP has no read or write integrations with real tenants. It cannot disable accounts, modify memberships or provision anything.
- **No automatic incident assertion.** Terms like *possible* and *verify* are intentional. A correlation is observable; causality and intent are often not.
- **No hidden risk score.** Priorities are rule-derived (`critical`, `high`, `medium`) and evidence confidence is qualitative.
- **No sensitive dataset in source control.** The fixture uses reserved `example.invalid` identities, invented systems and made-up event records.

## Testing strategy

`python -m unittest discover -s tests -v` covers equivalent CSV/JSON inputs, invalid/timezone-less data, duplicates, size validation, all five rules, false-positive sanity checks, stable incident IDs, report outputs, HTML escaping, CSV formula injection, model-input minimization, local model-name checks, and CLI execution.

## Output definitions

- `schema_version`: current major report shape (`1.0`).
- `read_only`: boolean; always true in this version.
- `input_event_count`, `incident_count`, `by_severity`: analysis overview.
- `incidents`: `incident_id`, `rule_id`, `title`, `severity`, `confidence`, `subject`, `start`, `end`, `summary`, `recommendation`, `evidence`, `sources`, `narrative`.

Report contents reflect the input, which can contain identifiers. Share generated reports only with people permitted to view the events.
