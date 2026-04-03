from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.audit import write_entry
from app.database import (
    COLL_GST_DRAFTS,
    COLL_MERCHANTS,
    COLL_TRANSACTIONS,
    DatabaseClient,
    demo_mode_enabled,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.dependencies import get_firestore_db
from app.seed import SEED_MERCHANT_ID, ensure_seed_data

router = APIRouter()
_EPHEMERAL_GST_DRAFTS: dict[str, dict[str, Any]] = {}


def _derive_gst_profile(tx_id: str) -> tuple[float, str, str]:
    bucket = sum(ord(ch) for ch in tx_id) % 4
    if bucket == 0:
        return 0.05, "B2C_LOCAL", "19059040"
    if bucket == 1:
        return 0.12, "B2B", "34011190"
    if bucket == 2:
        return 0.18, "B2C_INTERSTATE", "21069099"
    return 0.0, "EXEMPT", "998599"


def _derive_transactions_from_ledger(db: DatabaseClient, merchant_id: str) -> list[dict[str, Any]]:
    rows = list_documents(
        db,
        COLL_TRANSACTIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=False,
        limit=5000,
    )

    transactions: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        amount = round(float(row.get("amount") or 0.0), 2)
        if amount == 0.0:
            continue

        tx_id = str(row.get("tx_id") or row.get("id") or f"TX-{merchant_id}-{index}")
        description = str(row.get("raw_description") or row.get("description") or "Transaction")
        gst_rate, category, hsn_code = _derive_gst_profile(tx_id)
        review_flag = bool(row.get("review_flag")) or amount < 0 or any(
            keyword in description.lower() for keyword in ("return", "refund", "chargeback", "dispute")
        )

        transactions.append(
            {
                "tx_id": tx_id,
                "description": description,
                "amount": amount,
                "hsn_code": hsn_code,
                "gst_rate": gst_rate,
                "category": category,
                "review_flag": review_flag,
                "edited_by_user": bool(row.get("edited_by_user")),
                "cgst": round((amount * gst_rate) / 2, 2),
                "sgst": round((amount * gst_rate) / 2, 2),
            }
        )

    return transactions


def _merchant_or_404(db: DatabaseClient, merchant_id: str) -> dict[str, Any]:
    try:
        merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    except Exception:
        merchant = None

    if not merchant and demo_mode_enabled() and merchant_id == SEED_MERCHANT_ID:
        try:
            ensure_seed_data(db, force=False)
            merchant = get_document(db, COLL_MERCHANTS, merchant_id)
        except Exception:
            merchant = None

    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})
    return merchant


def _load_draft(db: DatabaseClient, merchant_id: str) -> dict[str, Any]:
    draft = _EPHEMERAL_GST_DRAFTS.get(merchant_id)
    if draft and list(draft.get("transactions") or []):
        return draft

    try:
        draft = get_document(db, COLL_GST_DRAFTS, merchant_id)
    except Exception:
        draft = None

    if draft and list(draft.get("transactions") or []):
        _EPHEMERAL_GST_DRAFTS[merchant_id] = draft
        return draft

    transactions = _derive_transactions_from_ledger(db, merchant_id)
    now = datetime.now(UTC)
    quarter = f"Q{((now.month - 1) // 3) + 1}"
    hydrated = {
        **(draft or {}),
        "merchant_id": merchant_id,
        "quarter": str((draft or {}).get("quarter") or quarter),
        "year": int((draft or {}).get("year") or now.year),
        "transactions": transactions,
        "summary": _summary(transactions),
        "generated_at": utc_now_iso(),
    }
    _save_draft(db, hydrated)
    return hydrated


def _txn_shape(row: dict[str, Any]) -> dict[str, Any]:
    review_flag = bool(row.get("review_flag"))
    category = str(row.get("category") or "B2B")
    return {
        "tx_id": str(row.get("tx_id") or ""),
        "description": str(row.get("description") or ""),
        "amount": float(row.get("amount") or 0.0),
        "hsn_code": str(row.get("hsn_code") or ""),
        "gst_rate": float(row.get("gst_rate") or 0.0),
        "gst_category": category,
        "cgst": float(row.get("cgst") or 0.0),
        "sgst": float(row.get("sgst") or 0.0),
        "review_flag": review_flag,
        "status": "needs_review" if review_flag else "ready",
    }


def _recompute_tax(row: dict[str, Any]) -> None:
    amount = float(row.get("amount") or 0.0)
    rate = float(row.get("gst_rate") or 0.0)
    row["cgst"] = round((amount * rate) / 2, 2)
    row["sgst"] = round((amount * rate) / 2, 2)


