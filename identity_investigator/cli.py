"""Command-line interface for offline investigation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from .ingest import InputError, parse_events
from .narrative import baseline_explanation, ollama_explanation
from .reporting import csv_report, html_report, json_report, report_data
from .rules import correlate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only IAM incident correlation (synthetic demo).")
    parser.add_argument("input", type=Path, help="UTF-8 CSV or JSON event file")
    parser.add_argument("--out", type=Path, default=Path("reports"), help="Output directory")
    parser.add_argument("--format", choices=["all", "html", "json", "csv"], default="all")
    parser.add_argument("--ai", choices=["none", "ollama"], default="none",
                        help="Opt into local Ollama explanations (default: none)")
    parser.add_argument("--model", default="llama3.2:3b", help="Installed local Ollama model")
    args = parser.parse_args(argv)
    try:
        events = parse_events(args.input.read_bytes(), args.input.name)
        incidents = correlate(events)
        narratives = {i.incident_id: baseline_explanation(i) for i in incidents}
        if args.ai == "ollama":
            for incident in incidents:
                try:
                    narratives[incident.incident_id] = ollama_explanation(incident, model=args.model)
                except (ValueError, RuntimeError) as exc:
                    print(f"AI unavailable for {incident.incident_id}: {exc}; using rule-based narrative", file=sys.stderr)
        payload = report_data(events, incidents, narratives)
        args.out.mkdir(parents=True, exist_ok=True)
        reports = {
            "html": ("incident-report.html", html_report(payload)),
            "json": ("incident-report.json", json_report(payload)),
            "csv": ("incident-report.csv", csv_report(incidents)),
        }
        formats = reports.keys() if args.format == "all" else (args.format,)
        for fmt in formats:
            filename, content = reports[fmt]
            (args.out / filename).write_text(content, encoding="utf-8", newline="")
        print(f"Processed {len(events)} events; identified {len(incidents)} evidence-backed incident patterns.")
        print(f"Reports saved in {args.out.resolve()}")
        return 0
    except (OSError, InputError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
