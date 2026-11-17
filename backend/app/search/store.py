import json
import math
import sqlite3
import struct
from pathlib import Path

from .types import CandidateMatch, ObservationRecord, SearchDomain


def _pack(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def _unpack(value: bytes) -> list[float]:
    count = len(value) // 4
    return list(struct.unpack(f"<{count}f", value))


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right)) / ((sum(a * a for a in left) * sum(b * b for b in right)) ** .5 or 1.0)


class SQLiteVectorStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    track_id TEXT NOT NULL,
                    event_id TEXT,
                    media_ts REAL NOT NULL,
                    crop_path TEXT NOT NULL,
                    frame_path TEXT,
                    embedding BLOB NOT NULL,
                    dimension INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS observations_domain ON observations(domain);
                CREATE INDEX IF NOT EXISTS observations_camera_time ON observations(camera_id, media_ts);
                CREATE TABLE IF NOT EXISTS query_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    camera_id TEXT,
                    min_media_ts REAL,
                    max_media_ts REAL,
                    top_k INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _connect(self):
        return sqlite3.connect(self.path)

    def upsert(self, record: ObservationRecord) -> None:
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO observations(observation_id, domain, camera_id, session_id, track_id, event_id, media_ts, crop_path, frame_path, embedding, dimension)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(observation_id) DO UPDATE SET embedding=excluded.embedding, crop_path=excluded.crop_path, frame_path=excluded.frame_path
            """, (record.observation_id, record.domain.value, record.camera_id, record.session_id, record.track_id, record.event_id, record.media_ts, record.crop_path, record.frame_path, _pack(record.embedding), len(record.embedding)))

    def search(self, domain: SearchDomain, embedding: list[float], top_k: int, camera_id: str | None = None, min_media_ts: float | None = None, max_media_ts: float | None = None) -> list[CandidateMatch]:
        clauses, values = ["domain = ?"], [domain.value]
        if camera_id:
            clauses.append("camera_id = ?"); values.append(camera_id)
        if min_media_ts is not None:
            clauses.append("media_ts >= ?"); values.append(min_media_ts)
        if max_media_ts is not None:
            clauses.append("media_ts <= ?"); values.append(max_media_ts)
        with self._connect() as connection:
            rows = connection.execute(f"SELECT observation_id, domain, camera_id, session_id, track_id, event_id, media_ts, crop_path, frame_path, embedding FROM observations WHERE {' AND '.join(clauses)}", values).fetchall()
            connection.execute("INSERT INTO query_audit(domain, camera_id, min_media_ts, max_media_ts, top_k) VALUES (?, ?, ?, ?, ?)", (domain.value, camera_id, min_media_ts, max_media_ts, top_k))
        matches = [CandidateMatch(row[0], SearchDomain(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], row[8], cosine(embedding, _unpack(row[9]))) for row in rows]
        return sorted(matches, key=lambda item: item.similarity, reverse=True)[:top_k]

    def purge_before(self, cutoff_media_ts: float) -> int:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM observations WHERE media_ts < ?", (cutoff_media_ts,))
            return result.rowcount
