import json
from pathlib import Path

from .embedder import ImageEmbedder
from .store import SQLiteVectorStore
from .types import ObservationRecord, SearchDomain


def index_events(storage_root: str | Path, store: SQLiteVectorStore, embedder: ImageEmbedder) -> int:
    root = Path(storage_root) / "cameras"
    indexed = 0
    for metadata_path in root.rglob("metadata.json") if root.exists() else []:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        camera_id = metadata.get("camera_id", metadata_path.parents[4].name)
        session_id = metadata.get("session_id", metadata_path.parents[2].name)
        event_id = metadata.get("event_id", metadata_path.parent.name)
        timestamp = float(metadata.get("timestamp_s", 0))
        for domain, field, track_key in ((SearchDomain.BAG, "bag_crop_path", "bag_track_id"), (SearchDomain.PERSON, "owner_crop_path", "owner_track_id")):
            crop_value = metadata.get(field)
            if not crop_value:
                continue
            crop = Path(crop_value)
            if not crop.is_absolute():
                crop = metadata_path.parent / crop
            if not crop.is_file():
                continue
            observation_id = f"{event_id}:{domain.value}"
            store.upsert(ObservationRecord(observation_id, domain, camera_id, session_id, str(metadata.get(track_key) or ""), event_id, timestamp, str(crop), metadata.get("raw_snapshot_path"), embedder.embed(crop.read_bytes())))
            indexed += 1
    return indexed
