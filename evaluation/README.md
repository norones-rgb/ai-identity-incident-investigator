# Synthetic incident fixture evaluation

Run from the repository root:

```bash
python -m evaluation.evaluate
```

The script compares **exact rule ID + subject + complete evidence event-ID set** against a small hand-specified fixture. It also checks that four unrelated events yield no findings. It exits nonzero if a scenario regresses.

| Measure | Result on authored synthetic fixture |
| --- | ---: |
| Events | **29** |
| Expected signatures | **5** |
| Exact matches | **5 / 5** |
| Unexpected or missed signatures | **0 / 0** |
| Negative controls producing alerts | **0 / 4** |

**Important:** This is a regression check on synthetic scenarios designed for these rules, **not** independent precision/recall, security coverage, or estimated false-positive rate in real IAM data. Neither the optional local LLM's reasoning nor operational performance is evaluated. Avoid presenting the fixture match as a production accuracy claim.

Next: independently labeled benign and malicious sequences, identity-alias tests, overlapping windows, noisy tenant telemetry, and measured alert rates.
