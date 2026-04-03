import hashlib
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.audit import append_audit
from backend.db import get_db
from backend.wallet import transfer_funds
from backend.whatsapp import send_whatsapp


invoice_router = APIRouter()


def _today() -> date:
    return date.today()


def _overdue_days(due_date_iso: str) -> int:
    due_date = date.fromisoformat(due_date_iso)
    return max((_today() - due_date).days, 0)


def _refresh_invoice_status(conn, invoice_row) -> tuple[str, int]:
    overdue_days = _overdue_days(invoice_row["due_date"])
    status = invoice_row["status"]

    if status in {"PAID", "CLOSED", "FINANCED"}:
        return status, overdue_days

    if overdue_days > 15:
        if status != "OVERDUE":
            conn.execute(
                "UPDATE invoices SET status = ? WHERE invoice_id = ?",
                ("OVERDUE", invoice_row["invoice_id"]),
            )
        return "OVERDUE", overdue_days

    if status == "OVERDUE":
        conn.execute(
            "UPDATE invoices SET status = ? WHERE invoice_id = ?",
            ("PENDING", invoice_row["invoice_id"]),
        )
    return "PENDING", overdue_days


def _score_band(score: int) -> dict | None:
    if score >= 80:
        return {"advance_pct": 0.90, "max_cap": 500000.0, "fee_rate": 1.2}
    if score >= 66:
        return {"advance_pct": 0.80, "max_cap": 200000.0, "fee_rate": 1.8}
    if score >= 41:
        return {"advance_pct": 0.70, "max_cap": 75000.0, "fee_rate": 2.5}
    return None


def _fetch_offer_for_invoice(conn, invoice_id: str):
    return conn.execute(
        """
        SELECT offer_id, advance_amount, status, expires_at, accepted_at
        FROM credit_offers
        WHERE invoice_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (invoice_id,),
    ).fetchone()


def _get_trustscore(conn, merchant_id: str) -> int | None:
    row = conn.execute(
        "SELECT score FROM trustscores WHERE merchant_id = ?",
        (merchant_id,),
    ).fetchone()
    if row is None:
        return None
    return int(row["score"])


def _record_ledger_event(conn, invoice_id: str, offer_id: str | None, event_type: str, amount: float, tx_id: str | None):
    conn.execute(
        """
        INSERT INTO financing_ledger (ledger_id, invoice_id, offer_id, event_type, amount, tx_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"LED-{uuid4().hex[:12]}",
            invoice_id,
            offer_id,
            event_type,
            round(amount, 2),
            tx_id,
            datetime.now(UTC).isoformat(),
        ),
    )


