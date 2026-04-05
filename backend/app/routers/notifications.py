from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import COLL_NOTIFICATIONS, DatabaseClient, get_document, list_documents, upsert_document
from app.dependencies import get_firestore_db
from app.schemas import NotificationReadAllRequest

router = APIRouter()


@router.get("/notifications")
def get_notifications(
    merchant_id: str = Query(...),
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_firestore_db),
):
    rows = list_documents(
        db,
        COLL_NOTIFICATIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=True,
        limit=5000,
    )

    if unread_only:
        rows = [row for row in rows if not bool(row.get("read"))]

    total = len(rows)
    unread_count = sum(1 for row in rows if not bool(row.get("read"))) if unread_only else sum(
        1
        for row in list_documents(db, COLL_NOTIFICATIONS, filters=[("merchant_id", "==", merchant_id)], limit=5000)
        if not bool(row.get("read"))
    )

    start = (page - 1) * page_size
    end = start + page_size

    notifications = [
        {
            "notif_id": row.get("notif_id") or row.get("id"),
            "type": row.get("type") or "alert",
            "title": row.get("title") or "",
            "body": row.get("body") or "",
            "read": bool(row.get("read")),
            "timestamp": row.get("timestamp") or "",
            "action_url": row.get("action_url"),
            "whatsapp_sent": bool(row.get("whatsapp_sent") or False),
        }
        for row in rows[start:end]
    ]

    return {
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
        "notifications": notifications,
    }


@router.post("/notifications/{notif_id}/read")
def post_mark_notification_read(
    notif_id: str,
    merchant_id: str = Query(...),
    db: DatabaseClient = Depends(get_firestore_db),
):
    row = get_document(db, COLL_NOTIFICATIONS, notif_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "notification_not_found", "notif_id": notif_id})

    if str(row.get("merchant_id") or "") != merchant_id:
        raise HTTPException(status_code=403, detail={"error": "notification_not_owned"})

    upsert_document(db, COLL_NOTIFICATIONS, notif_id, {"read": True}, merge=True)
    return {"notif_id": notif_id, "read": True}


@router.post("/notifications/read-all")
def post_mark_all_notifications_read(body: NotificationReadAllRequest, db: DatabaseClient = Depends(get_firestore_db)):
    rows = list_documents(db, COLL_NOTIFICATIONS, filters=[("merchant_id", "==", body.merchant_id)], limit=5000)

    marked = 0
    for row in rows:
        notif_id = str(row.get("notif_id") or row.get("id"))
        if notif_id and not bool(row.get("read")):
            upsert_document(db, COLL_NOTIFICATIONS, notif_id, {"read": True}, merge=True)
            marked += 1

    return {"merchant_id": body.merchant_id, "marked_read": marked}
