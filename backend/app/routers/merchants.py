from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.audit import write_entry
from app.database import (
    COLL_AUDIT_LOG,
    COLL_INVOICES,
    COLL_MERCHANTS,
    COLL_NOTIFICATIONS,
    COLL_TRUSTSCORE_HISTORY,
    DatabaseClient,
    demo_mode_enabled,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.dependencies import get_firestore_db
from app.seed import SEED_MERCHANT_ID, ensure_seed_data
from app.schemas import LoginRequest, RegisterRequest

router = APIRouter()

ADMIN_ALIAS = "admin_arth"
ADMIN_MERCHANT_ID = "admin_hq"


def _safe_get_document(db: DatabaseClient, collection_name: str, doc_id: str) -> dict[str, Any] | None:
    try:
        return get_document(db, collection_name, doc_id)
    except Exception:
        return None


def _safe_list_documents(
    db: DatabaseClient,
    collection_name: str,
    filters: list[tuple[str, str, Any]] | None = None,
    order_by: str | None = None,
    descending: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    try:
        return list_documents(
            db,
            collection_name,
            filters=filters,
            order_by=order_by,
            descending=descending,
            limit=limit,
        )
    except Exception:
        return []


def _bucket(score: int) -> str:
    if score <= 40:
        return "Low"
    if score <= 65:
        return "Medium"
    if score <= 80:
        return "Good"
    return "Excellent"


def _session_payload(merchant: dict[str, Any]) -> dict[str, Any]:
    merchant_id = str(merchant.get("merchant_id") or merchant.get("id"))
    role = str(merchant.get("role") or "merchant")
    return {
        "user_id": f"user_{merchant_id}",
        "name": merchant.get("name") or "",
        "phone": merchant.get("phone") or "",
        "role": role,
        "merchant_id": merchant_id if role == "merchant" else None,
        "token": f"live-token-{merchant_id}-{uuid4().hex[:8]}",
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }


def _normalize_merchant_for_frontend(merchant: dict[str, Any]) -> dict[str, Any]:
    return {
        "merchant_id": merchant.get("merchant_id") or merchant.get("id"),
        "name": merchant.get("name") or "",
        "business_name": merchant.get("business_name") or merchant.get("name") or "",
        "category": merchant.get("category") or "Other",
        "city": merchant.get("city") or "",
        "phone": merchant.get("phone") or "",
        "gstin": merchant.get("gstin") or "",
        "kyc_status": merchant.get("kyc_status") or "pending",
        "wallet_balance": float(merchant.get("wallet_balance") or 0.0),
        "trust_score": int(merchant.get("trust_score") or 0),
        "trust_bucket": merchant.get("trust_bucket") or _bucket(int(merchant.get("trust_score") or 0)),
        "created_at": merchant.get("created_at") or "",
    }


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or f"merchant_{uuid4().hex[:6]}"


@router.post("/login")
def post_login(body: LoginRequest, db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id = body.merchant_id.strip().lower()
    if merchant_id == ADMIN_ALIAS:
        merchant_id = ADMIN_MERCHANT_ID

    merchant = _safe_get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant and demo_mode_enabled() and merchant_id in {SEED_MERCHANT_ID, ADMIN_MERCHANT_ID}:
        try:
            ensure_seed_data(db, force=False)
            merchant = _safe_get_document(db, COLL_MERCHANTS, merchant_id)
        except Exception:
            merchant = None

    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": body.merchant_id})

    if str(merchant.get("pin_hash") or "") != body.pin_hash:
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials"})

    session = _session_payload(merchant)

    try:
        write_entry(
            db,
            actor_type="admin" if session["role"] == "admin" else "merchant",
            actor_id=merchant_id,
            action="login_success",
            entity_id=merchant_id,
            outcome="success",
            metadata={"role": session["role"]},
        )
    except Exception:
        # Keep authentication responsive even when audit writes are quota blocked.
        pass

    return {
        "session": session,
        "merchant": _normalize_merchant_for_frontend(merchant) if session["role"] == "merchant" else None,
    }


@router.post("/register")
def post_register(body: RegisterRequest, db: DatabaseClient = Depends(get_firestore_db)):
    role = body.role
    merchant_id = body.merchant_id.strip().lower() if body.merchant_id else None

    if role == "merchant":
        if not merchant_id:
            merchant_id = _safe_slug(body.business_name or body.name)
    else:
        merchant_id = merchant_id or f"user_{uuid4().hex[:8]}"

    existing = _safe_get_document(db, COLL_MERCHANTS, merchant_id)
    if existing:
        raise HTTPException(status_code=409, detail={"error": "merchant_id_exists", "merchant_id": merchant_id})

    payload = {
        "merchant_id": merchant_id,
        "name": body.name,
        "business_name": body.business_name or body.name,
        "category": body.category or "General",
        "city": body.city or "",
        "phone": body.phone,
        "gstin": body.gstin or "",
        "kyc_status": "pending",
        "wallet_balance": 0.0,
        "upi_id": f"{merchant_id}@paytm",
        "role": role,
        "pin_hash": body.pin_hash,
        "trust_score": 50 if role == "merchant" else 0,
        "trust_bucket": "Medium" if role == "merchant" else "Low",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }

    upsert_document(db, COLL_MERCHANTS, merchant_id, payload, merge=False)

    write_entry(
        db,
        actor_type="merchant" if role == "merchant" else "system",
        actor_id=merchant_id,
        action="account_registered",
        entity_id=merchant_id,
        outcome="success",
        metadata={"role": role},
    )

    session = _session_payload(payload)
    return {
        "session": session,
        "merchant": _normalize_merchant_for_frontend(payload) if role == "merchant" else None,
    }


@router.get("/merchants")
def get_merchants(
    category: str | None = Query(default=None),
    kyc_status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    response_format: str = Query(default="list", alias="format"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_firestore_db),
):
    merchants = _safe_list_documents(db, COLL_MERCHANTS, order_by="merchant_id", descending=False, limit=2000)

    history = _safe_list_documents(db, COLL_TRUSTSCORE_HISTORY, order_by="computed_at", descending=True, limit=5000)
    latest_by_merchant: dict[str, dict[str, Any]] = {}
    for row in history:
        merchant_id = str(row.get("merchant_id") or "")
        if not merchant_id or merchant_id in latest_by_merchant:
            continue
        latest_by_merchant[merchant_id] = row

    rows = []
    query = (search or "").strip().lower()
    for merchant in merchants:
        if str(merchant.get("role") or "merchant") != "merchant":
            continue

        if category and str(merchant.get("category") or "").lower() != category.lower():
            continue
        if kyc_status and str(merchant.get("kyc_status") or "").lower() != kyc_status.lower():
            continue

        blob = f"{merchant.get('merchant_id','')} {merchant.get('name','')} {merchant.get('business_name','')}"
        if query and query not in blob.lower():
            continue

        merchant_id = str(merchant.get("merchant_id") or merchant.get("id"))
        latest = latest_by_merchant.get(merchant_id, {})

        rows.append(
            {
                "merchant_id": merchant_id,
                "name": merchant.get("name") or "",
                "business_name": merchant.get("business_name") or merchant.get("name") or "",
                "category": merchant.get("category") or "",
                "city": merchant.get("city") or "",
                "kyc_status": merchant.get("kyc_status") or "pending",
                "wallet_balance": float(merchant.get("wallet_balance") or 0.0),
                "trust_score": int(latest.get("score") or merchant.get("trust_score") or 0),
                "trust_bucket": latest.get("bucket") or merchant.get("trust_bucket") or "Low",
                "created_at": merchant.get("created_at") or "",
            }
        )

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size

    paged = rows[start:end]
    if response_format.lower() == "paginated":
        return {"total": total, "page": page, "page_size": page_size, "merchants": paged}
    return paged


@router.get("/merchants/{merchant_id}")
def get_merchant_profile(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    merchant = _safe_get_document(db, COLL_MERCHANTS, merchant_id)

    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    trust_rows = _safe_list_documents(
        db,
        COLL_TRUSTSCORE_HISTORY,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="computed_at",
        descending=True,
        limit=1,
    )
    trust = trust_rows[0] if trust_rows else {
        "score": int(merchant.get("trust_score") or 0),
        "bucket": merchant.get("trust_bucket") or "Low",
        "components": {},
        "computed_at": merchant.get("updated_at") or utc_now_iso(),
    }

    invoices = _safe_list_documents(db, COLL_INVOICES, filters=[("merchant_id", "==", merchant_id)], limit=1000)
    summary = {"pending": 0, "paid": 0, "overdue": 0, "financed": 0}
    for row in invoices:
        key = str(row.get("status") or "PENDING").lower()
        if key == "pending":
            summary["pending"] += 1
        elif key == "paid":
            summary["paid"] += 1
        elif key == "overdue":
            summary["overdue"] += 1
        elif key == "financed":
            summary["financed"] += 1

    audit_rows = _safe_list_documents(db, COLL_AUDIT_LOG, filters=[("actor_id", "==", merchant_id)], order_by="timestamp", descending=True, limit=5)
    notif_rows = _safe_list_documents(db, COLL_NOTIFICATIONS, filters=[("merchant_id", "==", merchant_id)], limit=1000)
    unread = sum(1 for row in notif_rows if not bool(row.get("read")))

    return {
        "merchant": _normalize_merchant_for_frontend(merchant),
        "trust_score": {
            "score": int(trust.get("score") or 0),
            "bucket": trust.get("bucket") or "Low",
            "components": trust.get("components") or {},
            "computed_at": trust.get("computed_at"),
        },
        "invoice_summary": summary,
        "recent_audit": audit_rows,
        "unread_notifications": unread,
    }