def process_repayment(conn, sender_id: str, receiver_id: str, incoming_amount: float, parent_tx_id: str) -> None:
    financed = conn.execute(
        """
        SELECT invoice_id, seller_id, buyer_id, advance_amount, offer_id, status, repaid
        FROM invoices
        WHERE seller_id = ? AND buyer_id = ? AND status = 'FINANCED' AND repaid = 0
        ORDER BY financed_at ASC
        """,
        (receiver_id, sender_id),
    ).fetchall()

    remaining = incoming_amount
    for invoice in financed:
        if remaining <= 0:
            break

        if not invoice["offer_id"]:
            continue

        offer = conn.execute(
            "SELECT fee_rate FROM credit_offers WHERE offer_id = ?",
            (invoice["offer_id"],),
        ).fetchone()
        if offer is None:
            continue

        recovered_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS recovered
            FROM financing_ledger
            WHERE invoice_id = ? AND event_type = 'RECOVERY'
            """,
            (invoice["invoice_id"],),
        ).fetchone()
        already_recovered = float(recovered_row["recovered"])
        advance_amount = float(invoice["advance_amount"])
        total_due = round(advance_amount + (advance_amount * float(offer["fee_rate"]) / 100.0), 2)
        outstanding = round(total_due - already_recovered, 2)

        if outstanding <= 0:
            conn.execute(
                "UPDATE invoices SET repaid = 1, status = 'CLOSED', repaid_at = ? WHERE invoice_id = ?",
                (datetime.now(UTC).isoformat(), invoice["invoice_id"]),
            )
            continue

        recovery = round(min(remaining, outstanding), 2)
        if recovery <= 0:
            continue

        recovery_tx = transfer_funds(
            sender_id=receiver_id,
            receiver_id="financing_pool",
            amount=recovery,
            note=f"invoice_recovery:{invoice['invoice_id']} parent:{parent_tx_id}",
            connection=conn,
        )
        _record_ledger_event(
            conn,
            invoice_id=invoice["invoice_id"],
            offer_id=invoice["offer_id"],
            event_type="RECOVERY",
            amount=recovery,
            tx_id=recovery_tx,
        )

        append_audit(
            action="RECOVERY_APPLIED",
            entity_id=invoice["invoice_id"],
            amount=recovery,
            outcome="SUCCESS",
            details={"parent_tx_id": parent_tx_id, "recovery_tx_id": recovery_tx},
            connection=conn,
        )

        remaining = round(remaining - recovery, 2)
        if round(outstanding - recovery, 2) <= 0:
            conn.execute(
                "UPDATE invoices SET repaid = 1, status = 'CLOSED', repaid_at = ? WHERE invoice_id = ?",
                (datetime.now(UTC).isoformat(), invoice["invoice_id"]),
            )
            append_audit(
                action="RECOVERY_DONE",
                entity_id=invoice["invoice_id"],
                outcome="SUCCESS",
                details={"final_tx_id": recovery_tx},
                connection=conn,
            )


@invoice_router.get("/api/invoices")
def get_invoices(merchant_id: str = ""):
    merchant_id = merchant_id.strip()
    if not merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id is required")

    conn = get_db()
    rows = conn.execute(
        """
        SELECT invoice_id, seller_id, buyer_id, amount, due_date, status, advance_amount, offer_id, repaid
        FROM invoices
        WHERE seller_id = ?
        ORDER BY due_date ASC
        """,
        (merchant_id,),
    ).fetchall()

    output = []
    for row in rows:
        status, overdue_days = _refresh_invoice_status(conn, row)
        offer = _fetch_offer_for_invoice(conn, row["invoice_id"])
        has_offer = bool(offer and offer["status"] in {"PENDING_ACCEPTANCE", "ACCEPTED"})
        output.append(
            {
                "invoice_id": row["invoice_id"],
                "seller_id": row["seller_id"],
                "buyer_id": row["buyer_id"],
                "amount": float(row["amount"]),
                "due_date": row["due_date"],
                "status": status,
                "overdue_days": overdue_days,
                "has_offer": has_offer,
                "offer_id": offer["offer_id"] if offer else row["offer_id"],
                "advance_amount": float(row["advance_amount"] or 0),
                "repaid": bool(row["repaid"]),
            }
        )

    return {"merchant_id": merchant_id, "invoices": output}


@invoice_router.post("/api/credit-offer")
def create_credit_offer(payload: dict):
    merchant_id = (payload.get("merchant_id") or "").strip()
    invoice_id = (payload.get("invoice_id") or "").strip()

    if not merchant_id or not invoice_id:
        raise HTTPException(status_code=400, detail="merchant_id and invoice_id are required")

    conn = get_db()
    invoice = conn.execute(
        """
        SELECT invoice_id, seller_id, amount, due_date, status, offer_id
        FROM invoices
        WHERE invoice_id = ? AND seller_id = ?
        """,
        (invoice_id, merchant_id),
    ).fetchone()

    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")

    status, overdue_days = _refresh_invoice_status(conn, invoice)

    if status in {"FINANCED", "CLOSED"}:
        return {"status": "declined", "reason": "ALREADY_FINANCED"}

    if status != "OVERDUE":
        return {"status": "declined", "reason": "NOT_OVERDUE"}

    accepted_offer = conn.execute(
        "SELECT offer_id FROM credit_offers WHERE invoice_id = ? AND status = 'ACCEPTED'",
        (invoice_id,),
    ).fetchone()
    if accepted_offer is not None:
        return {"status": "declined", "reason": "ALREADY_FINANCED"}

    pending_offer = conn.execute(
        """
        SELECT offer_id, advance_amount, fee_rate, expires_at
        FROM credit_offers
        WHERE invoice_id = ? AND status = 'PENDING_ACCEPTANCE' AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (invoice_id, datetime.now(UTC).isoformat()),
    ).fetchone()

    score = _get_trustscore(conn, merchant_id)
    if score is None or score < 50:
        return {"status": "declined", "reason": "LOW_TRUSTSCORE"}

    band = _score_band(score)
    if band is None:
        return {"status": "declined", "reason": "LOW_TRUSTSCORE"}

    if pending_offer is not None:
        return {
            "offer_id": pending_offer["offer_id"],
            "invoice_id": invoice_id,
            "trustscore": score,
            "advance_amount": float(pending_offer["advance_amount"]),
            "fee_rate": float(pending_offer["fee_rate"]),
            "repayment_trigger": "buyer_payment",
            "status": "pending_acceptance",
            "expires_at": pending_offer["expires_at"],
        }

    overdue_bucket = overdue_days // 7
    idempotency_key = hashlib.sha256(
        f"{invoice_id}:{score}:{overdue_bucket}".encode("utf-8")
    ).hexdigest()

    existing = conn.execute(
        """
        SELECT offer_id, advance_amount, fee_rate, status, expires_at
        FROM credit_offers
        WHERE idempotency_key = ?
        LIMIT 1
        """,
        (idempotency_key,),
    ).fetchone()
    if existing is not None and existing["status"] != "EXPIRED":
        return {
            "offer_id": existing["offer_id"],
            "invoice_id": invoice_id,
            "trustscore": score,
            "advance_amount": float(existing["advance_amount"]),
            "fee_rate": float(existing["fee_rate"]),
            "repayment_trigger": "buyer_payment",
            "status": "pending_acceptance",
            "expires_at": existing["expires_at"],
        }

    base_advance = float(invoice["amount"]) * band["advance_pct"]
    advance_amount = round(min(base_advance, band["max_cap"]), 2)

    offer_id = f"OFF-{uuid4().hex[:12]}"
    created_at = datetime.now(UTC)
    expires_at = (created_at + timedelta(hours=24)).isoformat()

    conn.execute(
        """
        INSERT INTO credit_offers (
            offer_id, invoice_id, merchant_id, trustscore_snapshot,
            advance_pct, max_cap_applied, advance_amount, fee_rate,
            status, idempotency_key, created_at, expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            offer_id,
            invoice_id,
            merchant_id,
            score,
            band["advance_pct"],
            band["max_cap"],
            advance_amount,
            band["fee_rate"],
            "PENDING_ACCEPTANCE",
            idempotency_key,
            created_at.isoformat(),
            expires_at,
        ),
    )

    append_audit(
        action="OFFER_CREATED",
        entity_id=invoice_id,
        amount=advance_amount,
        outcome="SUCCESS",
        details={"offer_id": offer_id, "trustscore": score},
        connection=conn,
    )
    return {
        "offer_id": offer_id,
        "invoice_id": invoice_id,
        "trustscore": score,
        "advance_amount": advance_amount,
        "fee_rate": band["fee_rate"],
        "repayment_trigger": "buyer_payment",
        "status": "pending_acceptance",
        "expires_at": expires_at,
    }


@invoice_router.post("/api/credit-accept")
def accept_credit_offer(payload: dict):
    offer_id = (payload.get("offer_id") or "").strip()
    merchant_id = (payload.get("merchant_id") or "").strip()

    if not offer_id or not merchant_id:
        raise HTTPException(status_code=400, detail="offer_id and merchant_id are required")

    conn = get_db()
    offer = conn.execute(
        """
        SELECT offer_id, invoice_id, merchant_id, advance_amount, fee_rate, status, expires_at
        FROM credit_offers
        WHERE offer_id = ?
        """,
        (offer_id,),
    ).fetchone()

    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")

    if offer["merchant_id"] != merchant_id:
        raise HTTPException(status_code=403, detail="offer does not belong to merchant")

    invoice = conn.execute(
        "SELECT invoice_id, status FROM invoices WHERE invoice_id = ?",
        (offer["invoice_id"],),
    ).fetchone()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")

    if offer["status"] != "PENDING_ACCEPTANCE":
        raise HTTPException(status_code=409, detail="offer already processed")

    if offer["expires_at"] <= datetime.now(UTC).isoformat():
        conn.execute(
            "UPDATE credit_offers SET status = 'EXPIRED' WHERE offer_id = ?",
            (offer_id,),
        )
        raise HTTPException(status_code=409, detail="offer expired")

    if invoice["status"] in {"FINANCED", "CLOSED"}:
        raise HTTPException(status_code=409, detail="invoice already financed")

    try:
        disbursal_tx_id = transfer_funds(
            sender_id="financing_pool",
            receiver_id=merchant_id,
            amount=float(offer["advance_amount"]),
            note=f"invoice_disbursal:{offer['invoice_id']}",
            connection=conn,
        )
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    now = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE credit_offers SET status = 'ACCEPTED', accepted_at = ? WHERE offer_id = ?",
        (now, offer_id),
    )
    conn.execute(
        """
        UPDATE invoices
        SET status = 'FINANCED', advance_amount = ?, offer_id = ?, financed_at = ?, repaid = 0
        WHERE invoice_id = ?
        """,
        (float(offer["advance_amount"]), offer_id, now, offer["invoice_id"]),
    )

    _record_ledger_event(
        conn,
        invoice_id=offer["invoice_id"],
        offer_id=offer_id,
        event_type="DISBURSAL",
        amount=float(offer["advance_amount"]),
        tx_id=disbursal_tx_id,
    )

    append_audit(
        action="OFFER_ACCEPTED",
        entity_id=offer["invoice_id"],
        amount=float(offer["advance_amount"]),
        outcome="SUCCESS",
        details={"offer_id": offer_id},
        connection=conn,
    )

    append_audit(
        action="DISBURSAL_DONE",
        entity_id=offer["invoice_id"],
        amount=float(offer["advance_amount"]),
        outcome="SUCCESS",
        details={"disbursal_tx_id": disbursal_tx_id},
        connection=conn,
    )

    send_whatsapp(
        phone=merchant_id,
        message=f"Your advance of Rs.{offer['advance_amount']} is on its way.",
        connection=conn,
    )

    return {
        "status": "accepted",
        "disbursal_tx_id": disbursal_tx_id,
        "invoice_id": offer["invoice_id"],
        "advance_amount": float(offer["advance_amount"]),
        "updated_invoice_status": "FINANCED",
    }
