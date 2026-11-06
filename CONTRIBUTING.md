# Contributing

Contributions that improve evidence quality, test coverage and clear safety boundaries are welcome.

1. Use synthetic examples only; never include real names, logs, email addresses, IDs, tokens or vendor exports with personal data.
2. Add a focused unittest for a new detection rule, parsing edge case or output format.
3. Keep the tool read-only. Do not add automatic remediation or silent external services.
4. Document rule thresholds and evidence semantics. Describe model-generated observations as hypotheses.
5. Run `python -m unittest discover -s tests -v` before a PR.

For significant behavior changes, open an issue explaining the use case and false-positive considerations.
