from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.database import COLL_AUDIT_LOG, DatabaseClient, upsert_document, utc_now_iso


def write_entry(
    db: DatabaseClient,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_id: str | None = None,
    amount: float | None = None,
    token_id: str | None = None,
    outcome: str = "success",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    log_id = str(uuid4())
    payload = {
        "log_id": log_id,
        "timestamp": utc_now_iso(),
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "entity_id": entity_id,
        "amount": amount,
        "token_id": token_id,
        "outcome": outcome,
        "metadata": metadata or {},
    }
    upsert_document(db, COLL_AUDIT_LOG, log_id, payload, merge=False)
    return payload
