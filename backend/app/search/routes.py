import os
from functools import lru_cache

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from .service import create_search_service
from .types import SearchDomain

router = APIRouter(prefix="/api/search", tags=["visual-search"])


@lru_cache(maxsize=1)
def _service():
    return create_search_service()


def _role(role: str | None) -> None:
    required = os.environ.get("SEARCH_DEV_ROLE")
    if required and role != required:
        raise HTTPException(status_code=403, detail="operator role required")


def _query(service, domain, file, top_k, camera_id, min_media_ts, max_media_ts, role):
    _role(role)
    try:
        return service.search(domain, file, top_k, camera_id, min_media_ts, max_media_ts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/capabilities")
def capabilities() -> dict:
    return {"enabled": True, "backend": "sqlite_exact", "person": True, "bag": True, "identity_assertion": False}


@router.post("/person")
async def search_person(file: UploadFile = File(...), top_k: int = 20, camera_id: str | None = None, min_media_ts: float | None = None, max_media_ts: float | None = None, x_operator_role: str | None = Header(default=None)) -> dict:
    return _query(_service(), SearchDomain.PERSON, await file.read(), top_k, camera_id, min_media_ts, max_media_ts, x_operator_role)


@router.post("/bag")
async def search_bag(file: UploadFile = File(...), top_k: int = 20, camera_id: str | None = None, min_media_ts: float | None = None, max_media_ts: float | None = None, x_operator_role: str | None = Header(default=None)) -> dict:
    return _query(_service(), SearchDomain.BAG, await file.read(), top_k, camera_id, min_media_ts, max_media_ts, x_operator_role)
