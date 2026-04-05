from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.audit import write_entry
from app.database import (
    COLL_AUDIT_LOG,
    COLL_DEMO_STATE,
    COLL_GST_DRAFTS,
    COLL_INVOICES,
    COLL_MERCHANTS,
    COLL_TRANSACTIONS,
    COLL_TRUSTSCORE_HISTORY,
    DatabaseClient,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.dependencies import get_firestore_db
from app.notifications import create_notification
from app.schemas import TrustScoreEventRequest
from app.whatsapp import send_alert

router = APIRouter()


def _bucket(score: int) -> str:
    if score <= 40:
        return "Low"
    if score <= 65:
        return "Medium"
    if score <= 80:
        return "Good"
    return "Excellent"


def _safe_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _quarter_window(reference: date | None = None) -> tuple[date, date, date, date]:
    ref = reference or date.today()
    quarter = (ref.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    current_start = date(ref.year, start_month, 1)
    if quarter == 4:
        current_end = date(ref.year + 1, 1, 1)
    else:
        current_end = date(ref.year, start_month + 3, 1)

    previous_end = current_start
    if quarter == 1:
        previous_start = date(ref.year - 1, 10, 1)
    else:
        previous_start = date(ref.year, start_month - 3, 1)

    return current_start, current_end, previous_start, previous_end


def _daily_revenue(transactions: list[dict[str, Any]]) -> list[tuple[date, float]]:
    grouped: dict[date, float] = {}
    for row in transactions:
        dt = _safe_date(row.get("timestamp"))
        if dt is None:
            continue
        grouped[dt] = grouped.get(dt, 0.0) + float(row.get("amount") or 0.0)

    return sorted(grouped.items(), key=lambda item: item[0])


def _volume_trend_score(transactions: list[dict[str, Any]]) -> tuple[int, dict[str, float]]:
    today = date.today()
    recent_start = today - timedelta(days=30)
    prior_start = today - timedelta(days=60)

    recent: list[float] = []
    prior: list[float] = []

    for dt, amount in _daily_revenue(transactions):
        if dt >= recent_start:
            recent.append(amount)
        elif prior_start <= dt < recent_start:
            prior.append(amount)

    recent_avg = mean(recent) if recent else 0.0
    prior_avg = mean(prior) if prior else recent_avg

    if prior_avg <= 0:
        growth_pct = 0.0
    else:
        growth_pct = ((recent_avg - prior_avg) / prior_avg) * 100

    if growth_pct < -15:
        score = 2
    elif growth_pct < -5:
        score = 6
    elif growth_pct <= 5:
        score = 14
    else:
        score = 20

    return score, {
        "recent_30d_avg": round(recent_avg, 2),
        "prior_30d_avg": round(prior_avg, 2),
        "growth_pct": round(growth_pct, 1),
    }


def _compute_trust_components(db: DatabaseClient, merchant_id: str) -> tuple[dict[str, float], dict[str, Any]]:
    invoices = list_documents(db, COLL_INVOICES, filters=[("merchant_id", "==", merchant_id)])
    transactions = list_documents(db, COLL_TRANSACTIONS, filters=[("merchant_id", "==", merchant_id)])

    paid_invoices = [row for row in invoices if str(row.get("status", "")).upper() == "PAID"]
    on_time = 0
    for invoice in paid_invoices:
        paid_at = _safe_date(invoice.get("paid_at"))
        due_date = _safe_date(invoice.get("due_date"))
        if paid_at and due_date and paid_at <= due_date:
            on_time += 1

    if not paid_invoices:
        payment_rate = 15.0
    else:
        payment_rate = round((on_time / len(paid_invoices)) * 30.0, 2)

    paid_dates = sorted([_safe_date(row.get("paid_at")) for row in paid_invoices if _safe_date(row.get("paid_at"))])
    if len(paid_dates) < 3:
        consistency = 10.0
    else:
        intervals = [(paid_dates[idx] - paid_dates[idx - 1]).days for idx in range(1, len(paid_dates))]
        sigma = pstdev(intervals) if len(intervals) > 1 else 0.0
        if sigma <= 3:
            consistency = 20.0
        elif sigma <= 7:
            consistency = 15.0
        elif sigma <= 14:
            consistency = 10.0
        elif sigma <= 30:
            consistency = 5.0
        else:
            consistency = 2.0

    volume_trend, trend_meta = _volume_trend_score(transactions)

    demo_state = get_document(db, COLL_DEMO_STATE, merchant_id) or {}
    gst_override = demo_state.get("gst_override")
    if gst_override is not None:
        gst_compliance = float(gst_override)
    else:
        current_start, current_end, previous_start, previous_end = _quarter_window()
        audit_rows = list_documents(
            db,
            COLL_AUDIT_LOG,
            filters=[("actor_id", "==", merchant_id)],
            order_by="timestamp",
            descending=True,
            limit=400,
        )
        filed_dates = [
            _safe_date(row.get("timestamp"))
            for row in audit_rows
            if str(row.get("action", "")).upper() == "GST_FILED"
        ]
        filed_dates = [row for row in filed_dates if row]

        has_current = any(current_start <= row < current_end for row in filed_dates)
        has_previous = any(previous_start <= row < previous_end for row in filed_dates)
        if has_current:
            gst_compliance = 20.0
        elif has_previous:
            gst_compliance = 10.0
        else:
            gst_compliance = 0.0

    keywords = ("return", "refund", "dispute", "chargeback")
    explicit_returns = sum(
        1
        for row in transactions
        if any(key in str(row.get("raw_description", "")).lower() for key in keywords)
    )
    return_events = int(demo_state.get("return_events") or 0)
    return_count = explicit_returns + return_events

    total_tx = max(1, len(transactions))
    return_rate = max(0.0, round((1 - (return_count / total_tx)) * 10.0, 2))

    components = {
        "payment_rate": payment_rate,
        "consistency": consistency,
        "volume_trend": float(volume_trend),
        "gst_compliance": gst_compliance,
        "return_rate": return_rate,
    }
    meta = {
        "trend": trend_meta,
        "paid_invoice_count": len(paid_invoices),
        "transaction_count": len(transactions),
        "return_count": return_count,
    }
    return components, meta


def compute_trustscore_for_merchant(db: DatabaseClient, merchant_id: str, persist: bool = True) -> dict[str, Any]:
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    components, meta = _compute_trust_components(db, merchant_id)
    score = int(round(sum(components.values())))
    score = max(0, min(100, score))
    bucket = _bucket(score)
    computed_at = utc_now_iso()

    if persist:
        upsert_document(
            db,
            COLL_TRUSTSCORE_HISTORY,
            f"{merchant_id}-{uuid4().hex[:12]}",
            {
                "merchant_id": merchant_id,
                "date": computed_at[:10],
                "score": score,
                "bucket": bucket,
                "components": components,
                "computed_at": computed_at,
            },
            merge=False,
        )
        upsert_document(
            db,
            COLL_MERCHANTS,
            merchant_id,
            {
                "trust_score": score,
                "trust_bucket": bucket,
                "updated_at": computed_at,
            },
            merge=True,
        )

    history_rows = list_documents(
        db,
        COLL_TRUSTSCORE_HISTORY,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="computed_at",
        descending=False,
        limit=500,
    )

    cutoff = date.today() - timedelta(days=90)
    history = [
        {
            "date": str(row.get("date") or str(row.get("computed_at", ""))[:10]),
            "score": int(row.get("score") or 0),
            "bucket": row.get("bucket") or _bucket(int(row.get("score") or 0)),
            "components": row.get("components") or {},
        }
        for row in history_rows
        if (_safe_date(str(row.get("computed_at", ""))) or date.today()) >= cutoff
    ]

    return {
        "merchant_id": merchant_id,
        "score": score,
        "bucket": bucket,
        "components": components,
        "history": history,
        "computed_at": computed_at,
        "meta": meta,
    }


def process_trustscore_event(
    db: DatabaseClient,
    merchant_id: str,
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = metadata or {}

    previous = compute_trustscore_for_merchant(db, merchant_id, persist=False)
    previous_score = int(previous["score"])
    previous_bucket = str(previous["bucket"])

    if event_type == "GST_FILED":
        upsert_document(
            db,
            COLL_DEMO_STATE,
            merchant_id,
            {"merchant_id": merchant_id, "gst_override": 20.0, "updated_at": utc_now_iso()},
            merge=True,
        )
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="GST_FILED",
            entity_id=merchant_id,
            outcome="success",
            metadata=meta,
        )

    elif event_type == "PAYMENT_RECEIVED":
        invoice_id = str(meta.get("invoice_id") or "").strip()
        if not invoice_id:
            raise HTTPException(status_code=400, detail={"error": "invoice_id required for PAYMENT_RECEIVED"})
        invoice = get_document(db, COLL_INVOICES, invoice_id)
        if not invoice or invoice.get("merchant_id") != merchant_id:
            raise HTTPException(status_code=404, detail={"error": "invoice not found", "invoice_id": invoice_id})

        upsert_document(
            db,
            COLL_INVOICES,
            invoice_id,
            {
                "status": "PAID",
                "paid_at": utc_now_iso(),
                "repaid": True,
                "overdue_days": 0,
                "updated_at": utc_now_iso(),
            },
            merge=True,
        )

    elif event_type == "RETURN_RAISED":
        state = get_document(db, COLL_DEMO_STATE, merchant_id) or {"merchant_id": merchant_id, "return_events": 0}
        upsert_document(
            db,
            COLL_DEMO_STATE,
            merchant_id,
            {
                "merchant_id": merchant_id,
                "return_events": int(state.get("return_events") or 0) + 1,
                "updated_at": utc_now_iso(),
            },
            merge=True,
        )

    elif event_type == "INVOICE_OVERDUE":
        write_entry(
            db,
            actor_type="system",
            actor_id="invoice-engine",
            action="INVOICE_OVERDUE",
            entity_id=str(meta.get("invoice_id") or merchant_id),
            outcome="success",
            metadata=meta,
        )

    elif event_type == "TRANSFER_COMPLETED":
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="TRANSFER_COMPLETED",
            entity_id=str(meta.get("tx_id") or merchant_id),
            amount=float(meta.get("amount") or 0.0),
            outcome="success",
            metadata=meta,
        )
        create_notification(
            db,
            merchant_id=merchant_id,
            notif_type="transfer",
            title="Transfer completed",
            body="A wallet transfer was completed successfully.",
            action_url="/merchant/transfers",
        )

    else:
        raise HTTPException(status_code=400, detail={"error": "invalid event_type"})

    latest = compute_trustscore_for_merchant(db, merchant_id, persist=True)
    new_score = int(latest["score"])
    new_bucket = str(latest["bucket"])

    write_entry(
        db,
        actor_type="system",
        actor_id="trustscore-engine",
        action="TRUSTSCORE_UPDATED",
        entity_id=merchant_id,
        amount=float(new_score),
        outcome="success",
        metadata={
            "event_type": event_type,
            "previous_score": previous_score,
            "new_score": new_score,
            "score_delta": new_score - previous_score,
        },
    )

    return {
        "merchant_id": merchant_id,
        "event_processed": event_type,
        "previous_score": previous_score,
        "new_score": new_score,
        "score_delta": new_score - previous_score,
        "bucket_changed": previous_bucket != new_bucket,
        "new_bucket": new_bucket,
        "computed_at": latest["computed_at"],
    }


def _summarize_gst(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    total_taxable = round(sum(float(row.get("amount") or 0.0) for row in transactions), 2)
    total_cgst = round(sum(float(row.get("cgst") or 0.0) for row in transactions), 2)
    total_sgst = round(sum(float(row.get("sgst") or 0.0) for row in transactions), 2)
    return {
        "total_taxable": total_taxable,
        "total_cgst": total_cgst,
        "total_sgst": total_sgst,
        "net_liability": round(total_cgst + total_sgst, 2),
        "flagged_count": sum(1 for row in transactions if row.get("review_flag")),
        "total_count": len(transactions),
    }


@router.get("/trustscore")
def get_trustscore(merchant_id: str = Query(...), db: DatabaseClient = Depends(get_firestore_db)):
    try:
        return compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=True)
    except Exception:
        try:
            return compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=False)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "trustscore_unavailable",
                    "merchant_id": merchant_id,
                },
            ) from exc


