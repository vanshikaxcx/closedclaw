from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.audit import write_entry
from app.database import DatabaseClient, clear_caches, count_collection, demo_mode_enabled, demo_reset_enabled, utc_now_iso
from app.dependencies import get_firestore_db
from app.schemas import HealthResponse, ResetDemoResponse, WhatsappAlertRequest
from app.seed import get_seed_balances, reset_demo_data
from app.wallet import is_loaded, reset as wallet_reset, sync_to_db
from app.whatsapp import send_alert

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def get_health(db: DatabaseClient = Depends(get_firestore_db)):
    try:
        merchant_count = count_collection(db, "merchants")
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "detail": "database unavailable"}) from exc

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": "connected",
        "wallet_store": "loaded" if is_loaded() else "not_loaded",
        "merchant_count": merchant_count,
        "demo_mode": demo_mode_enabled(),
        "timestamp": utc_now_iso(),
    }


@router.post("/reset-demo", response_model=ResetDemoResponse)
def post_reset_demo(db: DatabaseClient = Depends(get_firestore_db)):
    if not demo_reset_enabled():
        raise HTTPException(status_code=403, detail={"error": "demo_reset_disabled"})

    payload = reset_demo_data(db)

    try:
        balances = get_seed_balances(db)
    except Exception:
        balances = {}

    if balances:
        wallet_reset(balances)
    else:
        payload["status"] = "reset_degraded"

    if balances:
        try:
            sync_to_db(db)
        except Exception:
            payload["status"] = "reset_degraded"

    clear_caches()

    return payload


@router.post("/whatsapp-alert")
def post_whatsapp_alert(body: WhatsappAlertRequest, db: DatabaseClient = Depends(get_firestore_db)):
    response = send_alert(db, phone=body.phone, message=body.message)

    write_entry(
        db,
        actor_type="system",
        actor_id="whatsapp-service",
        action="whatsapp_alert_sent",
        entity_id=body.merchant_id,
        outcome="success" if response.get("sent") else "failed",
        metadata={"phone": body.phone, "sid": response.get("sid")},
    )

    return {
        "sent": bool(response.get("sent", False)),
        "queuedAt": utc_now_iso(),
        "mode": response.get("mode", "mock"),
    }
