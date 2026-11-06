# Threat model (MVP)

**Assets:** source event files, employee/account identifiers in uploaded files, generated reports, the analyst workstation, and optionally a local model endpoint.

**Trust boundaries:** untrusted/third-party event files enter a local parser; data is summarized into fixed rules; output files may be opened in a browser or spreadsheet; an explicitly selected model may receive a **minimized** incident summary over loopback HTTP.

| Risk | Mitigation in this MVP | Residual risk |
| --- | --- | --- |
| Secrets or PII disclosed to remote AI | No cloud model integration, fixed localhost model URL, minimized model prompt, explicit opt-in | Publicly hosting the UI could expose data to server operators; local Ollama may log model requests |
| HTML script injection from event text | HTML escaping, static no-script report, restrictive CSP | Browser differences and new output templates still require testing |
| Spreadsheet formula injection | Prefix `'` for cells starting formula operators, including leading whitespace | Some spreadsheet parsers differ; verify before distributing externally |
| Malformed / oversized input | 2 MiB / 10,000 event limits, schema checks, duplicate ID rejection | In-memory parsing and crafted JSON can still consume resources; not hardened for hostile multi-tenant uploads |
| Prompt injection | LLM sees only internal rule summary and aggregate counts, no user-controlled raw fields | LLM may still hallucinate; output requires analyst verification |
| False positives / mistaken automated response | Evidence references, conservative phrasing, no remediation or write connector | Analysts could still over-trust severity or confidence labels |
| Log poisoning / synthetic spoofing | Explicit evidence IDs, stable deterministic rules | Input authenticity and source integrity are not verified |
| Identity correlation errors | Exact-match subjects; source labels preserved | Alias changes, reused identifiers and cross-system delays can cause missed or duplicate alerts |
| Sensitive report exposure | Reports created locally; generated `reports/` gitignored | Analyst controls file permissions, sharing and retention |

## Not implemented / prerequisites before production

- Authentication, authorization, tenant scoping, secure secrets management and audit logs for the UI.
- Vendor API connectors, source authentication, evidence integrity, chain of custody, and operational alert routing.
- Rate limiting, model resource caps, data retention controls, enterprise logging or SIEM integration.
- Rule tuning against labeled datasets, statistically grounded scoring and external security evaluation.
- Disaster recovery and a supportable upgrade/patch process.

## Explicit exclusions

This repository contains no credential harvesting, live exploitation, user account mutation, bulk collection, automatic disabling or persistence mechanism.