@router.post("/trustscore-event")
def post_trustscore_event(body: TrustScoreEventRequest, db: DatabaseClient = Depends(get_firestore_db)):
    return process_trustscore_event(db, body.merchant_id, body.event_type, body.metadata)


@router.get("/trustscore/history")
def get_trustscore_history(
    merchant_id: str = Query(...),
    days: int = Query(default=90, ge=1, le=365),
    db: DatabaseClient = Depends(get_firestore_db),
):
    _ = get_document(db, COLL_MERCHANTS, merchant_id)
    if not _:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    rows = list_documents(
        db,
        COLL_TRUSTSCORE_HISTORY,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="computed_at",
        descending=False,
        limit=800,
    )

    cutoff = date.today() - timedelta(days=days)
    history = [
        {
            "date": str(row.get("date") or str(row.get("computed_at", ""))[:10]),
            "score": int(row.get("score") or 0),
            "bucket": row.get("bucket") or _bucket(int(row.get("score") or 0)),
            "components": row.get("components") or {},
        }
        for row in rows
        if (_safe_date(str(row.get("computed_at", ""))) or date.today()) >= cutoff
    ]

    return {"merchant_id": merchant_id, "days_requested": days, "history": history}


@router.get("/trustscore/leaderboard")
def get_trustscore_leaderboard(
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: DatabaseClient = Depends(get_firestore_db),
):
    merchants = list_documents(db, COLL_MERCHANTS, order_by="name", descending=False, limit=500)

    rows: list[dict[str, Any]] = []
    for merchant in merchants:
        if str(merchant.get("role") or "merchant") != "merchant":
            continue
        if category and str(merchant.get("category") or "").lower() != category.lower():
            continue

        merchant_id = str(merchant.get("merchant_id") or merchant.get("id"))
        score_payload = compute_trustscore_for_merchant(db, merchant_id=merchant_id, persist=True)
        rows.append(
            {
                "merchant_id": merchant_id,
                "name": merchant.get("name") or "",
                "business_name": merchant.get("business_name") or merchant.get("name") or "",
                "category": merchant.get("category") or "",
                "score": int(score_payload["score"]),
                "bucket": score_payload["bucket"],
            }
        )

    rows.sort(key=lambda item: item["score"], reverse=True)
    leaderboard = []
    for idx, row in enumerate(rows[:limit], start=1):
        leaderboard.append({"rank": idx, **row})

    return {"leaderboard": leaderboard, "generated_at": utc_now_iso()}


