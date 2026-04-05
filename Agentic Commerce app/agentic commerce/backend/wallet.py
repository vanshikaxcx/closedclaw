"""
ArthSetu — Wallet Module
In-memory wallet with DB persistence for mock payment rails.
Handles /api/transfer and /api/check-balance logic.
"""

import uuid
from datetime import datetime, timezone

from backend.db import get_connection, get_user
from backend.audit import append_audit


def check_balance(user_id: str) -> dict:
    """Return the current wallet balance for a user."""
    conn = get_connection()
    user = get_user(conn, user_id)
    conn.close()
    if not user:
        return {"error": f"User {user_id} not found", "balance_inr": 0}
    return {"user_id": user_id, "balance_inr": user["wallet_balance"]}


def execute_transfer(
    user_id: str,
    merchant_id: str,
    amount: float,
    order_id: str,
    token_id: str | None = None,
    category: str | None = None,
    hsn_code: str | None = None,
) -> dict:
    """
    Execute a wallet transfer: debit user, credit merchant (as user balance).
    Writes to transactions table and appends audit log.
    Returns transaction receipt or error.
    """
    conn = get_connection()
    try:
        user = get_user(conn, user_id)
        if not user:
            return {"error": f"User {user_id} not found", "status": "failed"}

        if user["wallet_balance"] < amount:
            return {
                "error": "Insufficient balance",
                "balance": user["wallet_balance"],
                "required": amount,
                "status": "failed",
            }

        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

        # Debit user
        conn.execute(
            "UPDATE users SET wallet_balance = wallet_balance - ? WHERE user_id = ?",
            (amount, user_id),
        )

        # Credit merchant (if merchant has a user account, credit it — otherwise skip)
        merchant_as_user = get_user(conn, merchant_id)
        if merchant_as_user:
            conn.execute(
                "UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?",
                (amount, merchant_id),
            )

        # Write transaction record
        conn.execute(
            """INSERT INTO transactions
            (tx_id, merchant_id, user_id, amount, gst_category, hsn_code, status, order_id, token_id)
            VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)""",
            (tx_id, merchant_id, user_id, amount, category, hsn_code, order_id, token_id),
        )
        conn.commit()

        # Get updated balance
        updated_user = get_user(conn, user_id)
        balance_after = updated_user["wallet_balance"] if updated_user else 0

        # Append audit log
        append_audit(
            conn=conn,
            token_id=token_id,
            agent_id=None,
            action_type="PAYMENT_EXECUTED",
            actor="payment_agent",
            entity_id=tx_id,
            amount=amount,
            category=category,
            merchant_id=merchant_id,
            outcome="success",
            payload={
                "tx_id": tx_id,
                "user_id": user_id,
                "merchant_id": merchant_id,
                "amount": amount,
                "order_id": order_id,
            },
        )

        return {
            "status": "completed",
            "tx_id": tx_id,
            "amount": amount,
            "balance_after": balance_after,
            "merchant_id": merchant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        conn.rollback()
        return {"error": str(e), "status": "failed"}
    finally:
        conn.close()
