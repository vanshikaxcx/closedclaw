from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    COLL_INVOICES,
    COLL_MERCHANTS,
    COLL_TRANSACTIONS,
    COLL_WHATSAPP_LOG,
    DatabaseClient,
    get_db,
    get_document,
    list_documents,
    utc_now_iso,
)
from app.routers.ai_assistant import VoiceTextRequest, post_gst_voice_text
from app.routers.trustscore import compute_trustscore_for_merchant
from app.whatsapp import send_alert

router = APIRouter()


class MunimVoiceRequest(BaseModel):
    merchant_id: str = "seller_a"
    query: str = Field(..., min_length=1)
    generate_audio: bool = True


class MunimWhatsappSendRequest(BaseModel):
    merchant_id: str
    phone: str
    message: str = Field(..., min_length=1)


class MunimRecurringCreateRequest(BaseModel):
    merchant_id: str
    title: str = Field(..., min_length=2)
    amount: float = Field(..., gt=0)
    frequency: str = "monthly"
    next_due_at: str | None = None


_EPHEMERAL_RECURRING: dict[str, list[dict[str, Any]]] = defaultdict(list)
_EPHEMERAL_WHATSAPP: dict[str, list[dict[str, Any]]] = defaultdict(list)


def _get_db_or_none() -> DatabaseClient | None:
    try:
        return get_db()
    except Exception:
        return None


def _merchant_or_404(db: DatabaseClient | None, merchant_id: str) -> dict[str, Any]:
    if db is None:
        return {
            "merchant_id": merchant_id,
            "name": "Demo Merchant",
            "phone": "",
            "trust_score": 60,
            "trust_bucket": "Medium",
        }

    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})
    return merchant


@router.get("/munim/features")
def get_munim_features():
    return {
        "status": "ok",
        "features": [
            "voice_text_assistant",
            "whatsapp_bot",
            "udhari_tracker",
            "customer_intelligence",
            "scheme_recommendations",
            "recurring_payments",
            "morning_briefing",
        ],
        "source": "munim-compatible-layer",
    }


@router.post("/munim/voice/text")
async def post_munim_voice_text(body: MunimVoiceRequest):
    payload = await post_gst_voice_text(
        VoiceTextRequest(
            query=body.query,
            merchant_id=body.merchant_id,
            generate_audio=body.generate_audio,
        )
    )
    return {
        "merchant_id": body.merchant_id,
        "query": body.query,
        "response_text": payload.get("response_text") if isinstance(payload, dict) else None,
        "audio_base64": payload.get("audio_base64") if isinstance(payload, dict) else None,
    }


@router.get("/munim/whatsapp/{merchant_id}/messages")
def get_munim_whatsapp_messages(merchant_id: str):
    db = _get_db_or_none()
    _merchant_or_404(db, merchant_id)

    rows: list[dict[str, Any]] = []
    if db is not None:
        rows = list_documents(
            db,
            COLL_WHATSAPP_LOG,
            order_by="timestamp",
            descending=True,
            limit=100,
        )

    db_msgs = [
        {
            "id": str(row.get("sid") or row.get("id") or uuid4()),
            "merchant_id": merchant_id,
            "direction": "outbound",
            "phone": str(row.get("phone") or ""),
            "message": str(row.get("message") or ""),
            "status": "sent" if bool(row.get("sent")) else "failed",
            "channel": str(row.get("mode") or "mock"),
            "timestamp": str(row.get("timestamp") or utc_now_iso()),
        }
        for row in rows
        if str(row.get("message") or "")
    ]

    mem_msgs = list(_EPHEMERAL_WHATSAPP.get(merchant_id, []))
    all_rows = (mem_msgs + db_msgs)[:100]
    return {"merchant_id": merchant_id, "messages": all_rows}


@router.post("/munim/whatsapp/send")
def post_munim_whatsapp_send(body: MunimWhatsappSendRequest):
    db = _get_db_or_none()
    _merchant_or_404(db, body.merchant_id)
    response = send_alert(db, phone=body.phone, message=body.message)

    record = {
        "id": str(response.get("sid") or f"WA-{uuid4().hex[:10]}"),
        "merchant_id": body.merchant_id,
        "direction": "outbound",
        "phone": body.phone,
        "message": body.message,
        "status": "sent" if bool(response.get("sent")) else "failed",
        "channel": str(response.get("mode") or "mock"),
        "timestamp": utc_now_iso(),
    }
    _EPHEMERAL_WHATSAPP[body.merchant_id].insert(0, record)

    return {
        "ok": bool(response.get("sent")),
        "message_id": record["id"],
        "channel": record["channel"],
        "timestamp": record["timestamp"],
    }


