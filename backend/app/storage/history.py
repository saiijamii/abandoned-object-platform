import json
from pathlib import Path
from typing import Any


class JsonlHistory:
    def __init__(self, root: str | Path = "storage") -> None:
        self.root = Path(root)

    def append(self, camera_id: str, session_id: str, name: str, value: dict[str, Any]) -> None:
        directory = self.root / "cameras" / camera_id / "sessions" / session_id
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / name).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value) + "\n")

    def read(self, camera_id: str, session_id: str, name: str) -> list[dict[str, Any]]:
        path = self.root / "cameras" / camera_id / "sessions" / session_id / name
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []
