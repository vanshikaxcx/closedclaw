"""
ArthSetu PayBot — A2A Payment Agent
Isolated security boundary for payment execution.
This agent has NO access to user credentials — only receives token_id + order_id.
Implements tokenized payment execution (Layer 5).
"""

from backend.wallet import execute_transfer, check_balance
from backend.audit import append_audit
from backend.db import get_connection, update_token_budget


def execute_payment(
    user_id: str,
    merchant_id: str,
    amount: float,
    order_id: str,
    token_id: str,
    category: str | None = None,
    hsn_code: str | None = None,
) -> dict:
    """
    Execute payment through the isolated A2A payment agent.
    This agent:
    1. Receives only token_id + order_id (no credentials)
    2. Calls wallet.py for actual debit/credit
    3. Updates token budget atomically
    4. Logs to audit trail
    """
    # Execute wallet transfer
    result = execute_transfer(
        user_id=user_id,
        merchant_id=merchant_id,
        amount=amount,
        order_id=order_id,
        token_id=token_id,
        category=category,
        hsn_code=hsn_code,
    )

    if result.get("status") == "completed":
        # Update token budget atomically
        conn = get_connection()
        try:
            update_token_budget(conn, token_id, amount, order_id)
        finally:
            conn.close()

    return result


def get_user_balance(user_id: str) -> dict:
    """Get user balance through the payment agent."""
    return check_balance(user_id)


# ---------------------------------------------------------------------------
# x402 Integration Stub (Future: crypto rail via HTTP 402)
# ---------------------------------------------------------------------------

def x402_payment_stub(merchant_endpoint: str, order_payload: dict) -> dict:
    """
    x402 integration pattern for future crypto rail.
    When merchant endpoint returns HTTP 402 'Payment Required',
    PayBot would pay via stablecoin (USDC on Base).

    This is a stub — no real crypto settlement in prototype.
    """
    return {
        "status": "stub",
        "message": "x402 crypto rail not implemented in prototype",
        "pattern": {
            "step1": "POST to merchant_endpoint with order_payload",
            "step2": "If 402 returned, extract payment_required details",
            "step3": "Pay via x402_client.pay() with agent_wallet",
            "step4": "Retry with X-Payment header containing proof",
        },
    }
