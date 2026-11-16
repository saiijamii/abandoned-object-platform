import json
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, root: str | Path = "storage/index") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, collection: str, identifier: str, value: dict[str, Any]) -> None:
        directory = self.root / collection
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{identifier}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")

    def list(self, collection: str) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((self.root / collection).glob("*.json"))] if (self.root / collection).exists() else []

    def get(self, collection: str, identifier: str) -> dict[str, Any] | None:
        path = self.root / collection / f"{identifier}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
