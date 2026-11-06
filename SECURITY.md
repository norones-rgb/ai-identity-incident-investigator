# Security policy

This project is a **read-only portfolio demonstration**. It is not supported as production security software and does not offer any live SaaS / tenant connection. Please avoid submitting confidential information, access tokens, identifiable employees, or real event logs in issues or pull requests.

## Supported versions

| Version | Status |
| --- | --- |
| 0.1.x | Educational/demo fixes as maintained |

## Reporting vulnerabilities

Open a GitHub private vulnerability report if security advisories are enabled on the repository, or contact the repository maintainer privately through their preferred published contact method. Do not include secrets or actual employee data in a public issue.

## Safe development and test policy

- Use `samples/` data or fabricated identities under `example.invalid`.
- Never commit `.env`, reports derived from real data, API credentials, or customer exports.
- If you run the optional Streamlit UI, keep it on a trusted machine/network; Streamlit does not supply the enterprise multi-tenant access controls this use case requires.
- Local Ollama is optional and explicitly selected; no data is sent to a remote API by this code. Verify who operates your model server before processing sensitive data.
- Validate findings and context before taking any operational action.
