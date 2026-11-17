import os

from .embedder import ClipEmbedder, FakeEmbedder, ImageEmbedder
from .store import SQLiteVectorStore
from .types import SearchDomain


class VisualSearchService:
    def __init__(self, store: SQLiteVectorStore, embedder: ImageEmbedder, max_bytes: int = 8 * 1024 * 1024, max_top_k: int = 100) -> None:
        self.store, self.embedder, self.max_bytes, self.max_top_k = store, embedder, max_bytes, max_top_k

    def search(self, domain: SearchDomain, image_bytes: bytes, top_k: int = 20, camera_id: str | None = None, min_media_ts: float | None = None, max_media_ts: float | None = None) -> dict:
        if not image_bytes or len(image_bytes) > self.max_bytes:
            raise ValueError("image is empty or exceeds upload limit")
        if _image_type(image_bytes) not in {"jpeg", "png", "webp"}:
            raise ValueError("unsupported image type")
        if not 1 <= top_k <= self.max_top_k:
            raise ValueError(f"top_k must be between 1 and {self.max_top_k}")
        embedding = self.embedder.embed(image_bytes)
        matches = self.store.search(domain, embedding, top_k, camera_id, min_media_ts, max_media_ts)
        return {"query_domain": domain.value, "identity_assertion": False, "candidate_matches": [match.as_dict() for match in matches]}


def create_search_service() -> VisualSearchService:
    path = os.environ.get("SEARCH_DB_PATH", "storage/search/search.sqlite3")
    if os.environ.get("SEARCH_EMBEDDER", "fake") == "fake":
        embedder = FakeEmbedder()
    else:
        embedder = ClipEmbedder(os.environ.get("SEARCH_EMBEDDING_MODEL", "openai/clip-vit-base-patch32"), os.environ.get("SEARCH_DEVICE", "cpu"))
    return VisualSearchService(SQLiteVectorStore(path), embedder)


def _image_type(value: bytes) -> str | None:
    if value.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if value.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if value.startswith(b"RIFF") and value[8:12] == b"WEBP":
        return "webp"
    return None
