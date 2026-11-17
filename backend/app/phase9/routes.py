from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .db import database_ready, session_scope
from .models import AuditLog, Evidence, User
from .persistence import claim_event
from .security import current_user, issue_token, password_matches, require_roles


router = APIRouter(tags=["phase9"])


class TokenRequest(BaseModel):
    username: str
    password: str


class EventRequest(BaseModel):
    event_id: str
    idempotency_key: str
    camera_id: str
    event_type: str
    payload: dict = Field(default_factory=dict)


@router.post("/auth/token")
def token(request: TokenRequest) -> dict:
    try:
        with session_scope() as session:
            user = session.query(User).filter_by(username=request.username, enabled=True).one_or_none()
            if not user or not password_matches(request.password, user.password_hash):
                raise HTTPException(status_code=401, detail="invalid credentials")
            return {"access_token": issue_token(user.username, user.role), "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="authentication database unavailable") from exc


@router.get("/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {"username": user["sub"], "role": user["role"]}


@router.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    if not database_ready():
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", "database": "ok"}


@router.post("/api/phase9/events", status_code=201)
def create_event(request: EventRequest, user: dict = Depends(require_roles("admin", "operator"))) -> dict:
    try:
        created = claim_event(request.event_id, request.idempotency_key, request.camera_id, request.event_type, request.payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="event database unavailable") from exc
    if not created:
        return {"event_id": request.event_id, "created": False, "duplicate": True}
    return {"event_id": request.event_id, "created": True, "actor": user["sub"]}


@router.post("/api/phase9/evidence")
async def upload_evidence(file: Annotated[UploadFile, File(...)], user: dict = Depends(require_roles("admin", "operator"))) -> dict:
    from .evidence import EvidenceStore
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        result = EvidenceStore(os.environ.get("EVIDENCE_ROOT", "storage/evidence")).write("uploads", file.filename or "upload", content, file.content_type or "")
        with session_scope() as session:
            session.add(Evidence(event_id="uploads", object_uri=result["path"], sha256=result["sha256"], content_type=result["content_type"], byte_size=result["byte_size"], retention_deadline=datetime.now(timezone.utc) + timedelta(days=7), deleted=False))
            session.add(AuditLog(actor=user["sub"], action="evidence.upload", resource=result["path"], detail="{}"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {**result, "actor": user["sub"]}
