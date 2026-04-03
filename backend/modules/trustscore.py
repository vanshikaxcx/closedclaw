import json
from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException
from backend.audit import append_audit
from backend.db import get_db

trustscore_router = APIRouter()

def _components_from_score(score: int) -> dict:
    score_ratio = max(0.0, min(1.0, score / 100.0))
    return {
        "payment_rate": round(30 * score_ratio, 2),
        "consistency": round(20 * score_ratio, 2),
        "volume_trend": round(20 * score_ratio, 2),
        "gst_compliance": round(20 * score_ratio, 2),
        "return_rate": round(10 * score_ratio, 2),
    }


def _bucket(score: int) -> str:
    if score <= 40:
        return "Low"
    if score <= 65:
        return "Medium"
    if score <= 80:
        return "Good"
    return "Excellent"


@trustscore_router.get("/api/trustscore")
def get_trustscore(merchant_id: str = ""):
    merchant_id = merchant_id.strip()
    if not merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id is required")

    conn = get_db()
    current = conn.execute(
        "SELECT merchant_id, score FROM trustscores WHERE merchant_id = ?",
        (merchant_id,),
    ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail="merchant not found")

    history_rows = conn.execute(
        """
        SELECT score, components, computed_at
        FROM trustscore_history
        WHERE merchant_id = ?
        ORDER BY computed_at ASC
        """,
        (merchant_id,),
    ).fetchall()

    history = []
    components = _components_from_score(int(current["score"]))
    if history_rows:
        latest_components = history_rows[-1]["components"]
        components = json.loads(latest_components)
        for row in history_rows:
            history.append(
                {
                    "date": row["computed_at"],
                    "score": int(row["score"]),
                }
            )

    return {
        "merchant_id": merchant_id,
        "score": int(current["score"]),
        "bucket": _bucket(int(current["score"])),
        "components": components,
        "history": history,
    }


@trustscore_router.post("/api/trustscore-event")
def trustscore_event(payload: dict):
    merchant_id = (payload.get("merchant_id") or "").strip()
    event_type = (payload.get("event_type") or "").strip()

    if not merchant_id or not event_type:
        raise HTTPException(status_code=400, detail="merchant_id and event_type are required")

    deltas = {
        "PAYMENT_RECEIVED": 2,
        "GST_FILED": 5,
        "RETURN_RAISED": -4,
        "INVOICE_OVERDUE": -3,
    }
    if event_type not in deltas:
        raise HTTPException(status_code=400, detail="invalid event_type")

    conn = get_db()
    row = conn.execute(
        "SELECT score FROM trustscores WHERE merchant_id = ?",
        (merchant_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="merchant not found")

    updated_score = max(0, min(100, int(row["score"]) + deltas[event_type]))
    updated_at = datetime.now(UTC).isoformat()
    components = _components_from_score(updated_score)

    conn.execute(
        "UPDATE trustscores SET score = ?, updated_at = ? WHERE merchant_id = ?",
        (updated_score, updated_at, merchant_id),
    )
    conn.execute(
        """
        INSERT INTO trustscore_history (merchant_id, score, components, computed_at)
        VALUES (?, ?, ?, ?)
        """,
        (merchant_id, updated_score, json.dumps(components), updated_at),
    )

    append_audit(
        action="TRUSTSCORE_UPDATED",
        entity_id=merchant_id,
        outcome="SUCCESS",
        details={"event_type": event_type, "new_score": updated_score},
        connection=conn,
    )
    return {
        "merchant_id": merchant_id,
        "event_type": event_type,
        "score": updated_score,
        "bucket": _bucket(updated_score),
        "components": components,
    }
