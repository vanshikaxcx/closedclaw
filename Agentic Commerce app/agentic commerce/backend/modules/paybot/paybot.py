"""
ArthSetu PayBot — FastAPI Router V2
All PayBot API endpoints including V2: agent sessions, domain search, selection HITL.
"""

import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.db import (
    get_connection, get_all_merchants, get_merchant, get_merchant_products,
    get_token_fresh, save_token, update_token_status, get_all_merchant_ids,
    get_session, get_pending_selection,
)
from backend.modules.paybot.intent_parser import parse_intent
from backend.modules.paybot.token import (
    generate_scoped_token, get_budget_remaining, get_expiry_seconds, is_token_expired,
)
from backend.modules.paybot.scope_enforcer import enforce_scope, check_hitl_required, ScopeViolation
from backend.modules.paybot.shopping_agent import search_merchants, prepare_order
from backend.modules.paybot.payment_agent import execute_payment, get_user_balance
from backend.modules.paybot.hitl import (
    create_hitl_order, approve_hitl_order, cancel_hitl_order,
    get_pending_hitl, cleanup_expired_hitl,
)
from backend.modules.paybot.orchestrator import (
    run_agent_for_intent, start_agent_session,
    resume_agent_session, get_session_status,
)
from backend.modules.paybot.task_classifier import classify_task, get_task_description
from backend.crawlers.grocery_crawler import compare_grocery_prices_sync
from backend.crawlers.movie_crawler import search_movie_shows
from backend.crawlers.train_crawler import search_trains
from backend.crawlers.recharge_crawler import find_best_recharge_plan, get_all_plans
from backend.audit import append_audit, get_audit_log

