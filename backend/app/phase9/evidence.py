from __future__ import annotations

import hashlib
import os
from pathlib import Path


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class EvidenceStore:
    def __init__(self, root: str | Path = "storage/evidence") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, event_id: str, filename: str, content: bytes, content_type: str) -> dict:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("unsupported content type")
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("evidence file exceeds 10 MiB")
        safe_name = Path(filename).name
        if not safe_name or safe_name != filename:
            raise ValueError("invalid evidence filename")
        directory = (self.root / event_id).resolve()
        if self.root not in directory.parents:
            raise ValueError("invalid evidence path")
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / safe_name
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)
        return {"path": str(target), "sha256": hashlib.sha256(content).hexdigest(), "content_type": content_type, "byte_size": len(content)}
