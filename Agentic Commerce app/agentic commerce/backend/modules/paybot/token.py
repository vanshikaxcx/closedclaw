"""
ArthSetu PayBot — Scoped Delegation Token System
AP2 Intent Mandate implementation with HMAC-SHA256 signing.
Token lifecycle: active → exhausted | expired | revoked | pending_hitl
"""

import hmac
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

TOKEN_SECRET = os.getenv("TOKEN_SECRET", "arthsetu-paybot-secret-key-change-in-production")


def _sign_token(token_data: dict) -> str:
    """
    Compute HMAC-SHA256 signature of the token data.
    This simulates the AP2 VDC cryptographic proof.
    """
    # Create a canonical representation for signing
    # Normalize types to ensure consistency across DB round-trips
    signable = {
        "token_id": str(token_data["token_id"]),
        "user_id": str(token_data["user_id"]),
        "agent_id": str(token_data["agent_id"]),
        "budget_cap": float(token_data["budget_cap"]),
        "categories": sorted([str(c) for c in token_data["categories"]]),
        "valid_until": str(token_data["valid_until"]),
        "merchant_whitelist": sorted([str(m) for m in token_data["merchant_whitelist"]]),
    }
    message = json.dumps(signable, sort_keys=True, default=str)
    return hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(token_data: dict) -> bool:
    """Verify the HMAC-SHA256 signature of a token."""
    expected = _sign_token(token_data)
    return hmac.compare_digest(expected, token_data.get("signature", ""))


def generate_scoped_token(
    user_id: str,
    budget_cap: float,
    categories: list[str],
    items: list[dict],
    merchant_whitelist: list[str],
    prompt_playback: str,
    time_validity_hours: float = 2.0,
    hitl_threshold: float = 200.0,
) -> dict:
    """
    Generate a new scoped delegation token (AP2 Intent Mandate equivalent).
    """
    now = datetime.now(timezone.utc)
    token_id = f"tok_{uuid.uuid4().hex[:16]}"
    agent_id = f"agent_{uuid.uuid4().hex[:8]}_{int(now.timestamp())}"

    token = {
        "token_id": token_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "prompt_playback": prompt_playback,
        "budget_cap": budget_cap,
        "budget_spent": 0.0,
        "categories": categories,
        "merchant_whitelist": merchant_whitelist,
        "items": items,
        "created_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=time_validity_hours)).isoformat(),
        "tx_ids_used": [],
        "status": "active",
        "human_present": True,
        "hitl_threshold": hitl_threshold,
        "pending_hitl_token": None,
        "signature": "",  # placeholder — signed below
    }
    token["signature"] = _sign_token(token)
    return token


def is_token_expired(token: dict) -> bool:
    """Check if a token has expired based on valid_until."""
    valid_until = token.get("valid_until", "")
    if not valid_until:
        return True
    try:
        expiry = datetime.fromisoformat(valid_until)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry
    except (ValueError, TypeError):
        return True


def get_budget_remaining(token: dict) -> float:
    """Calculate remaining budget for a token."""
    return max(0, token["budget_cap"] - token["budget_spent"])


def get_expiry_seconds(token: dict) -> float:
    """Get seconds until token expiry."""
    try:
        expiry = datetime.fromisoformat(token["valid_until"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        delta = expiry - datetime.now(timezone.utc)
        return max(0, delta.total_seconds())
    except (ValueError, TypeError, KeyError):
        return 0
