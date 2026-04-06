from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.audit import write_entry
from app.database import (
    COLL_CREDIT_OFFERS,
    COLL_INVOICES,
    COLL_MERCHANTS,
    DatabaseClient,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.dependencies import get_firestore_db
from app.notifications import create_notification
from app.routers.trustscore import compute_trustscore_for_merchant, process_trustscore_event
from app.wallet import credit as wallet_credit
from app.wallet import get_balance, sync_to_db
from app.whatsapp import send_alert

router = APIRouter()


def _today() -> date:
    return date.today()


def _safe_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _invoice_to_response(invoice: dict[str, Any]) -> dict[str, Any]:
    return {
        "invoice_id": invoice.get("invoice_id"),
        "buyer_name": invoice.get("buyer_name") or "",
        "buyer_gstin": invoice.get("buyer_gstin") or "",
        "amount": float(invoice.get("amount") or 0.0),
        "due_date": invoice.get("due_date"),
        "status": str(invoice.get("status") or "PENDING").upper(),
        "overdue_days": int(invoice.get("overdue_days") or 0),
        "advance_amount": float(invoice.get("advance_amount") or 0.0),
        "fee_rate": float(invoice.get("fee_rate") or 0.0),
        "offer_id": invoice.get("offer_id"),
        "repaid": bool(invoice.get("repaid") or False),
        "created_at": invoice.get("created_at") or "",
    }


def _refresh_overdue(db: DatabaseClient, invoice: dict[str, Any]) -> dict[str, Any]:
    status = str(invoice.get("status") or "PENDING").upper()
    if status in {"PAID", "FINANCED"}:
        return invoice

    due_date = _safe_date(invoice.get("due_date"))
    if not due_date:
        return invoice

    overdue_days = max((_today() - due_date).days, 0)
    next_status = "OVERDUE" if overdue_days > 0 else "PENDING"

    if next_status != status or int(invoice.get("overdue_days") or 0) != overdue_days:
        patch = {
            "status": next_status,
            "overdue_days": overdue_days,
            "updated_at": utc_now_iso(),
        }
        upsert_document(db, COLL_INVOICES, str(invoice.get("invoice_id")), patch, merge=True)
        invoice = {**invoice, **patch}

    return invoice


@router.get("/invoices")
def get_invoices(
    merchant_id: str = Query(...),
    status: str = Query(default="ALL"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_firestore_db),
):
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    rows = list_documents(db, COLL_INVOICES, filters=[("merchant_id", "==", merchant_id)], order_by="due_date", descending=False, limit=1000)

    normalized_status = status.upper()
    output: list[dict[str, Any]] = []
    for row in rows:
        refreshed = _refresh_overdue(db, row)
        if normalized_status != "ALL" and str(refreshed.get("status") or "").upper() != normalized_status:
            continue
        output.append(_invoice_to_response(refreshed))

    total = len(output)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "merchant_id": merchant_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "invoices": output[start:end],
    }


@router.post("/credit-offer")
def post_credit_offer(payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id = str(payload.get("merchant_id") or payload.get("merchantId") or "").strip()
    invoice_id = str(payload.get("invoice_id") or payload.get("invoiceId") or "").strip()

    if not merchant_id or not invoice_id:
        raise HTTPException(status_code=400, detail={"error": "merchant_id and invoice_id are required"})

    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    invoice = get_document(db, COLL_INVOICES, invoice_id)
    if not invoice or str(invoice.get("merchant_id")) != merchant_id:
        raise HTTPException(status_code=404, detail={"error": "invoice_not_found", "invoice_id": invoice_id})

    invoice = _refresh_overdue(db, invoice)
    current_status = str(invoice.get("status") or "PENDING").upper()
    if current_status != "OVERDUE":
        raise HTTPException(status_code=400, detail={"error": "invoice_not_overdue", "current_status": current_status})

    offers = list_documents(db, COLL_CREDIT_OFFERS, filters=[("invoice_id", "==", invoice_id)], order_by="generated_at", descending=True, limit=20)
    now = datetime.now(UTC)
    for row in offers:
        if str(row.get("status") or "").lower() == "pending_acceptance":
            expires_at = row.get("expires_at")
            if expires_at and datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")) > now:
                return row

    score_payload = compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=True)
    score = int(score_payload["score"])
    if score < 41:
        raise HTTPException(status_code=400, detail={"error": "trust_score_too_low", "score": score, "minimum_required": 41})

    if score >= 80:
        advance_pct = 0.90
        max_advance = 500000.0
    elif score >= 66:
        advance_pct = 0.85
        max_advance = 200000.0
    else:
        advance_pct = 0.70
        max_advance = 75000.0

    amount = float(invoice.get("amount") or 0.0)
    advance_amount = round(min(amount * advance_pct, max_advance), 2)
    generated_at = utc_now_iso()
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()

    offer_id = str(uuid4())
    offer = {
        "offer_id": offer_id,
        "invoice_id": invoice_id,
        "merchant_id": merchant_id,
        "advance_amount": advance_amount,
        "fee_rate": 2.0,
        "repayment_trigger": "auto_deducted_on_buyer_payment",
        "status": "pending_acceptance",
        "expires_at": expires_at,
        "generated_at": generated_at,
    }
    upsert_document(db, COLL_CREDIT_OFFERS, offer_id, offer, merge=False)

    write_entry(
        db,
        actor_type="system",
        actor_id="finance-engine",
        action="CREDIT_OFFER_GENERATED",
        entity_id=invoice_id,
        amount=advance_amount,
        outcome="success",
        metadata={"offer_id": offer_id, "score": score},
    )

    create_notification(
        db,
        merchant_id=merchant_id,
        notif_type="finance",
        title="Finance advance available",
        body=f"A finance advance of Rs. {advance_amount} is available for Invoice #{invoice_id}.",
        action_url=f"/merchant/invoices/{invoice_id}",
    )

    return offer


