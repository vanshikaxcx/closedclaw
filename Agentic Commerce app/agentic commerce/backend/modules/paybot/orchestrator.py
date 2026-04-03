"""
ArthSetu PayBot — Orchestrator Agent V2
Gemini-based orchestrator with:
- Session-based execution (agent_sessions table)
- Dynamic system prompts based on hitl_mode
- Selection pause/resume (selection_hitl mode)
- Multi-domain tool routing
- Step-by-step reasoning narration
"""

import json
import os
import uuid
import time
from datetime import datetime, timezone

from backend.modules.paybot.tools import dispatch_tool, TOOL_DEFINITIONS
from backend.modules.paybot.task_classifier import get_task_description
from backend.db import (
    get_connection, create_session, get_session,
    update_session, create_pending_selection, get_pending_selection,
    resolve_selection,
)
from backend.audit import append_audit

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# Dynamic system prompts based on HITL mode
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "autonomous": """You are PayBot, an autonomous payment agent for ArthSetu.
The user's task can be executed without human approval. Find the best option and execute payment directly.

FLOW:
1. check_balance — verify funds
2. Search for the best option (use search_recharge_plans, search_merchants, etc.)
3. Pick the BEST option (cheapest matching all criteria)
4. Execute request_payment directly — no need for user approval

RULES:
- Always check balance first
- Pick the single best matching option
- Execute payment autonomously
- Provide clear reasoning in your responses""",

    "amount_hitl": """You are PayBot, a payment agent for ArthSetu.
This task requires human approval for payment above the threshold.

FLOW:
1. check_balance — verify funds
2. Search for items/merchants (search_merchants, compare_grocery_prices)  
3. Prepare order (prepare_order)
4. Execute request_payment — system will auto-trigger HITL if needed

RULES:
- Always check balance first
- Find the best prices
- Prepare a clear order summary
- The system handles HITL triggering automatically""",

    "selection_hitl": """You are PayBot, a payment agent for ArthSetu.
This task requires the user to choose from options before you can proceed.

FLOW:
1. check_balance — verify funds
2. Search for options (search_movie_shows, search_trains)
3. Call present_selection with the options — the agent will PAUSE here
4. After user selects, prepare order and execute request_payment

RULES:
- Always check balance first
- Search for all matching options
- Present options using present_selection tool — ALWAYS use this for movies/trains
- Wait for user selection before proceeding to payment
- After selection, prepare order and request payment""",
}


def get_system_prompt(hitl_mode: str, task_type: str) -> str:
    """Build the system prompt for the orchestrator based on HITL mode."""
    base = SYSTEM_PROMPTS.get(hitl_mode, SYSTEM_PROMPTS["amount_hitl"])
    return f"{base}\n\nTask type: {task_type}\nHITL mode: {hitl_mode}"


# ---------------------------------------------------------------------------
# Agent session runner
# ---------------------------------------------------------------------------

def start_agent_session(
    token_id: str,
    user_id: str,
    intent: dict,
    user_input: str,
) -> dict:
    """
    Start a new agent session and run the agent loop.
    Returns session data with steps and result.
    """
    task_type = intent.get("task_type", "general_purchase")
    hitl_mode = intent.get("hitl_mode", "amount_hitl")

    session_id = f"sess_{uuid.uuid4().hex[:16]}"

    session = {
        "session_id": session_id,
        "token_id": token_id,
        "user_id": user_id,
        "task_type": task_type,
        "hitl_mode": hitl_mode,
        "phase": "running",
        "steps": [],
        "user_input": user_input,
        "intent": intent,
    }

    # Save to DB
    conn = get_connection()
    create_session(conn, session)
    conn.close()

    append_audit(
        token_id=token_id, action_type="SESSION_STARTED",
        actor="orchestrator", outcome="success",
        payload={"session_id": session_id, "task_type": task_type, "hitl_mode": hitl_mode},
    )

    # Run the agent loop
    result = _run_agent_loop(session)
    return result


