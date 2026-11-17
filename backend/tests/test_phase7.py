from app.evaluation.dataset import split_manifest
from app.evaluation.event_trace import validate_trace
from app.evaluation.metrics import summarize_slices


def test_group_split_has_no_leakage(tmp_path) -> None:
    rows = []
    for group in ("clip-a", "clip-b", "clip-c", "clip-d"):
        image, label = tmp_path / f"{group}.jpg", tmp_path / f"{group}.txt"
        image.write_bytes(b"image")
        label.write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        rows.append({"image_path": str(image), "label_path": str(label), "group_id": group})
    splits = split_manifest(rows)
    locations = {row["group_id"]: split for split, values in splits.items() for row in values}
    assert len(locations) == 4
    assert len(set(locations.values())) > 1


def test_event_trace_requires_two_seconds_and_evidence() -> None:
    base = {"bag_track_id": "bag", "associated": True, "separated": True, "stationary": True}
    early = {**base, "media_ts": 0, "event_id": None}
    event = {**base, "media_ts": 2.0, "event_id": "evt-1", "frame_path": "frame", "annotated_path": "annotated", "bag_crop_path": "bag", "metadata_path": "meta"}
    assert validate_trace([early, event]) == []
    assert validate_trace([{**base, "media_ts": 1.9, "event_id": "evt-1"}])


def test_duplicate_event_rejected() -> None:
    row = {"bag_track_id": "bag", "associated": True, "separated": True, "stationary": True, "media_ts": 2.0, "event_id": "evt-1", "frame_path": "frame", "annotated_path": "annotated", "bag_crop_path": "bag", "metadata_path": "meta"}
    assert any("duplicate" in error for error in validate_trace([row, {**row, "media_ts": 3.0}]))


def test_slice_metrics() -> None:
    result = summarize_slices([{"tags": "green_duffel;stationary_bag", "true_positive": 2, "false_positive": 1, "false_negative": 1}])
    assert result["green_duffel"] == {"precision": 2 / 3, "recall": 2 / 3}
