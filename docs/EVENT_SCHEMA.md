# Normalized event format

The sample fixtures are **not** raw vendor exports. This format is designed to make cross-vendor rules demonstrable while keeping source adapters separate.

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `event_id` | Yes | UTF-8 string, max 120 chars | Unique event evidence ID per file |
| `timestamp` | Yes | ISO-8601 datetime with timezone | Converted to UTC for correlation |
| `source` | Yes | String, max 80 | e.g. `NetIQ IDM`, `Entra ID`, `Okta` |
| `subject` | Yes | String, max 160 | Stable **synthetic** identity key or `SYSTEM` |
| `action` | Yes | Lowercase snake_case | Event category recognized by rules |
| `outcome` | Yes | Enum | `success`, `failure`, or `info` |
| `resource` | No | String, max 160 | Target application / connector / domain |
| `actor` | No | String, max 160 | Initiator (synthetic only) |
| `metadata` | No | JSON object, max 2048 chars | JSON input only |
| `metadata_json` | No | JSON object serialized as CSV string | CSV input only |

## Known actions

- `connector_disabled` (outcome `info`, `metadata.connector` populated)
- `provisioning_failed` (outcome `failure`, matching `metadata.connector`)
- `user_terminated` (`success`)
- `authentication_succeeded` (`success`)
- `authentication_failed` (`failure`)
- `privileged_access_granted` (`success`)
- `mfa_denied` (`failure`)
- `mfa_approved` (`success`)
- `account_disabled` (`success`)

Other lowercase snake_case events are accepted but may not participate in a detection rule.

## Example CSV row

```csv
event_id,timestamp,source,subject,action,outcome,resource,actor,metadata_json
evt-test-1,2026-11-03T08:05:00Z,NetIQ IDM,SYSTEM,connector_disabled,info,AD Connector,idm-health,"{""connector"":""NETIQ_AD""}"
```

## Correlation considerations

Exact string equality of `subject` across systems is an MVP simplification. In production, an identity-mapping adapter would need durable subject IDs and explicit alias/correlation governance. Do not join on email alone without reviewing ambiguous/mutable identifiers and privacy obligations.