router = APIRouter(prefix="/api", tags=["PayBot"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ParseIntentRequest(BaseModel):
    user_input: str
    user_id: str = "priya_001"


class TransferRequest(BaseModel):
    token_id: str
    order_id: str
    merchant_id: str
    amount: float
    category: str = "general"


class TransferConfirmRequest(BaseModel):
    token_id: str
    order_id: str
    hitl_token: str


class TransferCancelRequest(BaseModel):
    token_id: str
    hitl_token: str


class AgentExecuteRequest(BaseModel):
    user_input: str
    user_id: str = "priya_001"


class AgentRunRequest(BaseModel):
    """V2: Start an agent session."""
    mandate_id: Optional[str] = None  # token_id
    user_id: str = "priya_001"
    user_input: Optional[str] = None  # can pass input directly


class AgentSelectRequest(BaseModel):
    """V2: Submit user selection for selection_hitl mode."""
    session_id: str
    option_id: str


class SearchMerchantsRequest(BaseModel):
    items: list[str]


class PrepareOrderRequest(BaseModel):
    merchant_id: str
    items: list[dict]


class TokenConfirmRequest(BaseModel):
    token_id: str


class TokenRevokeRequest(BaseModel):
    revoked: bool = True


# ---------------------------------------------------------------------------
# V1 Endpoints (unchanged)
# ---------------------------------------------------------------------------

@router.post("/parse-intent")
async def api_parse_intent(req: ParseIntentRequest):
    """
    POST /api/parse-intent
    Parse NL input → structured intent + scoped delegation token.
    V2: Now includes task_type + hitl_mode classification.
    """
    intent = parse_intent(req.user_input)

    conn = get_connection()
    merchant_ids = get_all_merchant_ids(conn)
    conn.close()

    token = generate_scoped_token(
        user_id=req.user_id,
        budget_cap=intent["budget_cap"],
        categories=intent["categories"],
        items=intent["items"],
        merchant_whitelist=merchant_ids,
        prompt_playback=req.user_input,
        time_validity_hours=intent.get("time_validity_hours", 2),
    )

    conn = get_connection()
    save_token(conn, token)
    conn.close()

    append_audit(
        token_id=token["token_id"],
        agent_id=token["agent_id"],
        action_type="INTENT_PARSED",
        actor="orchestrator",
        outcome="success",
        payload={"intent": intent, "user_input": req.user_input},
    )

    return {
        "intent": intent,
        "token_id": token["token_id"],
        "task_type": intent.get("task_type", "general_purchase"),
        "hitl_mode": intent.get("hitl_mode", "amount_hitl"),
        "mandate": {
            "token_id": token["token_id"],
            "budget_cap": token["budget_cap"],
            "categories": token["categories"],
            "valid_until": token["valid_until"],
        },
        "token": {
            "token_id": token["token_id"],
            "budget_cap": token["budget_cap"],
            "categories": token["categories"],
            "valid_until": token["valid_until"],
            "status": token["status"],
            "items": token["items"],
            "agent_id": token["agent_id"],
        },
    }


@router.post("/token/confirm")
async def api_confirm_token(req: TokenConfirmRequest):
    """Confirm token activation after user reviews intent."""
    conn = get_connection()
    token = get_token_fresh(conn, req.token_id)
    conn.close()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    append_audit(token_id=req.token_id, action_type="TOKEN_CONFIRMED", actor="user", outcome="success")
    return {"status": "active", "token_id": req.token_id, "message": "Token confirmed and active"}


@router.post("/agent/execute")
async def api_agent_execute(req: AgentExecuteRequest):
    """
    POST /api/agent/execute
    Full agent tool-calling loop (V1 compatible, uses V2 session system internally).
    """
    intent = parse_intent(req.user_input)

    conn = get_connection()
    merchant_ids = get_all_merchant_ids(conn)
    conn.close()

    token = generate_scoped_token(
        user_id=req.user_id,
        budget_cap=intent["budget_cap"],
        categories=intent["categories"],
        items=intent["items"],
        merchant_whitelist=merchant_ids,
        prompt_playback=req.user_input,
        time_validity_hours=intent.get("time_validity_hours", 2),
    )

    conn = get_connection()
    save_token(conn, token)
    conn.close()

    append_audit(
        token_id=token["token_id"],
        agent_id=token["agent_id"],
        action_type="INTENT_PARSED",
        actor="orchestrator",
        outcome="success",
        payload={"intent": intent},
    )

    result = run_agent_for_intent(
        token_id=token["token_id"],
        user_id=req.user_id,
        intent=intent,
        user_input=req.user_input,
    )

    return {
        "intent": intent,
        "token_id": token["token_id"],
        "token": {
            "token_id": token["token_id"],
            "budget_cap": token["budget_cap"],
            "categories": token["categories"],
            "valid_until": token["valid_until"],
        },
        "agent_result": result,
    }


# ---------------------------------------------------------------------------
# V2 Endpoints: Agent Sessions
# ---------------------------------------------------------------------------

@router.post("/agent-run")
async def api_agent_run(req: AgentRunRequest):
    """
    POST /api/agent-run
    Start a background agent session. Returns session_id for polling.
    V2 NEW
    """
    # If mandate_id provided, get token + intent from DB
    if req.mandate_id:
        conn = get_connection()
        token = get_token_fresh(conn, req.mandate_id)
        conn.close()
        if not token:
            raise HTTPException(status_code=404, detail="Token/mandate not found")

        user_input = req.user_input or token.get("prompt_playback", "")
        intent = parse_intent(user_input) if user_input else {
            "items": token.get("items", []),
            "budget_cap": token["budget_cap"],
            "categories": token["categories"],
            "task_type": "general_purchase",
            "hitl_mode": "amount_hitl",
        }

        result = start_agent_session(
            token_id=req.mandate_id,
            user_id=req.user_id,
            intent=intent,
            user_input=user_input,
        )
    else:
        # Parse intent and create token
        if not req.user_input:
            raise HTTPException(status_code=400, detail="user_input or mandate_id required")

        intent = parse_intent(req.user_input)

        conn = get_connection()
        merchant_ids = get_all_merchant_ids(conn)
        conn.close()

        token = generate_scoped_token(
            user_id=req.user_id,
            budget_cap=intent["budget_cap"],
            categories=intent["categories"],
            items=intent["items"],
            merchant_whitelist=merchant_ids,
            prompt_playback=req.user_input,
            time_validity_hours=intent.get("time_validity_hours", 2),
        )

        conn = get_connection()
        save_token(conn, token)
        conn.close()

        append_audit(
            token_id=token["token_id"],
            action_type="INTENT_PARSED",
            actor="orchestrator",
            outcome="success",
            payload={"intent": intent},
        )

        result = start_agent_session(
            token_id=token["token_id"],
            user_id=req.user_id,
            intent=intent,
            user_input=req.user_input,
        )

    return result


@router.get("/agent-status/{session_id}")
async def api_agent_status(session_id: str):
    """
    GET /api/agent-status/{session_id}
    Poll agent session status. Returns phase, steps, selection (if any), order, result.
    V2 NEW
    """
    result = get_session_status(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/agent-select")
async def api_agent_select(req: AgentSelectRequest):
    """
    POST /api/agent-select
    Submit user selection for selection_hitl mode. Resumes agent loop.
    V2 NEW
    """
    result = resume_agent_session(req.session_id, req.option_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# V2 Endpoints: Domain Search
# ---------------------------------------------------------------------------

@router.get("/prices/grocery")
async def api_grocery_prices(item: str, qty: str = "", live_only: bool = False):
    """
    GET /api/prices/grocery?item=atta+2kg
    Compare grocery prices across Blinkit, Zepto, BigBasket.
    Set live_only=true to disable fallback and return only live crawl results.
    V2 NEW — uses real Playwright crawlers with fallback.
    """
    items = [{"name": item, "qty": qty}]
    result = compare_grocery_prices_sync(items, use_fallback=not live_only)
    if result.get("comparisons"):
        comp = result["comparisons"][0]
        return {
            "item": item,
            "comparison": {
                "blinkit": comp.get("blinkit"),
                "zepto": comp.get("zepto"),
                "bigbasket": comp.get("bigbasket"),
            },
            "cheapest_platform": comp.get("cheapest_platform"),
            "cheapest_price": comp.get("cheapest_price"),
            "recommended": comp.get("cheapest_platform"),
        }
    return result


@router.get("/movies/search")
async def api_movie_search(
    movie: str,
    price_cap: float = 500,
    after: Optional[str] = None,
    city: Optional[str] = None,
):
    """
    GET /api/movies/search?movie=inception&price_cap=400&after=21:00
    Search for movie shows. Uses BookMyShow crawler with catalog fallback.
    V2 NEW
    """
    result = search_movie_shows(movie, price_cap, after, city)
    return result


@router.get("/trains/search")
async def api_train_search(
    from_city: str = "delhi",
    to_city: str = "mumbai",
    budget: float = 5000,
    preferred_class: Optional[str] = None,
):
    """
    GET /api/trains/search?from=delhi&to=mumbai&budget=2000
    Search for trains. Uses trainman crawler with catalog fallback.
    V2 NEW
    """
    result = search_trains(from_city, to_city, budget, preferred_class)
    return result


@router.get("/recharge/plans")
async def api_recharge_plans(
    operator: str = "jio",
    budget: float = 500,
    days: int = 28,
):
    """
    GET /api/recharge/plans?operator=jio&budget=300
    Search for recharge plans. Uses operator website crawler with catalog fallback.
    V2 NEW
    """
    result = find_best_recharge_plan(operator, budget, days)
    return result


# ---------------------------------------------------------------------------
# V1 Endpoints (transfers, merchants, etc.)
# ---------------------------------------------------------------------------

@router.post("/transfer")
async def api_transfer(req: TransferRequest):
    """POST /api/transfer — Initiate payment with scope enforcement."""
    try:
        token = enforce_scope(
            token_id=req.token_id,
            amount=req.amount,
            category=req.category,
            merchant_id=req.merchant_id,
            order_id=req.order_id,
        )
    except ScopeViolation as e:
        raise HTTPException(
            status_code=403,
            detail={"error": e.message, "layer": e.layer, "details": e.details},
        )

    if check_hitl_required(token, req.amount):
        hitl_result = create_hitl_order(
            token_id=req.token_id,
            order_id=req.order_id,
            merchant_id=req.merchant_id,
            amount=req.amount,
            line_items=[],
        )
        return hitl_result

    result = execute_payment(
        user_id=token["user_id"],
        merchant_id=req.merchant_id,
        amount=req.amount,
        order_id=req.order_id,
        token_id=req.token_id,
        category=req.category,
    )

    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)

    result["auto_approved"] = True
    return result


@router.post("/transfer-confirm")
async def api_transfer_confirm(req: TransferConfirmRequest):
    """POST /api/transfer-confirm — Execute payment after HITL approval."""
    approval = approve_hitl_order(req.token_id, req.order_id, req.hitl_token)
    if approval.get("status") != "approved":
        raise HTTPException(status_code=400, detail=approval)

    try:
        token = enforce_scope(
            token_id=req.token_id,
            amount=approval["amount"],
            merchant_id=approval["merchant_id"],
            order_id=approval["order_id"],
        )
    except ScopeViolation as e:
        raise HTTPException(status_code=403, detail={"error": e.message, "layer": e.layer})

    result = execute_payment(
        user_id=token["user_id"],
        merchant_id=approval["merchant_id"],
        amount=approval["amount"],
        order_id=approval["order_id"],
        token_id=req.token_id,
    )

    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/transfer-cancel")
async def api_transfer_cancel(req: TransferCancelRequest):
    """POST /api/transfer-cancel — Cancel pending HITL order."""
    result = cancel_hitl_order(req.token_id, req.hitl_token)
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/agent/search-merchants")
async def api_search_merchants(req: SearchMerchantsRequest, request: Request):
    """POST /api/agent/search-merchants"""
    token_id = request.headers.get("X-Token-Id")
    result = search_merchants(items=req.items, token_id=token_id)
    return result


@router.post("/agent/prepare-order")
async def api_prepare_order(req: PrepareOrderRequest, request: Request):
    """POST /api/agent/prepare-order"""
    token_id = request.headers.get("X-Token-Id")
    result = prepare_order(merchant_id=req.merchant_id, items=req.items, token_id=token_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/agent/check-balance")
async def api_check_balance(request: Request):
    """GET /api/agent/check-balance"""
    token_id = request.headers.get("X-Token-Id")
    user_id = request.query_params.get("user_id", "priya_001")
    if token_id:
        conn = get_connection()
        token = get_token_fresh(conn, token_id)
        conn.close()
        if not token or token["status"] != "active":
            raise HTTPException(status_code=403, detail="Token inactive or not found")
        user_id = token["user_id"]
    result = get_user_balance(user_id)
    return result


@router.get("/token-status")
async def api_token_status(token_id: str):
    """GET /api/token-status"""
    conn = get_connection()
    token = get_token_fresh(conn, token_id)
    conn.close()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return {
        "token_id": token_id,
        "status": "expired" if is_token_expired(token) else token["status"],
        "budget_cap": token["budget_cap"],
        "budget_spent": token["budget_spent"],
        "budget_remaining": get_budget_remaining(token),
        "expires_in_seconds": get_expiry_seconds(token),
        "valid_until": token["valid_until"],
        "categories": token["categories"],
        "transactions_count": len(token["tx_ids_used"]),
    }


@router.put("/token-status/{token_id}")
async def api_revoke_token(token_id: str, req: TokenRevokeRequest):
    """PUT /api/token-status/{token_id} — Revoke a token. V2 NEW."""
    conn = get_connection()
    token = get_token_fresh(conn, token_id)
    if not token:
        conn.close()
        raise HTTPException(status_code=404, detail="Token not found")
    if req.revoked:
        update_token_status(conn, token_id, "revoked")
        append_audit(token_id=token_id, action_type="TOKEN_REVOKED", actor="user", outcome="success")
    conn.close()
    return {"status": "revoked", "token_id": token_id}


@router.get("/merchants")
async def api_get_merchants(category: Optional[str] = None):
    """GET /api/merchants — All merchants + products."""
    conn = get_connection()
    merchants = get_all_merchants(conn)
    result = []
    for m in merchants:
        if category and m.get("category") != category:
            continue
        products = get_merchant_products(conn, m["merchant_id"])
        result.append({**m, "products": products})
    conn.close()
    return {"merchants": result, "total": len(result)}


@router.get("/merchants/{merchant_id}/catalog")
async def api_merchant_catalog(merchant_id: str):
    """GET /api/merchants/{id}/catalog — V2 NEW."""
    conn = get_connection()
    merchant = get_merchant(conn, merchant_id)
    if not merchant:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Merchant {merchant_id} not found")
    products = get_merchant_products(conn, merchant_id)
    conn.close()
    return {"merchant_id": merchant_id, "name": merchant["name"], "products": products}


@router.get("/audit-log")
async def api_audit_log(
    token_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
):
    """GET /api/audit-log — supports session_id filter (V2)."""
    entries = get_audit_log(token_id=token_id, limit=limit)
    return {"entries": entries, "count": len(entries)}


@router.get("/hitl/pending")
async def api_hitl_pending(token_id: str):
    """GET /api/hitl/pending"""
    pending = get_pending_hitl(token_id)
    if not pending:
        return {"pending": False}
    return {"pending": True, "order": pending}


@router.post("/hitl/cleanup")
async def api_hitl_cleanup():
    """Clean up expired HITL orders."""
    count = cleanup_expired_hitl()
    return {"cleaned": count}


@router.get("/users/{user_id}")
async def api_get_user(user_id: str):
    """GET /api/users/{user_id}"""
    from backend.db import get_user
    conn = get_connection()
    user = get_user(conn, user_id)
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.get("/health")
async def api_health():
    """Health check."""
    return {"status": "healthy", "service": "ArthSetu PayBot", "version": "2.0.0"}
