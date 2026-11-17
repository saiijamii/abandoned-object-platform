import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable

VALID_CLASSES = {0, 1}


def validate_label_file(path: str | Path) -> None:
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        values = line.split()
        if not values:
            continue
        if len(values) != 5:
            raise ValueError(f"{path}:{line_number}: expected class and four coordinates")
        class_id = int(values[0])
        if class_id not in VALID_CLASSES:
            raise ValueError(f"{path}:{line_number}: class must be 0 or 1")
        coordinates = [float(value) for value in values[1:]]
        if any(value < 0 or value > 1 for value in coordinates):
            raise ValueError(f"{path}:{line_number}: coordinates must be normalized")


def split_manifest(rows: Iterable[dict], seed: int = 42, fractions: dict[str, float] | None = None) -> dict[str, list[dict]]:
    fractions = fractions or {"train": .70, "valid": .15, "test": .15}
    if abs(sum(fractions.values()) - 1) > .001:
        raise ValueError("split fractions must sum to 1")
    groups = defaultdict(list)
    for row in rows:
        group_id = row.get("group_id", "").strip()
        if not group_id:
            raise ValueError("group_id is required")
        image, label = Path(row["image_path"]), Path(row["label_path"])
        if not image.is_file() or not label.is_file():
            raise FileNotFoundError(f"missing image or label for {image}")
        validate_label_file(label)
        groups[group_id].append(row)
    result = {name: [] for name in fractions}
    sizes = {name: 0 for name in fractions}
    order = list(groups)
    random.Random(seed).shuffle(order)
    for group_id in order:
        target = min(fractions, key=lambda name: sizes[name] / fractions[name])
        result[target].extend(groups[group_id])
        sizes[target] += len(groups[group_id])
    return result
