from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.audit import write_entry
from app.database import (
    ALL_COLLECTIONS,
    COLL_CREDIT_OFFERS,
    COLL_DEMO_STATE,
    COLL_GST_DRAFTS,
    COLL_INVOICES,
    COLL_MERCHANTS,
    COLL_NOTIFICATIONS,
    COLL_PENDING_TRANSFERS,
    COLL_TRANSACTIONS,
    COLL_TRUSTSCORE_HISTORY,
    DatabaseClient,
    count_collection,
    delete_collection,
    get_document,
    list_documents,
    upsert_document,
    utc_now_iso,
)
from app.notifications import create_notification
from data.synthetic_txns import generate_transactions_for_merchants

SEED_MERCHANT_ID = "seller_a"
ADMIN_MERCHANT_ID = "admin_hq"
PIN_HASH_1234 = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
PIN_HASH_9999 = "888df25ae35772424e2fcbf7ffb9c7f1f5e20a8f6f1d7f76f28fd00a355b0f7e"


def _merchants_file() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "merchants.json"


def _load_merchants_catalog() -> list[dict]:
    payload = json.loads(_merchants_file().read_text())
    if not isinstance(payload, list):
        raise ValueError("data/merchants.json must be a list")
    return payload


def _trust_bucket(score: int) -> str:
    if score <= 40:
        return "Low"
    if score <= 65:
        return "Medium"
    if score <= 80:
        return "Good"
    return "Excellent"


def _build_gst_transactions(count: int = 847) -> list[dict]:
    rows: list[dict] = []
    rates = [0.0, 0.05, 0.12, 0.18]
    categories = ["B2B", "B2C_LOCAL", "B2C_INTERSTATE", "EXEMPT"]

    for i in range(1, count + 1):
        amount = round(700 + ((i * 37) % 7800), 2)
        rate = rates[i % len(rates)]
        category = categories[i % len(categories)]
        if category == "EXEMPT":
            rate = 0.0

        cgst = round((amount * rate) / 2, 2)
        sgst = round((amount * rate) / 2, 2)

        rows.append(
            {
                "tx_id": f"GST-{i:04d}",
                "description": f"PayBot sale #{i}",
                "amount": amount,
                "hsn_code": f"{10000000 + (i % 999999)}",
                "gst_rate": rate,
                "cgst": cgst,
                "sgst": sgst,
                "category": category,
                "review_flag": False,
                "edited_by_user": False,
            }
        )

    rows[-1]["review_flag"] = True
    rows[-2]["review_flag"] = True
    rows[-3]["review_flag"] = True
    rows[-1]["hsn_code"] = "99999999"
    rows[-2]["hsn_code"] = "88888888"
    rows[-3]["hsn_code"] = "77777777"
    return rows


def _summarize_gst(rows: list[dict]) -> dict:
    total_taxable = round(sum(float(row["amount"]) for row in rows), 2)
    total_cgst = round(sum(float(row["cgst"]) for row in rows), 2)
    total_sgst = round(sum(float(row["sgst"]) for row in rows), 2)
    return {
        "total_taxable": total_taxable,
        "total_cgst": total_cgst,
        "total_sgst": total_sgst,
        "net_liability": round(total_cgst + total_sgst, 2),
        "flagged_count": sum(1 for row in rows if row.get("review_flag")),
        "total_count": len(rows),
    }


