from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.database import COLL_AUDIT_LOG, DatabaseClient, list_documents
from app.dependencies import get_firestore_db

router = APIRouter()


def _safe_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/audit-log")
def get_audit_log(
    merchant_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: DatabaseClient = Depends(get_firestore_db),
):
    rows = list_documents(db, COLL_AUDIT_LOG, order_by="timestamp", descending=True, limit=5000)

    from_dt = _safe_datetime(from_date) if from_date else None
    to_dt = _safe_datetime(to_date) if to_date else None

    filtered = []
    for row in rows:
        row_ts = _safe_datetime(row.get("timestamp"))
        if merchant_id and str(row.get("actor_id") or "") != merchant_id:
            continue
        if action and str(row.get("action") or "") != action:
            continue
        if outcome and str(row.get("outcome") or "") != outcome:
            continue
        if from_dt and row_ts and row_ts < from_dt:
            continue
        if to_dt and row_ts and row_ts > to_dt:
            continue

        filtered.append(
            {
                "log_id": row.get("log_id") or row.get("id"),
                "timestamp": row.get("timestamp"),
                "actor_type": row.get("actor_type"),
                "actor_id": row.get("actor_id"),
                "action": row.get("action"),
                "entity_id": row.get("entity_id"),
                "amount": row.get("amount"),
                "token_id": row.get("token_id"),
                "outcome": row.get("outcome"),
                "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            }
        )

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "filters_applied": {
            "merchant_id": merchant_id,
            "action": action,
            "outcome": outcome,
            "from_date": from_date,
            "to_date": to_date,
        },
        "entries": filtered[start:end],
    }