@router.get("/trustscore/health")
def get_trustscore_health(db: DatabaseClient = Depends(get_firestore_db)):
    rows = list_documents(db, COLL_TRUSTSCORE_HISTORY, order_by="computed_at", descending=True, limit=1000)
    merchants_scored = len({str(row.get("merchant_id") or "") for row in rows if row.get("merchant_id")})
    last_computation = rows[0].get("computed_at") if rows else None
    return {
        "status": "ok",
        "scoring_engine": "ready",
        "merchants_scored": merchants_scored,
        "last_computation": last_computation,
    }


@router.get("/gst-draft")
def get_gst_draft(merchant_id: str = Query(...), db: DatabaseClient = Depends(get_firestore_db)):
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    draft = get_document(db, COLL_GST_DRAFTS, merchant_id)
    if not draft:
        draft = {
            "merchant_id": merchant_id,
            "quarter": "Q1",
            "year": date.today().year,
            "transactions": [],
            "summary": {
                "total_taxable": 0,
                "total_cgst": 0,
                "total_sgst": 0,
                "net_liability": 0,
                "flagged_count": 0,
                "total_count": 0,
            },
            "generated_at": utc_now_iso(),
        }
        try:
            upsert_document(db, COLL_GST_DRAFTS, merchant_id, draft, merge=False)
        except Exception:
            pass

    return draft


