"""
ArthSetu PayBot — MCP Tool Definitions V2
Defines tools for the Gemini function-calling loop.
V2 adds: search_recharge_plans, search_movie_shows, search_trains,
         compare_grocery_prices, present_selection
"""

import json
import os

from backend.modules.paybot.shopping_agent import search_merchants, prepare_order
from backend.modules.paybot.payment_agent import execute_payment, get_user_balance
from backend.modules.paybot.scope_enforcer import enforce_scope, check_hitl_required, ScopeViolation
from backend.modules.paybot.hitl import create_hitl_order
from backend.audit import append_audit
from backend.crawlers.movie_crawler import search_movie_shows
from backend.crawlers.train_crawler import search_trains
from backend.crawlers.recharge_crawler import find_best_recharge_plan
from backend.crawlers.grocery_crawler import compare_grocery_prices_sync


# ---------------------------------------------------------------------------
# Tool definitions for Gemini function calling
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "check_balance",
        "description": "Check the user's wallet balance. Returns balance in INR.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The user's ID"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "search_merchants",
        "description": "Search for merchants that sell specific items. Returns a list of matching merchants with products and prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of item names to search for",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "prepare_order",
        "description": "Prepare an order from a specific merchant's catalog. Returns order details with line items and total.",
        "parameters": {
            "type": "object",
            "properties": {
                "merchant_id": {"type": "string", "description": "The merchant's ID"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "qty": {"type": "integer"},
                        },
                    },
                    "description": "List of items with quantities",
                },
            },
            "required": ["merchant_id", "items"],
        },
    },
    {
        "name": "request_payment",
        "description": "Request payment for an order. Will trigger HITL approval if amount exceeds threshold.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "merchant_id": {"type": "string"},
                "amount": {"type": "number"},
                "order_id": {"type": "string"},
                "token_id": {"type": "string"},
                "category": {"type": "string"},
                "line_items": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Order line items for HITL display",
                },
            },
            "required": ["user_id", "merchant_id", "amount", "order_id", "token_id", "category"],
        },
    },
    # --- V2 Tools ---
    {
        "name": "search_recharge_plans",
        "description": "Search for mobile recharge plans. Returns best plan and all matching plans for an operator.",
        "parameters": {
            "type": "object",
            "properties": {
                "operator": {"type": "string", "description": "Mobile operator: jio, airtel, bsnl, vi"},
                "budget": {"type": "number", "description": "Maximum recharge amount in INR"},
                "days": {"type": "integer", "description": "Minimum validity in days (default: 28)"},
                "phone_number": {"type": "string", "description": "Phone number for auto-detection"},
            },
            "required": ["operator"],
        },
    },
    {
        "name": "search_movie_shows",
        "description": "Search for movie shows. Returns available shows matching filters (movie name, price cap, time, city).",
        "parameters": {
            "type": "object",
            "properties": {
                "movie": {"type": "string", "description": "Movie name to search for"},
                "price_cap": {"type": "number", "description": "Maximum ticket price in INR"},
                "after_time": {"type": "string", "description": "Earliest show time (e.g., '21:00')"},
                "city": {"type": "string", "description": "City filter"},
            },
            "required": ["movie"],
        },
    },
    {
        "name": "search_trains",
        "description": "Search for trains between two cities. Returns available trains with classes and prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_city": {"type": "string", "description": "Departure city"},
                "to_city": {"type": "string", "description": "Destination city"},
                "budget": {"type": "number", "description": "Maximum ticket price in INR"},
                "preferred_class": {"type": "string", "description": "Preferred class: SL, 3A, 2A, 1A, CC, EC"},
            },
            "required": ["from_city", "to_city"],
        },
    },
    {
        "name": "compare_grocery_prices",
        "description": "Compare grocery prices across Blinkit, Zepto, and BigBasket. Returns price comparison matrix with cheapest split.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "qty": {"type": "string"},
                        },
                    },
                    "description": "List of items with quantities to compare",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "present_selection",
        "description": "Present a selection of options to the user for them to choose from. Used for movie show times, train classes, etc. The agent pauses until the user selects an option.",
        "parameters": {
            "type": "object",
            "properties": {
                "selection_type": {"type": "string", "description": "Type: movie_show, train_class, etc."},
                "prompt": {"type": "string", "description": "Prompt text to show the user"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "option_id": {"type": "string"},
                            "label": {"type": "string"},
                            "detail": {"type": "string"},
                            "price": {"type": "number"},
                        },
                    },
                    "description": "List of options for user to choose from",
                },
            },
            "required": ["selection_type", "prompt", "options"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------

def dispatch_tool(
    tool_name: str,
    args: dict,
    context: dict | None = None,
) -> dict:
    """
    Execute a tool and return the result.
    Context contains token_id, user_id, session_id etc.
    """
    context = context or {}
    token_id = context.get("token_id")
    user_id = context.get("user_id")
    session_id = context.get("session_id")

    try:
        if tool_name == "check_balance":
            uid = args.get("user_id", user_id)
            result = get_user_balance(uid)
            append_audit(
                token_id=token_id, action_type="BALANCE_CHECKED",
                actor="orchestrator", outcome="success",
                payload={"user_id": uid, "balance": result.get("balance_inr")},
            )
            return result

        elif tool_name == "search_merchants":
            result = search_merchants(items=args.get("items", []))
            append_audit(
                token_id=token_id, action_type="MERCHANT_SEARCHED",
                actor="shopping_agent", outcome="success",
                payload={"items": args.get("items", []), "found": result.get("total_found", 0)},
            )
            return result

        elif tool_name == "prepare_order":
            result = prepare_order(
                merchant_id=args["merchant_id"],
                items=args.get("items", []),
            )
            append_audit(
                token_id=token_id, action_type="ORDER_PREPARED",
                actor="shopping_agent", outcome="success",
                payload={"order_id": result.get("order_id"), "total": result.get("total_inr")},
            )
            return result

        elif tool_name == "request_payment":
            return _handle_payment(args, context)

        # --- V2 Tools ---
        elif tool_name == "search_recharge_plans":
            result = find_best_recharge_plan(
                operator=args.get("operator", ""),
                budget=args.get("budget", 500),
                days=args.get("days", 28),
                phone_number=args.get("phone_number", ""),
            )
            append_audit(
                token_id=token_id, action_type="RECHARGE_PLANS_SEARCHED",
                actor="recharge_agent", outcome="success",
                payload={"operator": args.get("operator"), "found": result.get("total_found", 0)},
            )
            return result

        elif tool_name == "search_movie_shows":
            result = search_movie_shows(
                movie=args.get("movie", ""),
                price_cap=args.get("price_cap", 500),
                after_time=args.get("after_time"),
                city=args.get("city"),
            )
            append_audit(
                token_id=token_id, action_type="MOVIE_SHOWS_SEARCHED",
                actor="movie_agent", outcome="success",
                payload={"movie": args.get("movie"), "found": result.get("total_found", 0)},
            )
            return result

        elif tool_name == "search_trains":
            result = search_trains(
                from_city=args.get("from_city", ""),
                to_city=args.get("to_city", ""),
                budget=args.get("budget", 5000),
                preferred_class=args.get("preferred_class"),
            )
            append_audit(
                token_id=token_id, action_type="TRAINS_SEARCHED",
                actor="train_agent", outcome="success",
                payload={
                    "from": args.get("from_city"), "to": args.get("to_city"),
                    "found": result.get("total_found", 0),
                },
            )
            return result

        elif tool_name == "compare_grocery_prices":
            result = compare_grocery_prices_sync(args.get("items", []))
            append_audit(
                token_id=token_id, action_type="PRICES_COMPARED",
                actor="grocery_agent", outcome="success",
                payload={"items_compared": len(args.get("items", []))},
            )
            return result

        elif tool_name == "present_selection":
            # This tool pauses the agent loop — returns selection data
            result = {
                "status": "selection_required",
                "selection_type": args.get("selection_type", "unknown"),
                "prompt": args.get("prompt", "Please select an option:"),
                "options": args.get("options", []),
            }
            append_audit(
                token_id=token_id, action_type="SELECTION_PRESENTED",
                actor="orchestrator", outcome="pending",
                payload={"type": args.get("selection_type"), "options_count": len(args.get("options", []))},
            )
            return result

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except ScopeViolation as e:
        append_audit(
            token_id=token_id, action_type="SCOPE_VIOLATION",
            actor="scope_enforcer", outcome="rejected",
            payload={"layer": e.layer, "message": e.message, "tool": tool_name},
        )
        return {"error": f"Scope violation (Layer {e.layer}): {e.message}"}
    except Exception as e:
        append_audit(
            token_id=token_id, action_type="TOOL_ERROR",
            actor=tool_name, outcome="error",
            payload={"error": str(e)},
        )
        return {"error": str(e)}


def _handle_payment(args: dict, context: dict) -> dict:
    """Handle payment request with scope enforcement and HITL check."""
    token_id = args.get("token_id", context.get("token_id"))
    user_id = args.get("user_id", context.get("user_id"))
    merchant_id = args.get("merchant_id", "")
    amount = args.get("amount", 0)
    order_id = args.get("order_id", "")
    category = args.get("category", "general")
    line_items = args.get("line_items", [])
    hitl_mode = context.get("hitl_mode", "amount_hitl")

    # Scope enforcement
    token_data = enforce_scope(
        token_id=token_id, amount=amount,
        category=category, merchant_id=merchant_id,
        order_id=order_id,
    )

    # HITL check — autonomous mode skips HITL entirely
    if hitl_mode == "autonomous":
        needs_hitl = False
    else:
        needs_hitl = check_hitl_required(token_data, amount)

    if needs_hitl:
        hitl_result = create_hitl_order(
            token_id=token_id, order_id=order_id,
            merchant_id=merchant_id, amount=amount,
            line_items=line_items,
        )
        append_audit(
            token_id=token_id, action_type="HITL_REQUIRED",
            actor="scope_enforcer", outcome="pending",
            amount=amount,
            payload={"order_id": order_id, "hitl_token": hitl_result.get("hitl_token")},
        )
        return hitl_result

    # Auto-approve — execute payment directly
    result = execute_payment(
        user_id=user_id, merchant_id=merchant_id,
        amount=amount, order_id=order_id,
        token_id=token_id, category=category,
    )

    append_audit(
        token_id=token_id, action_type="PAYMENT_EXECUTED",
        actor="payment_agent", outcome="success",
        amount=amount,
        payload={"order_id": order_id, "tx_id": result.get("tx_id"), "auto_approved": True},
    )

    result["auto_approved"] = True
    return result