def _seed_merchants(db: DatabaseClient) -> list[dict]:
    merchants = _load_merchants_catalog()

    for idx, merchant in enumerate(merchants):
        merchant_id = merchant["merchant_id"]
        score = 74 if merchant_id == SEED_MERCHANT_ID else max(46, 82 - (idx % 9) * 4)

        payload = {
            "merchant_id": merchant_id,
            "name": merchant["name"],
            "business_name": merchant["business_name"],
            "category": merchant["category"],
            "city": merchant["city"],
            "phone": merchant["phone"],
            "gstin": merchant["gstin"],
            "kyc_status": merchant.get("kyc_status", "pending"),
            "wallet_balance": float(merchant.get("wallet_balance", 0.0)),
            "upi_id": f"{merchant_id}@paytm",
            "role": "merchant",
            "pin_hash": PIN_HASH_1234,
            "trust_score": score,
            "trust_bucket": _trust_bucket(score),
            "created_at": datetime(2025, 6, 11, tzinfo=UTC).isoformat(),
            "updated_at": utc_now_iso(),
        }
        upsert_document(db, COLL_MERCHANTS, merchant_id, payload, merge=False)

    admin_payload = {
        "merchant_id": ADMIN_MERCHANT_ID,
        "name": "ArthSetu Admin",
        "business_name": "ArthSetu HQ",
        "category": "Operations",
        "city": "Delhi",
        "phone": "+91-99999-00000",
        "gstin": "07AAECA2026A1ZA",
        "kyc_status": "verified",
        "wallet_balance": 0.0,
        "upi_id": f"{ADMIN_MERCHANT_ID}@paytm",
        "role": "admin",
        "pin_hash": PIN_HASH_9999,
        "trust_score": 86,
        "trust_bucket": "Excellent",
        "created_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
        "updated_at": utc_now_iso(),
    }
    upsert_document(db, COLL_MERCHANTS, ADMIN_MERCHANT_ID, admin_payload, merge=False)

    return merchants


def _seed_transactions(db: DatabaseClient, merchant_ids: list[str]) -> None:
    all_rows = generate_transactions_for_merchants(merchant_ids, days=180)
    for row in all_rows:
        upsert_document(db, COLL_TRANSACTIONS, row["tx_id"], row, merge=False)


def _seed_invoices(db: DatabaseClient) -> None:
    today = date.today()

    invoices = [
        {
            "invoice_id": "INV-041",
            "merchant_id": SEED_MERCHANT_ID,
            "seller_id": SEED_MERCHANT_ID,
            "buyer_name": "Acme Retail LLP",
            "buyer_gstin": "06AACCA1111A1Z5",
            "amount": 42000.0,
            "due_date": (today - timedelta(days=5)).isoformat(),
            "status": "PENDING",
            "overdue_days": 0,
            "advance_amount": 0.0,
            "fee_rate": 0.0,
            "offer_id": None,
            "repaid": False,
            "created_at": (today - timedelta(days=42)).isoformat(),
            "paid_at": None,
        },
        {
            "invoice_id": "INV-042",
            "merchant_id": SEED_MERCHANT_ID,
            "seller_id": SEED_MERCHANT_ID,
            "buyer_name": "Metro Supplies",
            "buyer_gstin": "07AAGCM2222B1ZY",
            "amount": 36500.0,
            "due_date": (today - timedelta(days=28)).isoformat(),
            "status": "PAID",
            "overdue_days": 0,
            "advance_amount": 0.0,
            "fee_rate": 0.0,
            "offer_id": None,
            "repaid": True,
            "created_at": (today - timedelta(days=60)).isoformat(),
            "paid_at": (today - timedelta(days=25)).isoformat(),
        },
        {
            "invoice_id": "INV-043",
            "merchant_id": SEED_MERCHANT_ID,
            "seller_id": SEED_MERCHANT_ID,
            "buyer_name": "Pioneer Traders",
            "buyer_gstin": "07BBCCP3333K1Z1",
            "amount": 51000.0,
            "due_date": (today - timedelta(days=21)).isoformat(),
            "status": "OVERDUE",
            "overdue_days": 21,
            "advance_amount": 0.0,
            "fee_rate": 0.0,
            "offer_id": None,
            "repaid": False,
            "created_at": (today - timedelta(days=55)).isoformat(),
            "paid_at": None,
        },
        {
            "invoice_id": "INV-044",
            "merchant_id": SEED_MERCHANT_ID,
            "seller_id": SEED_MERCHANT_ID,
            "buyer_name": "Sapphire Supermarket",
            "buyer_gstin": "07AAVCS4444Q1ZA",
            "amount": 28500.0,
            "due_date": (today - timedelta(days=18)).isoformat(),
            "status": "OVERDUE",
            "overdue_days": 18,
            "advance_amount": 0.0,
            "fee_rate": 0.0,
            "offer_id": None,
            "repaid": False,
            "created_at": (today - timedelta(days=50)).isoformat(),
            "paid_at": None,
        },
        {
            "invoice_id": "INV-045",
            "merchant_id": SEED_MERCHANT_ID,
            "seller_id": SEED_MERCHANT_ID,
            "buyer_name": "Northline Distributors",
            "buyer_gstin": "07AAGTN5555L1ZX",
            "amount": 61200.0,
            "due_date": (today + timedelta(days=12)).isoformat(),
            "status": "PENDING",
            "overdue_days": 0,
            "advance_amount": 0.0,
            "fee_rate": 0.0,
            "offer_id": None,
            "repaid": False,
            "created_at": (today - timedelta(days=15)).isoformat(),
            "paid_at": None,
        },
    ]

    for invoice in invoices:
        upsert_document(db, COLL_INVOICES, invoice["invoice_id"], invoice, merge=False)


