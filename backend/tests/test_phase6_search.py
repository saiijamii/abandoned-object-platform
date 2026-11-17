from app.search.embedder import FakeEmbedder
from app.search.service import VisualSearchService
from app.search.store import SQLiteVectorStore
from app.search.types import ObservationRecord, SearchDomain


def test_person_and_bag_domains_are_isolated(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "search.sqlite3")
    store.upsert(ObservationRecord("person-1", SearchDomain.PERSON, "cam", "session", "p1", None, 1, "person.jpg", None, [1.0, 0.0]))
    store.upsert(ObservationRecord("bag-1", SearchDomain.BAG, "cam", "session", "b1", None, 1, "bag.jpg", None, [1.0, 0.0]))
    assert [item.observation_id for item in store.search(SearchDomain.PERSON, [1.0, 0.0], 10)] == ["person-1"]
    assert [item.observation_id for item in store.search(SearchDomain.BAG, [1.0, 0.0], 10)] == ["bag-1"]


def test_search_ranking_filters_and_candidate_flag(tmp_path) -> None:
    service = VisualSearchService(SQLiteVectorStore(tmp_path / "search.sqlite3"), FakeEmbedder())
    service.store.upsert(ObservationRecord("bag-1", SearchDomain.BAG, "cam-a", "s", "b1", "e1", 10, "bag.jpg", None, service.embedder.embed(b"query")))
    result = service.search(SearchDomain.BAG, b"\xff\xd8\xffquery", top_k=5, camera_id="cam-a", min_media_ts=5, max_media_ts=15)
    assert result["identity_assertion"] is False
    assert result["candidate_matches"][0]["observation_id"] == "bag-1"


def test_retention_deletes_old_records(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "search.sqlite3")
    store.upsert(ObservationRecord("old", SearchDomain.BAG, "cam", "s", "b", None, 1, "bag.jpg", None, [1.0]))
    store.upsert(ObservationRecord("new", SearchDomain.BAG, "cam", "s", "b", None, 10, "bag.jpg", None, [1.0]))
    assert store.purge_before(5) == 1
    assert [item.observation_id for item in store.search(SearchDomain.BAG, [1.0], 10)] == ["new"]
