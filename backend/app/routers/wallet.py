from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.audit import write_entry
from app.database import (
    COLL_MERCHANTS,
    COLL_PENDING_TRANSFERS,
    COLL_TRANSACTIONS,
    DatabaseClient,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.dependencies import get_firestore_db
from app.notifications import create_notification
from app.schemas import TransferConfirmRequest, TransferRequest
from app.wallet import InsufficientFundsError, get_balance, get_last_updated, sync_to_db, transfer as wallet_transfer

router = APIRouter()


def _threshold() -> float:
    raw = os.getenv("HITL_THRESHOLD", "200").strip()
    try:
        return float(raw)
    except Exception:
        return 200.0


def _resolve_recipient(db: DatabaseClient, to_upi_id: str) -> dict[str, Any] | None:
    target = to_upi_id.strip().lower()
    if target.endswith("@paytm"):
        maybe_id = target[:-6]
        merchant = get_document(db, COLL_MERCHANTS, maybe_id)
        if merchant:
            return merchant

    rows = list_documents(db, COLL_MERCHANTS, order_by="merchant_id", descending=False, limit=500)
    for row in rows:
        upi = str(row.get("upi_id") or "").lower()
        if upi == target:
            return row
    return None


def _write_transfer_transactions(
    db: DatabaseClient,
    tx_id: str,
    from_id: str,
    to_id: str,
    to_upi_id: str,
    amount: float,
    note: str,
) -> None:
    now_iso = utc_now_iso()

    debit_doc = {
        "tx_id": f"{tx_id}-D",
        "merchant_id": from_id,
        "amount": -round(amount, 2),
        "timestamp": now_iso,
        "raw_description": f"Transfer to {to_upi_id}",
        "type": "transfer_debit",
        "counterparty": to_id,
        "parent_tx_id": tx_id,
        "note": note,
    }
    credit_doc = {
        "tx_id": f"{tx_id}-C",
        "merchant_id": to_id,
        "amount": round(amount, 2),
        "timestamp": now_iso,
        "raw_description": f"Transfer from {from_id}",
        "type": "transfer_credit",
        "counterparty": from_id,
        "parent_tx_id": tx_id,
        "note": note,
    }

    upsert_document(db, COLL_TRANSACTIONS, debit_doc["tx_id"], debit_doc, merge=False)
    upsert_document(db, COLL_TRANSACTIONS, credit_doc["tx_id"], credit_doc, merge=False)


def _execute_transfer(
    db: DatabaseClient,
    from_id: str,
    to_id: str,
    to_upi_id: str,
    amount: float,
    note: str,
    token_id: str | None,
) -> dict[str, Any]:
    sender_new, _ = wallet_transfer(from_id, to_id, amount)
    sync_to_db(db)

    tx_id = str(uuid4())
    _write_transfer_transactions(db, tx_id, from_id, to_id, to_upi_id, amount, note)

    audit = write_entry(
        db,
        actor_type="merchant",
        actor_id=from_id,
        action="TRANSFER_COMPLETED",
        entity_id=tx_id,
        amount=amount,
        token_id=token_id,
        outcome="success",
        metadata={"from_id": from_id, "to_id": to_id, "to_upi_id": to_upi_id},
    )

    create_notification(
        db,
        merchant_id=to_id,
        notif_type="transfer",
        title="Incoming transfer",
        body=f"You received Rs. {round(amount, 2)} from {from_id}.",
        action_url="/merchant/wallet",
    )

    return {
        "tx_id": tx_id,
        "from_id": from_id,
        "to_id": to_id,
        "to_upi_id": to_upi_id,
        "amount": round(amount, 2),
        "note": note,
        "status": "completed",
        "new_balance": sender_new,
        "timestamp": utc_now_iso(),
        "audit_id": audit["log_id"],
    }


@router.get("/check-balance")
def get_check_balance(
    merchant_id: str = Query(...),
    db: DatabaseClient = Depends(get_firestore_db),
):
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    return {
        "merchant_id": merchant_id,
        "balance": get_balance(merchant_id),
        "currency": "INR",
        "last_updated": get_last_updated(merchant_id),
    }


@router.post("/transfer")
def post_transfer(body: TransferRequest, db: DatabaseClient = Depends(get_firestore_db)):
    if body.amount <= 0 or body.amount > 100000:
        raise HTTPException(status_code=400, detail={"error": "amount_out_of_range", "min": 0, "max": 100000})

    sender = get_document(db, COLL_MERCHANTS, body.from_id)
    if not sender:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": body.from_id})

    recipient = _resolve_recipient(db, body.to_upi_id)
    if not recipient:
        raise HTTPException(status_code=400, detail={"error": "recipient_not_found", "upi_id": body.to_upi_id})

    to_id = str(recipient.get("merchant_id") or recipient.get("id"))

    if body.amount > _threshold() and not body.token_id:
        transfer_id = str(uuid4())
        upsert_document(
            db,
            COLL_PENDING_TRANSFERS,
            transfer_id,
            {
                "transfer_id": transfer_id,
                "from_id": body.from_id,
                "to_id": to_id,
                "to_upi_id": body.to_upi_id,
                "amount": body.amount,
                "note": body.note or "",
                "created_at": utc_now_iso(),
            },
            merge=False,
        )
        return {
            "status": "pending_approval",
            "transfer_id": transfer_id,
            "amount": body.amount,
            "message": "Amount exceeds threshold. Confirm via /api/transfer-confirm",
        }

    try:
        return _execute_transfer(
            db,
            from_id=body.from_id,
            to_id=to_id,
            to_upi_id=body.to_upi_id,
            amount=body.amount,
            note=body.note or "",
            token_id=body.token_id,
        )
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=400, detail={"error": "insufficient_funds"}) from exc


@router.post("/transfer-confirm")
def post_transfer_confirm(body: TransferConfirmRequest, db: DatabaseClient = Depends(get_firestore_db)):
    pending = get_document(db, COLL_PENDING_TRANSFERS, body.transfer_id)
    if not pending:
        raise HTTPException(status_code=404, detail={"error": "transfer_not_found", "transfer_id": body.transfer_id})

    if str(pending.get("from_id")) != body.merchant_id:
        raise HTTPException(status_code=403, detail={"error": "transfer_not_owned"})

    try:
        response = _execute_transfer(
            db,
            from_id=str(pending.get("from_id")),
            to_id=str(pending.get("to_id")),
            to_upi_id=str(pending.get("to_upi_id")),
            amount=float(pending.get("amount") or 0.0),
            note=str(pending.get("note") or ""),
            token_id=body.transfer_id,
        )
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=400, detail={"error": "insufficient_funds"}) from exc

    db.collection(COLL_PENDING_TRANSFERS).document(body.transfer_id).delete()
    return response