@router.get("/munim/udhari/{merchant_id}")
def get_munim_udhari(merchant_id: str):
    db = _get_db_or_none()
    _merchant_or_404(db, merchant_id)

    if db is None:
        return {
            "merchant_id": merchant_id,
            "total_due": 0.0,
            "count": 0,
            "items": [],
        }

    invoices = list_documents(
        db,
        COLL_INVOICES,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="due_date",
        descending=False,
        limit=1000,
    )

    udhari_rows = []
    for row in invoices:
        status = str(row.get("status") or "").upper()
        if status not in {"OVERDUE", "PENDING"}:
            continue
        udhari_rows.append(
            {
                "udhari_id": str(row.get("invoice_id") or row.get("id") or f"U-{uuid4().hex[:8]}"),
                "merchant_id": merchant_id,
                "customer_name": str(row.get("buyer_name") or "Unknown customer"),
                "customer_phone": "",
                "amount_due": float(row.get("amount") or 0.0),
                "due_date": str(row.get("due_date") or ""),
                "overdue_days": int(row.get("overdue_days") or 0),
                "status": status.lower(),
                "priority": "high" if int(row.get("overdue_days") or 0) >= 15 else "medium",
            }
        )

    total_due = round(sum(float(item["amount_due"]) for item in udhari_rows), 2)
    return {
        "merchant_id": merchant_id,
        "total_due": total_due,
        "count": len(udhari_rows),
        "items": udhari_rows,
    }


@router.post("/munim/udhari/{merchant_id}/remind-all")
def post_munim_udhari_remind_all(merchant_id: str):
    db = _get_db_or_none()
    merchant = _merchant_or_404(db, merchant_id)
    payload = get_munim_udhari(merchant_id)

    phone = str(merchant.get("phone") or "")
    message = (
        f"Udhari reminder summary: {payload['count']} pending entries, total Rs. {payload['total_due']}. "
        "Please follow-up with debtors today."
    )

    sent = False
    if phone and db is not None:
        response = send_alert(db, phone=phone, message=message)
        sent = bool(response.get("sent"))

    return {
        "merchant_id": merchant_id,
        "sent": sent,
        "items_reminded": int(payload["count"]),
        "total_due": float(payload["total_due"]),
        "timestamp": utc_now_iso(),
    }


@router.get("/munim/customers/{merchant_id}")
def get_munim_customers(merchant_id: str):
    db = _get_db_or_none()
    _merchant_or_404(db, merchant_id)

    if db is None:
        return {"merchant_id": merchant_id, "customers": []}

    txns = list_documents(
        db,
        COLL_TRANSACTIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=True,
        limit=2000,
    )

    grouped: dict[str, dict[str, Any]] = {}
    for row in txns:
        counterparty = str(row.get("counterparty") or row.get("raw_description") or "walk-in").strip() or "walk-in"
        amount = float(row.get("amount") or 0.0)
        record = grouped.setdefault(
            counterparty,
            {
                "customer_id": f"C-{abs(hash(counterparty)) % 100000}",
                "name": counterparty,
                "txn_count": 0,
                "total_value": 0.0,
                "last_seen": str(row.get("timestamp") or utc_now_iso()),
            },
        )
        record["txn_count"] = int(record["txn_count"]) + 1
        record["total_value"] = round(float(record["total_value"]) + amount, 2)

    customers = sorted(
        grouped.values(),
        key=lambda item: (float(item["total_value"]), int(item["txn_count"])),
        reverse=True,
    )[:50]

    for item in customers:
        tx_count = int(item["txn_count"])
        if tx_count >= 30:
            segment = "champion"
        elif tx_count >= 15:
            segment = "loyal"
        elif tx_count >= 6:
            segment = "promising"
        else:
            segment = "new"
        item["segment"] = segment

    return {"merchant_id": merchant_id, "customers": customers}


