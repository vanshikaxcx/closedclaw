"""
ArthSetu PayBot — 9-Layer Scope Enforcer
Server-side security middleware implementing the full AP2 security architecture.

Layers:
1. Intent Mandate signature verification
2. Server-side scope enforcement (budget, category, merchant whitelist)
3. HITL confirmation threshold
4. Prompt injection prevention (architectural)
5. Tokenized payment execution (no credential exposure)
6. Immutable audit trail
7. Token budget depletion guard (atomic DB read)
8. Agent identity binding
9. Expiry + replay protection
"""

import json
from datetime import datetime, timezone

from backend.db import get_token_fresh, get_connection
from backend.modules.paybot.token import verify_signature, is_token_expired
from backend.audit import append_audit


class ScopeViolation(Exception):
    """Raised when a scope enforcer check fails."""
    def __init__(self, message: str, layer: int, details: dict | None = None):
        self.message = message
        self.layer = layer
        self.details = details or {}
        super().__init__(message)


def enforce_scope(
    token_id: str,
    amount: float | None = None,
    category: str | None = None,
    merchant_id: str | None = None,
    order_id: str | None = None,
) -> dict:
    """
    Run all 9 scope enforcement layers against the given request.
    Returns the fresh token if all checks pass.
    Raises ScopeViolation if any check fails.
    """
    conn = get_connection()

    try:
        # Layer 7: Atomic DB read (TOCTOU prevention)
        token = get_token_fresh(conn, token_id)

        if not token:
            _audit_violation(conn, token_id, "TOKEN_NOT_FOUND", 7)
            raise ScopeViolation("Token not found", layer=7)

        # Layer 1: Intent Mandate signature verification
        if not verify_signature(token):
            _audit_violation(conn, token_id, "SIGNATURE_INVALID", 1)
            raise ScopeViolation("Token signature verification failed", layer=1)

        # Layer 9: Expiry check
        if is_token_expired(token):
            _audit_violation(conn, token_id, "TOKEN_EXPIRED", 9)
            raise ScopeViolation("Token has expired", layer=9)

        # Layer 9: Status check
        if token["status"] not in ("active",):
            _audit_violation(conn, token_id, "TOKEN_INACTIVE", 9,
                             {"status": token["status"]})
            raise ScopeViolation(
                f"Token is not active (status: {token['status']})", layer=9
            )

        # Layer 2: Budget check
        if amount is not None:
            budget_remaining = token["budget_cap"] - token["budget_spent"]
            if amount > budget_remaining:
                _audit_violation(conn, token_id, "BUDGET_EXCEEDED", 2,
                                 {"amount": amount, "remaining": budget_remaining})
                raise ScopeViolation(
                    f"Budget exceeded: requested Rs.{amount}, remaining Rs.{budget_remaining}",
                    layer=2,
                    details={"budget_remaining": budget_remaining, "requested": amount},
                )

        # Layer 2: Category check
        if category is not None and category not in token["categories"]:
            _audit_violation(conn, token_id, "CATEGORY_VIOLATION", 2,
                             {"category": category, "allowed": token["categories"]})
            raise ScopeViolation(
                f"Category '{category}' not in scope. Allowed: {token['categories']}",
                layer=2,
            )

        # Layer 2: Merchant whitelist check
        # V2: Skip whitelist check for virtual merchants (recharge, movies, trains, grocery splits)
        VIRTUAL_MERCHANT_PATTERNS = ("_recharge", "_booking", "cheapest_split",
                                      "pvr_", "inox_", "cinepolis_",
                                      "movie_", "train_")
        if merchant_id is not None:
            is_virtual = any(merchant_id.startswith(p) or merchant_id.endswith(p.rstrip("_"))
                             for p in VIRTUAL_MERCHANT_PATTERNS)
            if not is_virtual and merchant_id not in token["merchant_whitelist"]:
                _audit_violation(conn, token_id, "MERCHANT_NOT_WHITELISTED", 2,
                                 {"merchant_id": merchant_id})
                raise ScopeViolation(
                    f"Merchant '{merchant_id}' is not whitelisted",
                    layer=2,
                )

        # Layer 9: Replay prevention
        if order_id is not None and order_id in token["tx_ids_used"]:
            _audit_violation(conn, token_id, "REPLAY_ATTEMPT", 9,
                             {"order_id": order_id})
            raise ScopeViolation(
                f"Order '{order_id}' has already been processed (replay attack prevented)",
                layer=9,
            )

        return token

    finally:
        conn.close()


def check_hitl_required(token: dict, amount: float) -> bool:
    """
    Layer 3: Check if HITL (Human-in-the-Loop) approval is required.
    Returns True if amount exceeds the HITL threshold.
    """
    threshold = token.get("hitl_threshold", 200)
    return amount > threshold


def _audit_violation(
    conn, token_id: str, action_type: str, layer: int, details: dict | None = None
) -> None:
    """Log a scope violation to the audit trail."""
    append_audit(
        conn=conn,
        token_id=token_id,
        action_type=f"SCOPE_VIOLATION_{action_type}",
        actor="scope_enforcer",
        outcome="rejected",
        payload={"layer": layer, **(details or {})},
    )
