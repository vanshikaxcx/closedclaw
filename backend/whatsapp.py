from datetime import UTC, datetime
from uuid import uuid4

from backend.audit import append_audit
from backend.db import get_db


def send_whatsapp(phone: str, message: str, connection=None) -> dict:
    conn = connection or get_db()
    sid = f"SM-{uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO whatsapp_log (sid, phone, message, sent_at) VALUES (?, ?, ?, ?)",
        (sid, phone, message, datetime.now(UTC).isoformat()),
    )
    append_audit(
        action="WHATSAPP_SENT",
        entity_id=phone,
        outcome="SUCCESS",
        details={"sid": sid, "message_preview": message[:80]},
        connection=conn,
    )
    return {"sent": True, "sid": sid}