@router.get("/munim/schemes/{merchant_id}")
def get_munim_schemes(merchant_id: str):
    db = _get_db_or_none()
    _merchant_or_404(db, merchant_id)

    try:
        if db is None:
            raise RuntimeError("database unavailable")
        trust = compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=False)
        score = int(trust.get("score") or 0)
    except Exception:
        score = 60

    rows = [
        {
            "scheme_code": "MUDRA_TARUN",
            "title": "Pradhan Mantri MUDRA Yojana (Tarun)",
            "max_amount": 1000000,
            "interest_range": "8.5% - 12%",
            "eligibility_score": 88 if score >= 65 else 62,
            "why_match": "Suitable for working capital expansion and invoice-backed growth.",
        },
        {
            "scheme_code": "CGTMSE",
            "title": "CGTMSE Collateral-Free Credit",
            "max_amount": 20000000,
            "interest_range": "9% - 14%",
            "eligibility_score": 81 if score >= 70 else 58,
            "why_match": "Useful when formal collateral is unavailable.",
        },
        {
            "scheme_code": "PMEGP",
            "title": "PMEGP Subsidy-linked Finance",
            "max_amount": 5000000,
            "interest_range": "As per partner bank",
            "eligibility_score": 74,
            "why_match": "Supports manufacturing/trading unit modernization.",
        },
    ]
    rows.sort(key=lambda item: int(item["eligibility_score"]), reverse=True)
    return {"merchant_id": merchant_id, "schemes": rows}


@router.get("/munim/recurring/{merchant_id}")
def get_munim_recurring(merchant_id: str):
    db = _get_db_or_none()
    _merchant_or_404(db, merchant_id)
    rows = _EPHEMERAL_RECURRING.get(merchant_id, [])
    return {"merchant_id": merchant_id, "items": rows}


@router.post("/munim/recurring")
def post_munim_recurring_create(body: MunimRecurringCreateRequest):
    db = _get_db_or_none()
    _merchant_or_404(db, body.merchant_id)

    next_due = body.next_due_at
    if not next_due:
        next_due = (datetime.now(UTC) + timedelta(days=30)).isoformat()

    item = {
        "recurring_id": f"R-{uuid4().hex[:10]}",
        "merchant_id": body.merchant_id,
        "title": body.title,
        "amount": round(body.amount, 2),
        "frequency": body.frequency,
        "next_due_at": next_due,
        "status": "active",
        "created_at": utc_now_iso(),
    }
    _EPHEMERAL_RECURRING[body.merchant_id].append(item)
    return item


@router.get("/munim/briefing/{merchant_id}")
def get_munim_briefing(merchant_id: str):
    db = _get_db_or_none()
    merchant = _merchant_or_404(db, merchant_id)

    if db is None:
        return {
            "merchant_id": merchant_id,
            "generated_at": utc_now_iso(),
            "summary_text": "Database not configured locally. Add real Appwrite credentials to get full Munim briefing.",
            "highlights": {
                "today_revenue": 0.0,
                "today_txn_count": 0,
                "udhari_total_due": 0.0,
                "udhari_count": 0,
                "trust_score": 60,
                "trust_bucket": "Medium",
            },
        }

    txns = list_documents(
        db,
        COLL_TRANSACTIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=True,
        limit=200,
    )
    today = datetime.now(UTC).date().isoformat()
    today_rows = [row for row in txns if str(row.get("timestamp") or "").startswith(today)]

    today_revenue = round(sum(float(row.get("amount") or 0.0) for row in today_rows), 2)
    today_count = len(today_rows)

    udhari = get_munim_udhari(merchant_id)

    try:
        trust = compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=False)
        trust_score = int(trust.get("score") or 0)
        trust_bucket = str(trust.get("bucket") or "Medium")
    except Exception:
        trust_score = int(merchant.get("trust_score") or 0)
        trust_bucket = str(merchant.get("trust_bucket") or "Medium")

    summary_text = (
        f"Namaste {merchant.get('name') or 'Merchant'}. Aaj {today_count} transactions hue aur "
        f"Rs. {today_revenue} ka flow raha. Udhari outstanding Rs. {udhari['total_due']} hai. "
        f"Current trust score {trust_score} ({trust_bucket})."
    )

    return {
        "merchant_id": merchant_id,
        "generated_at": utc_now_iso(),
        "summary_text": summary_text,
        "highlights": {
            "today_revenue": today_revenue,
            "today_txn_count": today_count,
            "udhari_total_due": float(udhari["total_due"]),
            "udhari_count": int(udhari["count"]),
            "trust_score": trust_score,
            "trust_bucket": trust_bucket,
        },
    }
