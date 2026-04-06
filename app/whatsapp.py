from __future__ import annotations

import os
from uuid import uuid4

from app.database import COLL_WHATSAPP_LOG, DatabaseClient, upsert_document, utc_now_iso


def _normalize_whatsapp_number(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return raw
    return raw if raw.startswith("whatsapp:") else f"whatsapp:{raw}"


def _send_with_twilio(phone: str, message: str) -> dict:
    from twilio.rest import Client

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    sender = (
        os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
        or os.getenv("TWILIO_PHONE_NUMBER", "").strip()
        or "whatsapp:+14155238886"
    )

    sender = _normalize_whatsapp_number(sender)
    to_phone = _normalize_whatsapp_number(phone)

    client = Client(account_sid, auth_token)
    msg = client.messages.create(from_=sender, body=message, to=to_phone)
    return {"sent": True, "sid": msg.sid, "mode": "twilio"}


def send_alert(db: DatabaseClient | None, phone: str, message: str) -> dict:
    mode = os.getenv("WHATSAPP_MODE", "mock").strip().lower() or "mock"
    
    # Override phone number if configured (for testing/demo purposes)
    override_phone = os.getenv("WHATSAPP_OVERRIDE_PHONE", "").strip()
    if override_phone:
        print(f"[WhatsApp] Overriding phone {phone} with {override_phone}")
        phone = override_phone

    if mode == "twilio":
        try:
            response = _send_with_twilio(phone=phone, message=message)
        except Exception as exc:
            print(f"[WhatsApp TWILIO ERROR] phone={phone} error={exc}")
            response = {"sent": False, "sid": f"TWILIO-ERR-{uuid4()}", "mode": "twilio"}
    else:
        print(f"[WhatsApp MOCK] To: {phone} | Message: {message}")
        response = {"sent": True, "sid": f"MOCK-SID-{uuid4()}", "mode": "mock"}

    payload = {
        "sid": response["sid"],
        "phone": phone,
        "message": message,
        "sent": bool(response.get("sent", False)),
        "mode": response.get("mode", mode),
        "timestamp": utc_now_iso(),
    }
    if db is not None:
        upsert_document(db, COLL_WHATSAPP_LOG, payload["sid"], payload, merge=False)

    return response