@router.post("/credit-accept")
def post_credit_accept(payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    offer_id = str(payload.get("offer_id") or payload.get("offerId") or "").strip()
    merchant_id = str(payload.get("merchant_id") or payload.get("merchantId") or "").strip()

    if not offer_id or not merchant_id:
        raise HTTPException(status_code=400, detail={"error": "offer_id and merchant_id are required"})

    offer = get_document(db, COLL_CREDIT_OFFERS, offer_id)
    if not offer or str(offer.get("merchant_id")) != merchant_id:
        raise HTTPException(status_code=404, detail={"error": "offer_not_found", "offer_id": offer_id})

    if str(offer.get("status") or "") != "pending_acceptance":
        raise HTTPException(status_code=400, detail={"error": "offer_not_pending", "status": offer.get("status")})

    expires_at_raw = str(offer.get("expires_at") or "")
    if not expires_at_raw:
        raise HTTPException(status_code=400, detail={"error": "offer_invalid", "detail": "missing expires_at"})
    expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    if expires_at <= datetime.now(UTC):
        upsert_document(db, COLL_CREDIT_OFFERS, offer_id, {"status": "expired", "updated_at": utc_now_iso()}, merge=True)
        raise HTTPException(status_code=400, detail={"error": "offer_expired", "expired_at": expires_at_raw})

    invoice_id = str(offer.get("invoice_id") or "")
    invoice = get_document(db, COLL_INVOICES, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"error": "invoice_not_found", "invoice_id": invoice_id})

    amount = float(offer.get("advance_amount") or 0.0)
    new_wallet = wallet_credit(merchant_id, amount)
    sync_to_db(db)

    accepted_at = utc_now_iso()
    upsert_document(
        db,
        COLL_CREDIT_OFFERS,
        offer_id,
        {"status": "accepted", "accepted_at": accepted_at, "updated_at": accepted_at},
        merge=True,
    )

    upsert_document(
        db,
        COLL_INVOICES,
        invoice_id,
        {
            "status": "FINANCED",
            "advance_amount": amount,
            "fee_rate": float(offer.get("fee_rate") or 2.0),
            "offer_id": offer_id,
            "overdue_days": 0,
            "repaid": False,
            "updated_at": accepted_at,
        },
        merge=True,
    )

    write_entry(
        db,
        actor_type="merchant",
        actor_id=merchant_id,
        action="CREDIT_ACCEPTED",
        entity_id=invoice_id,
        amount=amount,
        outcome="success",
        metadata={"offer_id": offer_id},
    )

    merchant = get_document(db, COLL_MERCHANTS, merchant_id) or {}
    buyer_name = str(invoice.get("buyer_name") or "buyer")
    message = (
        f"ArthSetu Finance: Your advance of Rs. {amount} against Invoice #{invoice_id} has been approved. "
        f"Disbursement complete. Repayment will be auto-deducted when {buyer_name} pays."
    )
    wa = send_alert(db, phone=str(merchant.get("phone") or ""), message=message)

    process_trustscore_event(
        db,
        merchant_id,
        "TRANSFER_COMPLETED",
        {"source": "invoice_finance", "amount": amount, "invoice_id": invoice_id, "offer_id": offer_id},
    )

    create_notification(
        db,
        merchant_id=merchant_id,
        notif_type="finance",
        title="Advance disbursed",
        body=f"Advance of Rs. {amount} disbursed to wallet for invoice {invoice_id}.",
        action_url="/merchant/wallet",
        whatsapp_sent=bool(wa.get("sent")),
    )

    return {
        "offer_id": offer_id,
        "invoice_id": invoice_id,
        "status": "accepted",
        "advance_amount": amount,
        "disbursed_to_wallet": True,
        "new_wallet_balance": new_wallet,
        "whatsapp_sent": bool(wa.get("sent", False)),
        "accepted_at": accepted_at,
    }
