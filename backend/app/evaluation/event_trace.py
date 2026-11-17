import json
from pathlib import Path
from typing import Iterable

REQUIRED_EVIDENCE = ("frame_path", "annotated_path", "bag_crop_path", "metadata_path")


def validate_trace(rows: Iterable[dict], separation_seconds: float = 2.0) -> list[str]:
    errors, starts, emitted = [], {}, set()
    for row in sorted(rows, key=lambda item: float(item.get("media_ts", 0))):
        bag_id, timestamp = row.get("bag_track_id"), float(row.get("media_ts", 0))
        associated, separated, stationary = bool(row.get("associated")), bool(row.get("separated")), bool(row.get("stationary"))
        if associated and separated:
            starts.setdefault(bag_id, timestamp)
        else:
            starts.pop(bag_id, None)
        event_id = row.get("event_id")
        if not event_id:
            continue
        if event_id in emitted:
            errors.append(f"duplicate event: {event_id}")
        emitted.add(event_id)
        if not associated:
            errors.append(f"event without association: {event_id}")
        if not separated:
            errors.append(f"event without separation: {event_id}")
        if not stationary:
            errors.append(f"event without stationarity: {event_id}")
        if bag_id not in starts or timestamp - starts[bag_id] < separation_seconds:
            errors.append(f"event before separation threshold: {event_id}")
        for field in REQUIRED_EVIDENCE:
            if not row.get(field):
                errors.append(f"missing {field}: {event_id}")
        if row.get("owner_visible") and not row.get("owner_crop_path"):
            errors.append(f"missing owner crop: {event_id}")
    return errors


def validate_trace_file(path: str | Path, separation_seconds: float = 2.0) -> list[str]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return validate_trace(rows, separation_seconds)
