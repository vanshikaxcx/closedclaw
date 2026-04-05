"""
ArthSetu PayBot — HITL (Human-in-the-Loop) Manager
Handles HITL order creation, approval, cancellation, and timeout.
Implements AP2 Human Present Transaction confirmation.
"""

import uuid
from datetime import datetime, timedelta, timezone

from backend.db import get_connection, set_token_hitl
from backend.audit import append_audit

# HITL order expires after 30 seconds
HITL_TIMEOUT_SECONDS = 30


def create_hitl_order(
    token_id: str,
    order_id: str,
    merchant_id: str,
    amount: float,
    line_items: list[dict],
) -> dict:
    """
    Create a pending HITL order requiring human approval.
    Called when transaction amount exceeds HITL threshold (Layer 3).
    """
    conn = get_connection()

    hitl_token = f"hitl_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=HITL_TIMEOUT_SECONDS)

    try:
        # Insert HITL order
        import json
        conn.execute(
            """INSERT INTO hitl_orders
            (hitl_token, token_id, order_id, merchant_id, amount, line_items, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (hitl_token, token_id, order_id, merchant_id, amount,
             json.dumps(line_items), expires_at.isoformat(), ),
        )

        # Update token with pending HITL
        set_token_hitl(conn, token_id, hitl_token)

        # Audit
        append_audit(
            conn=conn,
            token_id=token_id,
            action_type="HITL_TRIGGERED",
            actor="scope_enforcer",
            entity_id=order_id,
            amount=amount,
            merchant_id=merchant_id,
            outcome="pending",
            payload={
                "hitl_token": hitl_token,
                "expires_at": expires_at.isoformat(),
                "timeout_seconds": HITL_TIMEOUT_SECONDS,
            },
        )

        return {
            "status": "pending_approval",
            "hitl_token": hitl_token,
            "order_id": order_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "line_items": line_items,
            "expires_at": expires_at.isoformat(),
            "timeout_seconds": HITL_TIMEOUT_SECONDS,
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def approve_hitl_order(token_id: str, order_id: str, hitl_token: str) -> dict:
    """
    Approve a pending HITL order.
    Validates hitl_token matches and order hasn't expired.
    """
    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM hitl_orders WHERE hitl_token = ? AND token_id = ?",
            (hitl_token, token_id),
        ).fetchone()

        if not row:
            return {"error": "HITL order not found or token mismatch", "status": "failed"}

        order = dict(row)

        if order["status"] != "pending":
            return {"error": f"HITL order already {order['status']}", "status": "failed"}

        # Check expiry
        expires_at = datetime.fromisoformat(order["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            # Auto-cancel on timeout
            conn.execute(
                "UPDATE hitl_orders SET status = 'timeout' WHERE hitl_token = ?",
                (hitl_token,),
            )
            set_token_hitl(conn, token_id, None)
            conn.commit()

            append_audit(
                conn=conn,
                token_id=token_id,
                action_type="HITL_TIMEOUT",
                actor="hitl_manager",
                entity_id=order_id,
                amount=order["amount"],
                outcome="cancelled",
            )

            return {"error": "HITL order expired (30s timeout)", "status": "timeout"}

        # Approve
        conn.execute(
            "UPDATE hitl_orders SET status = 'approved' WHERE hitl_token = ?",
            (hitl_token,),
        )
        set_token_hitl(conn, token_id, None)
        conn.commit()

        append_audit(
            conn=conn,
            token_id=token_id,
            action_type="HITL_APPROVED",
            actor="user",
            entity_id=order_id,
            amount=order["amount"],
            merchant_id=order["merchant_id"],
            outcome="success",
        )

        import json
        return {
            "status": "approved",
            "order_id": order["order_id"],
            "merchant_id": order["merchant_id"],
            "amount": order["amount"],
            "line_items": json.loads(order["line_items"]),
        }

    finally:
        conn.close()


def cancel_hitl_order(token_id: str, hitl_token: str) -> dict:
    """Cancel a pending HITL order. Budget remains unchanged."""
    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM hitl_orders WHERE hitl_token = ? AND token_id = ?",
            (hitl_token, token_id),
        ).fetchone()

        if not row:
            return {"error": "HITL order not found", "status": "failed"}

        order = dict(row)

        conn.execute(
            "UPDATE hitl_orders SET status = 'cancelled' WHERE hitl_token = ?",
            (hitl_token,),
        )
        set_token_hitl(conn, token_id, None)
        conn.commit()

        append_audit(
            conn=conn,
            token_id=token_id,
            action_type="HITL_CANCELLED",
            actor="user",
            entity_id=order["order_id"],
            amount=order["amount"],
            outcome="cancelled",
        )

        return {
            "status": "cancelled",
            "order_id": order["order_id"],
            "message": "Order cancelled. Budget unchanged.",
        }

    finally:
        conn.close()


def get_pending_hitl(token_id: str) -> dict | None:
    """Get any pending HITL order for a token."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM hitl_orders WHERE token_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (token_id,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    import json
    order = dict(row)
    order["line_items"] = json.loads(order["line_items"])
    return order


def cleanup_expired_hitl() -> int:
    """Clean up expired HITL orders. Returns count of cleaned orders."""
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    rows = conn.execute(
        "SELECT * FROM hitl_orders WHERE status = 'pending' AND expires_at < ?",
        (now,),
    ).fetchall()

    count = 0
    for row in rows:
        order = dict(row)
        conn.execute(
            "UPDATE hitl_orders SET status = 'timeout' WHERE hitl_token = ?",
            (order["hitl_token"],),
        )
        set_token_hitl(conn, order["token_id"], None)
        count += 1

    conn.commit()
    conn.close()
    return count