@router.post("/gst-update-tx")
def post_gst_update_tx(payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id = str(payload.get("merchant_id") or payload.get("merchantId") or "").strip()
    tx_id = str(payload.get("tx_id") or payload.get("txId") or "").strip()
    if not merchant_id or not tx_id:
        raise HTTPException(status_code=400, detail={"error": "merchant_id and tx_id are required"})

    draft = get_document(db, COLL_GST_DRAFTS, merchant_id)
    if not draft:
        raise HTTPException(status_code=404, detail={"error": "gst draft not found", "merchant_id": merchant_id})

    transactions = list(draft.get("transactions") or [])
    target = None
    for row in transactions:
        if str(row.get("tx_id")) == tx_id:
            target = row
            break

    if not target:
        raise HTTPException(status_code=404, detail={"error": "transaction not found", "tx_id": tx_id})

    hsn_code = payload.get("hsn_code") if payload.get("hsn_code") is not None else payload.get("hsnCode")
    gst_rate = payload.get("gst_rate") if payload.get("gst_rate") is not None else payload.get("gstRate")
    category = payload.get("category")

    if hsn_code is not None:
        target["hsn_code"] = str(hsn_code)
    if gst_rate is not None:
        target["gst_rate"] = float(gst_rate)
    if category is not None:
        target["category"] = str(category)

    rate = float(target.get("gst_rate") or 0.0)
    amount = float(target.get("amount") or 0.0)
    target["cgst"] = round((amount * rate) / 2, 2)
    target["sgst"] = round((amount * rate) / 2, 2)
    target["review_flag"] = False
    target["edited_by_user"] = True

    summary = _summarize_gst(transactions)
    updated = {
        **draft,
        "transactions": transactions,
        "summary": summary,
        "generated_at": utc_now_iso(),
    }

    upsert_document(db, COLL_GST_DRAFTS, merchant_id, updated, merge=False)

    write_entry(
        db,
        actor_type="merchant",
        actor_id=merchant_id,
        action="gst_transaction_updated",
        entity_id=tx_id,
        amount=amount,
        outcome="success",
        metadata={"gst_rate": target.get("gst_rate"), "hsn_code": target.get("hsn_code")},
    )

    return updated


@router.post("/gst-file")
def post_gst_file(payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id = str(payload.get("merchant_id") or payload.get("merchantId") or "").strip()
    if not merchant_id:
        raise HTTPException(status_code=400, detail={"error": "merchant_id is required"})

    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})

    draft = get_document(db, COLL_GST_DRAFTS, merchant_id)
    if not draft:
        raise HTTPException(status_code=404, detail={"error": "gst draft not found", "merchant_id": merchant_id})

    txns = []
    for row in list(draft.get("transactions") or []):
        item = dict(row)
        item["review_flag"] = False
        txns.append(item)

    summary = _summarize_gst(txns)
    updated = {
        **draft,
        "transactions": txns,
        "summary": summary,
        "generated_at": utc_now_iso(),
    }
    upsert_document(db, COLL_GST_DRAFTS, merchant_id, updated, merge=False)

    ref_id = f"GST-REF-{date.today().year}-{uuid4().hex[:6].upper()}"
    filed_at = utc_now_iso()

    write_entry(
        db,
        actor_type="merchant",
        actor_id=merchant_id,
        action="GST_FILED",
        entity_id=ref_id,
        amount=float(summary.get("net_liability") or 0.0),
        outcome="success",
        metadata={"quarter": draft.get("quarter"), "year": draft.get("year")},
    )

    message = (
        f"ArthSetu Alert: Your GST return has been filed. Reference {ref_id}. "
        f"Tax liability: Rs. {summary.get('net_liability', 0)}."
    )
    wa = send_alert(db, phone=str(merchant.get("phone") or ""), message=message)

    create_notification(
        db,
        merchant_id=merchant_id,
        notif_type="gst",
        title="GST filed successfully",
        body=f"Filed return successfully. Reference: {ref_id}",
        action_url="/merchant/gst/history",
        whatsapp_sent=bool(wa.get("sent")),
    )

    process_trustscore_event(db, merchant_id, "GST_FILED", {"ref_id": ref_id})

    return {
        "status": "success",
        "ref_id": ref_id,
        "filed_at": filed_at,
        "whatsapp_sent": bool(wa.get("sent", False)),
        "phone": merchant.get("phone") or "",
    }
