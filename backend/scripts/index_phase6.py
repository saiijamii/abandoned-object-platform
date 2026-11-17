import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.search.embedder import ClipEmbedder, FakeEmbedder
from app.search.indexer import index_events
from app.search.store import SQLiteVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Phase Five event crops for visual search.")
    parser.add_argument("--storage-root", default="storage")
    args = parser.parse_args()
    embedder = FakeEmbedder() if os.environ.get("SEARCH_EMBEDDER", "fake") == "fake" else ClipEmbedder()
    count = index_events(args.storage_root, SQLiteVectorStore(os.environ.get("SEARCH_DB_PATH", "storage/search/search.sqlite3")), embedder)
    print(f"indexed observations: {count}")


if __name__ == "__main__":
    main()