def _summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    total_taxable = round(sum(float(row.get("amount") or 0.0) for row in transactions), 2)
    total_cgst = round(sum(float(row.get("cgst") or 0.0) for row in transactions), 2)
    total_sgst = round(sum(float(row.get("sgst") or 0.0) for row in transactions), 2)
    flagged_count = sum(1 for row in transactions if bool(row.get("review_flag")))

    return {
        "total_taxable": total_taxable,
        "total_cgst": total_cgst,
        "total_sgst": total_sgst,
        "net_liability": round(total_cgst + total_sgst, 2),
        "flagged_count": flagged_count,
        "total_count": len(transactions),
    }


def _save_draft(db: DatabaseClient, draft: dict[str, Any]) -> None:
    merchant_id = str(draft.get("merchant_id") or "")
    _EPHEMERAL_GST_DRAFTS[merchant_id] = draft
    try:
        upsert_document(db, COLL_GST_DRAFTS, merchant_id, draft, merge=False)
    except Exception:
        pass


def _build_gstr1(merchant_id: str, transactions: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_txn_shape(row) for row in transactions]

    def compact(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "tx_id": row["tx_id"],
            "description": row["description"],
            "amount": row["amount"],
            "hsn_code": row["hsn_code"],
            "gst_rate": row["gst_rate"],
            "cgst": row["cgst"],
            "sgst": row["sgst"],
        }

    table_4 = [compact(row) for row in normalized if row["gst_category"] == "B2B"]
    table_5 = [compact(row) for row in normalized if row["gst_category"] in {"B2C_LOCAL", "B2C_INTERSTATE"}]
    table_7 = [compact(row) for row in normalized if row["gst_category"] == "EXEMPT"]

    return {
        "merchant_id": merchant_id,
        "generated_at": utc_now_iso(),
        "table_4": table_4,
        "table_5": table_5,
        "table_7": table_7,
        "summary": {
            "total_records": len(normalized),
            "total_taxable_value": round(sum(row["amount"] for row in normalized), 2),
            "total_tax": round(sum(row["cgst"] + row["sgst"] for row in normalized), 2),
            "b2b_records": len(table_4),
            "b2c_records": len(table_5),
            "exempt_records": len(table_7),
        },
    }


def _build_gstr3b(merchant_id: str, transactions: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_txn_shape(row) for row in transactions]
    taxable = [row for row in normalized if row["gst_category"] != "EXEMPT"]
    exempt = [row for row in normalized if row["gst_category"] == "EXEMPT"]

    total_cgst = round(sum(row["cgst"] for row in normalized), 2)
    total_sgst = round(sum(row["sgst"] for row in normalized), 2)
    gross_tax = round(total_cgst + total_sgst, 2)
    itc_available = round(gross_tax * 0.2, 2)

    return {
        "merchant_id": merchant_id,
        "generated_at": utc_now_iso(),
        "taxable_value": round(sum(row["amount"] for row in taxable), 2),
        "exempt_value": round(sum(row["amount"] for row in exempt), 2),
        "total_cgst": total_cgst,
        "total_sgst": total_sgst,
        "itc_available": itc_available,
        "net_payable": round(max(gross_tax - itc_available, 0.0), 2),
        "record_count": len(normalized),
    }


def _parse_queue_id(queue_id: str) -> tuple[str, str]:
    if ":" in queue_id:
        merchant_id, tx_id = queue_id.split(":", 1)
        if merchant_id and tx_id:
            return merchant_id, tx_id
    raise HTTPException(status_code=400, detail={"error": "invalid_queue_id", "queue_id": queue_id})


