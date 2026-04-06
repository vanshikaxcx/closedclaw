from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.database import COLL_NOTIFICATIONS, DatabaseClient, upsert_document, utc_now_iso


def create_notification(
    db: DatabaseClient,
    merchant_id: str,
    notif_type: str,
    title: str,
    body: str,
    action_url: str | None = None,
    whatsapp_sent: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    notif_id = str(uuid4())
    payload = {
        "notif_id": notif_id,
        "merchant_id": merchant_id,
        "type": notif_type,
        "title": title,
        "body": body,
        "read": False,
        "timestamp": utc_now_iso(),
        "action_url": action_url,
        "whatsapp_sent": whatsapp_sent,
    }
    if extra:
        payload.update(extra)

    upsert_document(db, COLL_NOTIFICATIONS, notif_id, payload, merge=False)
    return payload
