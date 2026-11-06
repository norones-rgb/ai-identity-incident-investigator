"""Strict ingestion: JSON arrays or CSV with a JSON-encoded metadata column."""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Event

MAX_BYTES = 2 * 1024 * 1024
MAX_EVENTS = 10000
REQUIRED = {"event_id", "timestamp", "source", "subject", "action", "outcome"}
SAFE_ACTION = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ALLOWED_OUTCOMES = {"success", "failure", "info"}


class InputError(ValueError):
    """Invalid or unsafe event input."""


def _string(item: dict[str, Any], key: str, limit: int = 160) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InputError(f"{key} must be a nonempty string (max {limit} characters)")
    if any(ord(ch) < 32 for ch in value):
        raise InputError(f"{key} contains control characters")
    return value.strip()


def _parse_one(item: Any, row: int) -> Event:
    if not isinstance(item, dict):
        raise InputError(f"Row {row}: expected an object")
    absent = REQUIRED.difference(item)
    if absent:
        raise InputError(f"Row {row}: missing {', '.join(sorted(absent))}")
    try:
        raw_time = _string(item, "timestamp", 40)
        stamp = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("timezone offset required")
        stamp = stamp.astimezone(timezone.utc)
        action = _string(item, "action", 64)
        if not SAFE_ACTION.fullmatch(action):
            raise InputError("action must be lowercase snake_case")
        outcome = _string(item, "outcome", 20)
        if outcome not in ALLOWED_OUTCOMES:
            raise InputError("outcome must be success, failure, or info")
        metadata = item.get("metadata", {})
        if "metadata_json" in item:
            metadata = json.loads(item["metadata_json"] or "{}")
        if not isinstance(metadata, dict):
            raise InputError("metadata must be a JSON object")
        if len(json.dumps(metadata)) > 2048:
            raise InputError("metadata exceeds 2048 characters")
        resource = item.get("resource", "") or ""
        actor = item.get("actor", "") or ""
        if not isinstance(resource, str) or len(resource) > 160:
            raise InputError("resource must be a string (max 160 characters)")
        if not isinstance(actor, str) or len(actor) > 160:
            raise InputError("actor must be a string (max 160 characters)")
        return Event(
            event_id=_string(item, "event_id", 120), timestamp=stamp,
            source=_string(item, "source", 80), subject=_string(item, "subject"),
            action=action, outcome=outcome, resource=resource, actor=actor,
            metadata=metadata,
        )
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise InputError(f"Row {row}: {exc}") from exc


def parse_events(data: bytes, filename: str) -> list[Event]:
    """Parse input entirely in memory, bounding size and record count."""
    if len(data) > MAX_BYTES:
        raise InputError(f"File exceeds the {MAX_BYTES // (1024*1024)} MiB limit")
    if not data:
        raise InputError("File is empty")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError("File must be UTF-8") from exc
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".json":
            records = json.loads(content)
            if isinstance(records, dict):
                records = records.get("events")
        elif suffix == ".csv":
            reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
            if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
                raise InputError("CSV must contain: " + ", ".join(sorted(REQUIRED)))
            records = list(reader)
        else:
            raise InputError("Only .csv or .json input is accepted")
    except (csv.Error, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot parse file: {exc}") from exc
    if not isinstance(records, list) or not records:
        raise InputError("Expected a nonempty list of events")
    if len(records) > MAX_EVENTS:
        raise InputError(f"More than {MAX_EVENTS} events are not supported")
    events = [_parse_one(record, i) for i, record in enumerate(records, start=1)]
    ids = [event.event_id for event in events]
    if len(ids) != len(set(ids)):
        raise InputError("Duplicate event_id values are not allowed")
    return sorted(events, key=lambda e: (e.timestamp, e.event_id))