@router.get("/dashboard/{merchant_id}")
def get_dashboard(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    transactions = list(draft.get("transactions") or [])

    summary = _summary(transactions)
    return {
        "merchant_id": merchant_id,
        "summary": {
            "total_transactions": summary["total_count"],
            "flagged_transactions": summary["flagged_count"],
            "total_taxable": summary["total_taxable"],
            "total_cgst": summary["total_cgst"],
            "total_sgst": summary["total_sgst"],
            "net_liability": summary["net_liability"],
            "last_generated_at": draft.get("generated_at") or utc_now_iso(),
        },
        "gstr1_generated": bool(draft.get("gstr1_draft")),
        "gstr3b_generated": bool(draft.get("gstr3b_summary")),
    }


@router.get("/transactions/{merchant_id}")
def get_transactions(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    return [_txn_shape(row) for row in list(draft.get("transactions") or [])]


@router.get("/review/queue/{merchant_id}")
def get_review_queue(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)

    queue: list[dict[str, Any]] = []
    for row in list(draft.get("transactions") or []):
        if not bool(row.get("review_flag")):
            continue

        shaped = _txn_shape(row)
        queue.append(
            {
                "queue_id": f"{merchant_id}:{shaped['tx_id']}",
                "merchant_id": merchant_id,
                "tx_id": shaped["tx_id"],
                "description": shaped["description"],
                "amount": shaped["amount"],
                "current_hsn": shaped["hsn_code"],
                "current_gst_rate": shaped["gst_rate"],
                "gst_category": shaped["gst_category"],
                "review_flag": True,
                "status": "needs_review",
            }
        )

    return queue


@router.put("/review/{queue_id}/resolve")
def resolve_review_item(queue_id: str, payload: dict[str, Any], db: DatabaseClient = Depends(get_firestore_db)):
    merchant_id, tx_id = _parse_queue_id(queue_id)
    _merchant_or_404(db, merchant_id)

    draft = _load_draft(db, merchant_id)
    transactions = list(draft.get("transactions") or [])

    target: dict[str, Any] | None = None
    for row in transactions:
        if str(row.get("tx_id") or "") == tx_id:
            target = row
            break

    if target is None:
        raise HTTPException(status_code=404, detail={"error": "queue_item_not_found", "queue_id": queue_id})

    if payload.get("hsn_code") is not None:
        target["hsn_code"] = str(payload.get("hsn_code"))
    if payload.get("gst_rate") is not None:
        target["gst_rate"] = float(payload.get("gst_rate"))

    target["review_flag"] = False
    target["edited_by_user"] = True
    _recompute_tax(target)

    updated = {
        **draft,
        "transactions": transactions,
        "summary": _summary(transactions),
        "generated_at": utc_now_iso(),
    }
    _save_draft(db, updated)

    try:
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="gst_review_resolved",
            entity_id=tx_id,
            amount=float(target.get("amount") or 0.0),
            outcome="success",
            metadata={
                "queue_id": queue_id,
                "hsn_code": target.get("hsn_code"),
                "gst_rate": target.get("gst_rate"),
            },
        )
    except Exception:
        pass

    return {
        "status": "updated",
        "queue_id": queue_id,
        "merchant_id": merchant_id,
        "tx_id": tx_id,
        "updated_at": utc_now_iso(),
    }


@router.post("/gstr1/generate/{merchant_id}")
def generate_gstr1(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    transactions = list(draft.get("transactions") or [])

    gstr1 = _build_gstr1(merchant_id, transactions)
    updated = {
        **draft,
        "gstr1_draft": gstr1,
        "generated_at": utc_now_iso(),
    }
    _save_draft(db, updated)

    try:
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="gstr1_generated",
            entity_id=merchant_id,
            amount=float(gstr1["summary"].get("total_tax", 0.0)),
            outcome="success",
            metadata={"record_count": gstr1["summary"].get("total_records", 0)},
        )
    except Exception:
        pass

    return {
        "status": "completed",
        "merchant_id": merchant_id,
        "generated_at": gstr1["generated_at"],
        "record_count": gstr1["summary"].get("total_records", 0),
    }


@router.get("/gstr1/draft/{merchant_id}")
def get_gstr1_draft(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    payload = draft.get("gstr1_draft")
    if not payload:
        raise HTTPException(status_code=404, detail={"error": "gstr1_not_generated", "merchant_id": merchant_id})
    return payload


@router.post("/gstr3b/generate/{merchant_id}")
def generate_gstr3b(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    transactions = list(draft.get("transactions") or [])

    gstr3b = _build_gstr3b(merchant_id, transactions)
    updated = {
        **draft,
        "gstr3b_summary": gstr3b,
        "generated_at": utc_now_iso(),
    }
    _save_draft(db, updated)

    try:
        write_entry(
            db,
            actor_type="merchant",
            actor_id=merchant_id,
            action="gstr3b_generated",
            entity_id=merchant_id,
            amount=float(gstr3b.get("net_payable") or 0.0),
            outcome="success",
            metadata={"record_count": gstr3b.get("record_count", 0)},
        )
    except Exception:
        pass

    return {
        "status": "completed",
        "merchant_id": merchant_id,
        "generated_at": gstr3b["generated_at"],
        "record_count": gstr3b.get("record_count", 0),
    }


@router.get("/gstr3b/summary/{merchant_id}")
def get_gstr3b_summary(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)
    draft = _load_draft(db, merchant_id)
    payload = draft.get("gstr3b_summary")
    if not payload:
        raise HTTPException(status_code=404, detail={"error": "gstr3b_not_generated", "merchant_id": merchant_id})
    return payload
