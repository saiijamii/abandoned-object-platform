import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.evaluation.dataset import split_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare leakage-safe YOLO dataset splits.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--classes", nargs=2, default=["person", "bag"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    with Path(args.manifest).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    splits = split_manifest(rows, args.seed)
    output = Path(args.output)
    for split, split_rows in splits.items():
        for row in split_rows:
            image, label = Path(row["image_path"]), Path(row["label_path"])
            stem = f"{row['group_id']}_{image.stem}"
            image_target, label_target = output / split / "images" / f"{stem}{image.suffix}", output / split / "labels" / f"{stem}.txt"
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, image_target)
            shutil.copy2(label, label_target)
    (output / "split_manifest.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
    (output / "data.yaml").write_text(f"path: {output.resolve()}\ntrain: train/images\nval: valid/images\ntest: test/images\nnames: {args.classes}\n", encoding="utf-8")
    print(json.dumps({name: len(values) for name, values in splits.items()}, indent=2))


if __name__ == "__main__":
    main()