def _seed_trustscore_history(db: DatabaseClient, merchants: list[dict]) -> None:
    today = date.today()

    for idx, merchant in enumerate(merchants):
        merchant_id = merchant["merchant_id"]
        base_score = 74 if merchant_id == SEED_MERCHANT_ID else max(46, 82 - (idx % 9) * 4)

        for week in range(13):
            dt = today - timedelta(days=(12 - week) * 7)
            score = min(100, max(25, base_score - 6 + (week // 2)))
            components = {
                "payment_rate": round(score * 0.3, 2),
                "consistency": round(score * 0.2, 2),
                "volume_trend": round(score * 0.2, 2),
                "gst_compliance": 13.0 if merchant_id == SEED_MERCHANT_ID else round(score * 0.2, 2),
                "return_rate": round(score * 0.1, 2),
            }
            doc_id = f"{merchant_id}-{dt.isoformat()}"
            upsert_document(
                db,
                COLL_TRUSTSCORE_HISTORY,
                doc_id,
                {
                    "merchant_id": merchant_id,
                    "date": dt.isoformat(),
                    "score": score,
                    "bucket": _trust_bucket(score),
                    "components": components,
                    "computed_at": datetime(dt.year, dt.month, dt.day, 9, 0, tzinfo=UTC).isoformat(),
                },
                merge=False,
            )


def _seed_gst_draft(db: DatabaseClient) -> None:
    txns = _build_gst_transactions()
    summary = _summarize_gst(txns)
    upsert_document(
        db,
        COLL_GST_DRAFTS,
        SEED_MERCHANT_ID,
        {
            "merchant_id": SEED_MERCHANT_ID,
            "quarter": "Q1",
            "year": 2026,
            "transactions": txns,
            "summary": summary,
            "generated_at": utc_now_iso(),
        },
        merge=False,
    )


def _seed_notifications_and_audit(db: DatabaseClient) -> None:
    create_notification(
        db,
        merchant_id=SEED_MERCHANT_ID,
        notif_type="gst",
        title="GST draft ready",
        body="Q1 2026 draft prepared with 847 transactions. 3 need review.",
        action_url="/merchant/gst/review",
    )
    create_notification(
        db,
        merchant_id=SEED_MERCHANT_ID,
        notif_type="finance",
        title="Invoice eligible for advance",
        body="INV-044 is overdue and eligible for finance.",
        action_url="/merchant/invoices/INV-044",
    )

    write_entry(
        db,
        actor_type="system",
        actor_id="seed",
        action="demo_seeded",
        entity_id=SEED_MERCHANT_ID,
        outcome="success",
        metadata={"rows": 847, "invoices": 5, "trust_score": 74},
    )


def _seed_demo_state(db: DatabaseClient) -> None:
    upsert_document(
        db,
        COLL_DEMO_STATE,
        SEED_MERCHANT_ID,
        {
            "merchant_id": SEED_MERCHANT_ID,
            "return_events": 0,
            "gst_override": None,
            "updated_at": utc_now_iso(),
        },
        merge=False,
    )


def ensure_seed_data(db: DatabaseClient, force: bool = False) -> int:
    existing = count_collection(db, COLL_MERCHANTS)
    if existing > 0 and not force:
        seller_exists = get_document(db, COLL_MERCHANTS, SEED_MERCHANT_ID) is not None
        admin_exists = get_document(db, COLL_MERCHANTS, ADMIN_MERCHANT_ID) is not None

        if not (seller_exists and admin_exists):
            _seed_merchants(db)

        seller_rows = [{"merchant_id": SEED_MERCHANT_ID}]
        merchant_ids = [SEED_MERCHANT_ID]

        existing_tx_for_seed = list_documents(
            db,
            COLL_TRANSACTIONS,
            filters=[("merchant_id", "==", SEED_MERCHANT_ID)],
            limit=1,
        )
        if not existing_tx_for_seed:
            _seed_transactions(db, merchant_ids)

        existing_invoices_for_seed = list_documents(
            db,
            COLL_INVOICES,
            filters=[("merchant_id", "==", SEED_MERCHANT_ID)],
            limit=1,
        )
        if not existing_invoices_for_seed:
            _seed_invoices(db)

        if get_document(db, COLL_GST_DRAFTS, SEED_MERCHANT_ID) is None:
            _seed_gst_draft(db)

        existing_history_for_seed = list_documents(
            db,
            COLL_TRUSTSCORE_HISTORY,
            filters=[("merchant_id", "==", SEED_MERCHANT_ID)],
            limit=1,
        )
        if not existing_history_for_seed:
            _seed_trustscore_history(db, seller_rows)

        existing_notif_for_seed = list_documents(
            db,
            COLL_NOTIFICATIONS,
            filters=[("merchant_id", "==", SEED_MERCHANT_ID)],
            limit=1,
        )
        if not existing_notif_for_seed:
            _seed_notifications_and_audit(db)

        if get_document(db, COLL_DEMO_STATE, SEED_MERCHANT_ID) is None:
            _seed_demo_state(db)

        return count_collection(db, COLL_MERCHANTS)

    if force:
        for collection_name in ALL_COLLECTIONS:
            delete_collection(db, collection_name)

    merchants = _seed_merchants(db)
    merchant_ids = [row["merchant_id"] for row in merchants]
    _seed_transactions(db, merchant_ids)
    _seed_invoices(db)
    _seed_trustscore_history(db, merchants)
    _seed_gst_draft(db)
    _seed_notifications_and_audit(db)
    _seed_demo_state(db)

    return count_collection(db, COLL_MERCHANTS)


def reset_demo_data(db: DatabaseClient) -> dict:
    # Keep reset lightweight and reliable for demo mode.
    # Full collection wipes can fail mid-way on quota-limited Firestore projects.
    status = "reset_complete"

    try:
        ensure_seed_data(db, force=False)
    except Exception:
        status = "reset_degraded"

    for collection_name in (COLL_CREDIT_OFFERS, COLL_PENDING_TRANSFERS):
        try:
            delete_collection(db, collection_name)
        except Exception:
            status = "reset_degraded"

    return {
        "status": status,
        "merchant_id": SEED_MERCHANT_ID,
        "reset_at": utc_now_iso(),
    }


def get_seed_balances(db: DatabaseClient) -> dict[str, float]:
    balances: dict[str, float] = {}
    for doc in db.collection(COLL_MERCHANTS).stream():
        row = doc.to_dict() or {}
        merchant_id = row.get("merchant_id") or doc.id
        balances[merchant_id] = float(row.get("wallet_balance") or 0.0)
    return balances
