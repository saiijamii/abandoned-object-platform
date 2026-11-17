from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def purge_expired_files(root: str | Path, cutoff: datetime) -> int:
    """Delete files older than cutoff; caller records audit and DB state."""
    base = Path(root).resolve()
    removed = 0
    if not base.exists():
        return 0
    for path in base.rglob("*"):
        if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            path.unlink()
            removed += 1
    return removed