def resume_agent_session(session_id: str, selected_option_id: str) -> dict:
    """
    Resume an agent session after user selection (selection_hitl mode).
    """
    conn = get_connection()
    session = get_session(conn, session_id)
    conn.close()

    if not session:
        return {"error": f"Session {session_id} not found"}

    if session["phase"] != "selection_required":
        return {"error": f"Session is in phase '{session['phase']}', not 'selection_required'"}

    # Resolve the pending selection
    conn = get_connection()
    pending = get_pending_selection(conn, session_id)
    if pending:
        resolve_selection(conn, pending["selection_id"], selected_option_id)
    conn.close()

    # Find the selected option details
    selected_option = None
    if pending:
        for opt in pending["options"]:
            if opt.get("option_id") == selected_option_id:
                selected_option = opt
                break

    if not selected_option and pending:
        # Try matching by index
        try:
            idx = int(selected_option_id)
            if 0 <= idx < len(pending["options"]):
                selected_option = pending["options"][idx]
        except (ValueError, IndexError):
            pass

    # Update session
    conn = get_connection()
    steps = session["steps"]
    steps.append({
        "tool": "user_selection",
        "narration": f"User selected: {selected_option.get('label', selected_option_id) if selected_option else selected_option_id}",
        "result": {"selected": selected_option or {"option_id": selected_option_id}},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    update_session(conn, session_id, steps=steps, phase="running",
                   selection_data={"selected_option": selected_option or {"option_id": selected_option_id}})
    conn.close()

    append_audit(
        token_id=session["token_id"], action_type="USER_SELECTION_MADE",
        actor="user", outcome="success",
        payload={"session_id": session_id, "option_id": selected_option_id},
    )

    # Continue the agent loop with selection context
    session["steps"] = steps
    session["phase"] = "running"
    session["selection_data"] = {"selected_option": selected_option or {"option_id": selected_option_id}}

    result = _run_agent_loop_after_selection(session)
    return result


def get_session_status(session_id: str) -> dict:
    """Get the current status of an agent session."""
    conn = get_connection()
    session = get_session(conn, session_id)

    if not session:
        conn.close()
        return {"error": f"Session {session_id} not found"}

    # Check for pending selection
    selection = get_pending_selection(conn, session_id)
    conn.close()

    result = {
        "session_id": session_id,
        "phase": session["phase"],
        "task_type": session["task_type"],
        "hitl_mode": session["hitl_mode"],
        "steps": session["steps"],
    }

    if selection:
        result["selection"] = {
            "selection_type": selection["selection_type"],
            "prompt": selection["prompt"],
            "options": selection["options"],
        }

    if session.get("order_data"):
        result["order"] = session["order_data"]

    if session.get("result"):
        result["result"] = session["result"]

    return result


# ---------------------------------------------------------------------------
# Mock agent loop (no API key)
# ---------------------------------------------------------------------------

def _run_agent_loop(session: dict) -> dict:
    """Run the agent loop — uses Gemini if available, mock otherwise."""
    if GEMINI_API_KEY:
        return _run_gemini_loop(session)
    return _run_mock_loop(session)


def _run_mock_loop(session: dict) -> dict:
    """Mock agent loop for when Gemini API is unavailable."""
    context = {
        "token_id": session["token_id"],
        "user_id": session["user_id"],
        "session_id": session["session_id"],
        "hitl_mode": session["hitl_mode"],
    }

    steps = session.get("steps", [])
    intent = session["intent"]
    task_type = session["task_type"]
    hitl_mode = session["hitl_mode"]

    # Step 1: Check balance
    balance = dispatch_tool("check_balance", {"user_id": session["user_id"]}, context)
    steps.append({
        "tool": "check_balance",
        "narration": f"Checking wallet balance... Rs.{balance.get('balance_inr', 0)} available",
        "result": balance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Step 2: Domain-specific search
    if task_type == "phone_recharge":
        return _mock_recharge_flow(session, steps, context, intent)
    elif task_type == "movie_tickets":
        return _mock_movie_flow(session, steps, context, intent)
    elif task_type == "train_tickets":
        return _mock_train_flow(session, steps, context, intent)
    elif task_type == "grocery_cheapest":
        return _mock_grocery_comparison_flow(session, steps, context, intent)
    else:
        return _mock_grocery_flow(session, steps, context, intent)


def _mock_recharge_flow(session, steps, context, intent):
    """Mock recharge flow - autonomous."""
    operator = intent.get("operator", "jio")
    budget = intent.get("budget_cap", 300)

    # Search plans
    plans = dispatch_tool("search_recharge_plans", {
        "operator": operator, "budget": budget, "days": 28,
    }, context)

    best = plans.get("best_plan")
    steps.append({
        "tool": "search_recharge_plans",
        "narration": f"Finding best {operator.capitalize()} plan under Rs.{budget}... "
                     f"{'Found: ' + best['plan_id'] + ' Rs.' + str(best['price']) if best else 'No plans found'}",
        "result": plans,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if not best:
        return _finalize_session(session, steps, "completed", {"status": "no_plans_found"})

    # Auto-execute payment
    payment = dispatch_tool("request_payment", {
        "user_id": session["user_id"],
        "merchant_id": f"{operator}_recharge",
        "amount": best["price"],
        "order_id": f"ord_{uuid.uuid4().hex[:12]}",
        "token_id": session["token_id"],
        "category": "telecom",
    }, context)

    steps.append({
        "tool": "request_payment",
        "narration": f"Executing payment autonomously — Rs.{best['price']} for {best['plan_id']}",
        "result": payment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return _finalize_session(session, steps, "completed", payment)


def _mock_movie_flow(session, steps, context, intent):
    """Mock movie flow - selection_hitl."""
    movie = intent.get("movie", "inception")
    price_cap = intent.get("budget_cap", 400)
    after_time = intent.get("after_time")

    # Search shows
    shows = dispatch_tool("search_movie_shows", {
        "movie": movie, "price_cap": price_cap, "after_time": after_time,
    }, context)

    steps.append({
        "tool": "search_movie_shows",
        "narration": f"Searching for {movie.title()} shows" +
                     (f" after {after_time}" if after_time else "") +
                     f" under Rs.{price_cap}... Found {shows.get('total_found', 0)} shows",
        "result": shows,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if not shows.get("shows"):
        return _finalize_session(session, steps, "completed", {"status": "no_shows_found"})

    # Present selection
    options = []
    for show in shows["shows"][:4]:
        options.append({
            "option_id": show["show_id"],
            "label": f"{show['theatre']} · {show['format']}",
            "detail": f"{show['time']} · {show.get('seats_available', 0)} seats available",
            "price": show["price"],
        })

    selection_result = dispatch_tool("present_selection", {
        "selection_type": "movie_show",
        "prompt": f"Select a show for {shows.get('movie', movie)}:",
        "options": options,
    }, context)

    steps.append({
        "tool": "present_selection",
        "narration": f"Presenting {len(options)} show options for user selection...",
        "result": selection_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Save pending selection to DB
    _save_selection_and_pause(session, steps, selection_result, options)

    return {
        "session_id": session["session_id"],
        "status": "selection_required",
        "phase": "selection_required",
        "steps": steps,
        "selection": {
            "selection_type": "movie_show",
            "prompt": f"Select a show for {shows.get('movie', movie)}:",
            "options": options,
        },
    }


def _mock_train_flow(session, steps, context, intent):
    """Mock train flow - selection_hitl."""
    from_city = intent.get("from_city", "delhi")
    to_city = intent.get("to_city", "mumbai")
    budget = intent.get("budget_cap", 2000)

    # Search trains
    trains = dispatch_tool("search_trains", {
        "from_city": from_city, "to_city": to_city, "budget": budget,
    }, context)

    steps.append({
        "tool": "search_trains",
        "narration": f"Searching trains {from_city.title()} → {to_city.title()} under Rs.{budget}... "
                     f"Found {trains.get('total_found', 0)} options",
        "result": trains,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if not trains.get("options"):
        return _finalize_session(session, steps, "completed", {"status": "no_trains_found"})

    # Present selection
    options = []
    for opt in trains["options"][:4]:
        options.append({
            "option_id": opt["option_id"],
            "label": opt["label"],
            "detail": opt["detail"],
            "price": opt["price"],
        })

    selection_result = dispatch_tool("present_selection", {
        "selection_type": "train_class",
        "prompt": f"Select a train for {trains.get('route', f'{from_city} → {to_city}')}:",
        "options": options,
    }, context)

    steps.append({
        "tool": "present_selection",
        "narration": f"Presenting {len(options)} train options for user selection...",
        "result": selection_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    _save_selection_and_pause(session, steps, selection_result, options)

    return {
        "session_id": session["session_id"],
        "status": "selection_required",
        "phase": "selection_required",
        "steps": steps,
        "selection": {
            "selection_type": "train_class",
            "prompt": f"Select a train for {trains.get('route', f'{from_city} → {to_city}')}:",
            "options": options,
        },
    }


def _mock_grocery_comparison_flow(session, steps, context, intent):
    """Mock grocery comparison flow."""
    items = intent.get("items", [{"name": "atta", "qty": "2 kg"}, {"name": "milk", "qty": "1 L"}])
    search_items = [{"name": i.get("name", ""), "qty": str(i.get("qty", "1"))} for i in items]

    comparison = dispatch_tool("compare_grocery_prices", {"items": search_items}, context)

    steps.append({
        "tool": "compare_grocery_prices",
        "narration": f"Comparing prices across Blinkit, Zepto, BigBasket for {len(items)} items...",
        "result": comparison,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Build order from cheapest split
    total = comparison.get("total_cheapest", 0)
    if total > 0:
        order_id = f"ord_{uuid.uuid4().hex[:12]}"

        # Request payment for the total
        payment = dispatch_tool("request_payment", {
            "user_id": session["user_id"],
            "merchant_id": "cheapest_split",
            "amount": total,
            "order_id": order_id,
            "token_id": session["token_id"],
            "category": "grocery",
            "line_items": comparison.get("cheapest_split", []),
        }, context)

        steps.append({
            "tool": "request_payment",
            "narration": f"Total Rs.{total} from cheapest split — " +
                         ("requesting approval..." if payment.get("status") == "pending_approval"
                          else f"payment {'completed' if payment.get('status') == 'completed' else 'processed'}"),
            "result": payment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return _finalize_session(session, steps, "completed", payment)

    return _finalize_session(session, steps, "completed", {"status": "no_prices_found"})


def _mock_grocery_flow(session, steps, context, intent):
    """Mock standard grocery flow."""
    items = intent.get("items", [])
    item_names = [i.get("name", "") for i in items if i.get("category") in ("grocery", "general")]

    if not item_names:
        item_names = [i.get("name", "") for i in items]

    # Search merchants
    merchants = dispatch_tool("search_merchants", {"items": item_names}, context)
    steps.append({
        "tool": "search_merchants",
        "narration": f"Searching for merchants with {', '.join(item_names[:3])}... "
                     f"Found {merchants.get('total_found', 0)} merchants",
        "result": merchants,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if merchants.get("total_found", 0) == 0:
        return _finalize_session(session, steps, "completed", {"status": "no_merchants_found"})

    # Prepare order from first matching merchant
    merchant = merchants["merchants"][0]
    order_items = [{"name": i.get("name", ""), "qty": i.get("qty", 1)} for i in items]

    order = dispatch_tool("prepare_order", {
        "merchant_id": merchant["merchant_id"],
        "items": order_items,
    }, context)

    steps.append({
        "tool": "prepare_order",
        "narration": f"Order prepared from {merchant.get('name', merchant['merchant_id'])}: "
                     f"Rs.{order.get('total_inr', 0)}",
        "result": order,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if "error" in order:
        return _finalize_session(session, steps, "completed", order)

    # Request payment
    payment = dispatch_tool("request_payment", {
        "user_id": session["user_id"],
        "merchant_id": merchant["merchant_id"],
        "amount": order["total_inr"],
        "order_id": order["order_id"],
        "token_id": session["token_id"],
        "category": merchant.get("category", "grocery"),
        "line_items": order.get("line_items", []),
    }, context)

    steps.append({
        "tool": "request_payment",
        "narration": f"Payment Rs.{order['total_inr']} — " +
                     ("requesting approval..." if payment.get("status") == "pending_approval"
                      else f"{'completed' if payment.get('status') == 'completed' else 'processed'}"),
        "result": payment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return _finalize_session(session, steps, "completed", payment)


def _run_agent_loop_after_selection(session: dict) -> dict:
    """Continue agent loop after user makes a selection."""
    context = {
        "token_id": session["token_id"],
        "user_id": session["user_id"],
        "session_id": session["session_id"],
        "hitl_mode": session["hitl_mode"],
    }
    steps = session.get("steps", [])
    selected = session.get("selection_data", {}).get("selected_option", {})

    if not selected:
        return _finalize_session(session, steps, "completed", {"status": "no_selection_made"})

    # Build order from selection and execute payment
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    amount = selected.get("price", 0)
    label = selected.get("label", "Selected item")

    # Determine merchant/category from task type
    task_type = session["task_type"]
    if task_type == "movie_tickets":
        merchant_id = selected.get("option_id", "movie_booking")
        category = "entertainment"
    elif task_type == "train_tickets":
        merchant_id = selected.get("option_id", "train_booking")
        category = "travel"
    else:
        merchant_id = selected.get("option_id", "booking")
        category = "general"

    steps.append({
        "tool": "prepare_order",
        "narration": f"Order prepared: {label} · Rs.{amount}",
        "result": {"order_id": order_id, "label": label, "amount": amount},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Execute payment
    payment = dispatch_tool("request_payment", {
        "user_id": session["user_id"],
        "merchant_id": merchant_id,
        "amount": amount,
        "order_id": order_id,
        "token_id": session["token_id"],
        "category": category,
        "line_items": [{"name": label, "price": amount, "qty": 1}],
    }, context)

    narration = f"Payment Rs.{amount} for {label} — "
    if payment.get("status") == "pending_approval":
        narration += "requesting approval..."
    elif payment.get("status") == "completed":
        narration += "completed ✓"
    else:
        narration += payment.get("status", "processed")

    steps.append({
        "tool": "request_payment",
        "narration": narration,
        "result": payment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return _finalize_session(session, steps, "completed", payment)


# ---------------------------------------------------------------------------
# Gemini-based agent loop
# ---------------------------------------------------------------------------

def _run_gemini_loop(session: dict) -> dict:
    """Run agent loop using Gemini function calling."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        context = {
            "token_id": session["token_id"],
            "user_id": session["user_id"],
            "session_id": session["session_id"],
            "hitl_mode": session["hitl_mode"],
        }
        steps = session.get("steps", [])
        hitl_mode = session["hitl_mode"]
        task_type = session["task_type"]

        system_prompt = get_system_prompt(hitl_mode, task_type)

        # Build Gemini tool declarations
        gemini_tools = []
        for tool_def in TOOL_DEFINITIONS:
            params = tool_def.get("parameters", {})
            gemini_tools.append(types.Tool(
                function_declarations=[types.FunctionDeclaration(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=params,
                )],
            ))

        # Build the initial message with context
        user_msg = f"""User request: {session['user_input']}
User ID: {session['user_id']}
Token ID: {session['token_id']}
Task type: {task_type}
HITL mode: {hitl_mode}
Intent: {json.dumps(session['intent'])}"""

        messages = [types.Content(role="user", parts=[types.Part(text=user_msg)])]

        # Tool-calling loop (max 10 iterations)
        for iteration in range(10):
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    temperature=0.2,
                ),
            )

            # Check if model wants to call a function
            if response.candidates and response.candidates[0].content.parts:
                parts = response.candidates[0].content.parts
                has_function_call = any(hasattr(p, 'function_call') and p.function_call for p in parts)

                if has_function_call:
                    # Process each function call
                    messages.append(response.candidates[0].content)

                    function_responses = []
                    for part in parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}

                            # Execute tool
                            result = dispatch_tool(tool_name, tool_args, context)

                            steps.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "narration": f"Calling {tool_name}...",
                                "result": result,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })

                            # Check for selection required
                            if result.get("status") == "selection_required":
                                options = result.get("options", [])
                                _save_selection_and_pause(session, steps, result, options)

                                return {
                                    "session_id": session["session_id"],
                                    "status": "selection_required",
                                    "phase": "selection_required",
                                    "steps": steps,
                                    "selection": {
                                        "selection_type": result.get("selection_type"),
                                        "prompt": result.get("prompt"),
                                        "options": options,
                                    },
                                }

                            function_responses.append(types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_name,
                                    response={"result": json.dumps(result, default=str)},
                                ),
                            ))

                    messages.append(types.Content(
                        role="function",
                        parts=function_responses,
                    ))
                else:
                    # Model returned text — we're done
                    final_text = response.text if response.text else "Agent loop completed."
                    steps.append({
                        "tool": "final_response",
                        "narration": final_text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    break
            else:
                break

        # Determine final result
        last_payment = None
        for step in reversed(steps):
            result = step.get("result", {})
            if isinstance(result, dict) and result.get("status") in ("completed", "pending_approval"):
                last_payment = result
                break

        return _finalize_session(session, steps, "completed", last_payment or {"status": "completed", "steps_executed": len(steps)})

    except Exception as e:
        print(f"[Orchestrator] Gemini error, falling back to mock: {e}")
        return _run_mock_loop(session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_selection_and_pause(session, steps, selection_result, options):
    """Save pending selection to DB and pause session."""
    selection_id = f"sel_{uuid.uuid4().hex[:12]}"

    conn = get_connection()
    create_pending_selection(conn, {
        "selection_id": selection_id,
        "session_id": session["session_id"],
        "token_id": session["token_id"],
        "selection_type": selection_result.get("selection_type", "unknown"),
        "prompt": selection_result.get("prompt", "Select an option:"),
        "options": options,
    })
    update_session(conn, session["session_id"],
                   phase="selection_required", steps=steps,
                   selection_data={"selection_id": selection_id, "options": options})
    conn.close()


def _finalize_session(session, steps, phase, result):
    """Finalize a session and update DB."""
    conn = get_connection()
    update_session(conn, session["session_id"],
                   phase=phase, steps=steps, result=result or {})
    conn.close()

    return {
        "session_id": session["session_id"],
        "status": phase,
        "phase": phase,
        "steps": steps,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Legacy V1 compatibility — run_agent_for_intent
# ---------------------------------------------------------------------------

def run_agent_for_intent(
    token_id: str,
    user_id: str,
    intent: dict,
    user_input: str,
) -> dict:
    """
    V1-compatible agent execution. Wraps the V2 session system.
    """
    result = start_agent_session(token_id, user_id, intent, user_input)

    return {
        "status": result.get("status", "completed"),
        "steps": result.get("steps", []),
        "result": result.get("result"),
        "session_id": result.get("session_id"),
    }
