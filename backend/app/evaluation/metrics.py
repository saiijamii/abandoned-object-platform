from collections import defaultdict


def precision_recall(true_positive: int, false_positive: int, false_negative: int) -> dict[str, float]:
    return {
        "precision": true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0,
        "recall": true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0,
    }


def summarize_slices(rows: list[dict]) -> dict[str, dict[str, float]]:
    counts = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        for tag in str(row.get("tags", "")).split(";"):
            if tag:
                counts[tag][0] += int(row.get("true_positive", 0))
                counts[tag][1] += int(row.get("false_positive", 0))
                counts[tag][2] += int(row.get("false_negative", 0))
    return {tag: precision_recall(*values) for tag, values in counts.items()}
