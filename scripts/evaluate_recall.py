import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.detection.types import Detection
from app.evaluation import precision_recall, score_frame


def read_rows(path: str) -> dict[int, list[Detection]]:
    grouped = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped.setdefault(int(row["frame_index"]), []).append(Detection(row["class_name"], float(row.get("confidence", 1)), tuple(int(float(row[key])) for key in ("x1", "y1", "x2", "y2"))))
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate person/luggage recall from CSV boxes.")
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", default="storage/evaluation/recall.json")
    parser.add_argument("--iou", type=float, default=.5)
    args = parser.parse_args()
    truth, predictions = read_rows(args.ground_truth), read_rows(args.predictions)
    counts = Counter()
    for frame_index in set(truth) | set(predictions):
        counts.update(score_frame(predictions.get(frame_index, []), truth.get(frame_index, []), args.iou))
    report = {"iou_threshold": args.iou, "frames_evaluated": len(truth), "person": precision_recall(counts, "person"), "luggage": precision_recall(counts, "luggage")}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
