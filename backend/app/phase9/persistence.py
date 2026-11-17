from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from .db import session_scope
from .models import AuditLog, Event, ProcessingSession


def claim_event(event_id: str, idempotency_key: str, camera_id: str, event_type: str, payload: dict) -> bool:
    try:
        with session_scope() as session:
            session.add(Event(event_id=event_id, idempotency_key=idempotency_key, camera_id=camera_id, event_type=event_type, payload=json.dumps(payload)))
            session.add(AuditLog(actor=None, action="event.created", resource=event_id, detail=json.dumps({"camera_id": camera_id})))
        return True
    except IntegrityError:
        return False


def recover_running_sessions() -> int:
    with session_scope() as session:
        result = session.execute(update(ProcessingSession).where(ProcessingSession.status == "running").values(status="interrupted", ended_at=datetime.now(timezone.utc)))
        return result.rowcount or 0
