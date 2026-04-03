from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from app.database import COLL_MERCHANTS, DatabaseClient, get_db, get_document


def get_firestore_db() -> DatabaseClient:
    return get_db()


def get_merchant(
    merchant_id: str = Query(...),
    db: DatabaseClient = Depends(get_firestore_db),
) -> dict:
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=404,
            detail={"error": "merchant not found", "merchant_id": merchant_id},
        )
    return merchant


def get_optional_merchant(
    merchant_id: str | None = Query(default=None),
    db: DatabaseClient = Depends(get_firestore_db),
) -> dict | None:
    if not merchant_id:
        return None
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=404,
            detail={"error": "merchant not found", "merchant_id": merchant_id},
        )
    return merchant
