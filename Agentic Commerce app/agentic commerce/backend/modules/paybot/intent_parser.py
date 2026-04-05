"""
ArthSetu PayBot — Intent Parser V2
Uses Google Gemini API to parse natural language purchase intents into structured JSON.
Adds task_type + hitl_mode classification, multi-domain support, and pre-parsed fallbacks.
"""

import json
import os
import re

from google import genai
from google.genai import types

from backend.modules.paybot.task_classifier import classify_task, get_task_description

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Pre-parsed fallback intents for demo safety (V2)
# ---------------------------------------------------------------------------

PRE_PARSED_INTENTS = {
    "recharge my jio": {
        "items": [{"name": "Jio Recharge", "qty": 1, "category": "telecom"}],
        "budget_cap": 300.0,
        "categories": ["telecom"],
        "time_validity_hours": 2.0,
        "task_type": "phone_recharge",
        "hitl_mode": "autonomous",
    },
    "book inception tickets": {
        "items": [{"name": "Inception Movie Ticket", "qty": 1, "category": "entertainment"}],
        "budget_cap": 400.0,
        "categories": ["entertainment"],
        "time_validity_hours": 2.0,
        "task_type": "movie_tickets",
        "hitl_mode": "selection_hitl",
        "movie": "inception",
        "after_time": "21:00",
    },
    "order atta milk cheapest": {
        "items": [
            {"name": "Atta (Wheat Flour)", "qty": 2, "category": "grocery"},
            {"name": "Milk (Full Cream)", "qty": 1, "category": "grocery"},
        ],
        "budget_cap": 300.0,
        "categories": ["grocery"],
        "time_validity_hours": 2.0,
        "task_type": "grocery_cheapest",
        "hitl_mode": "amount_hitl",
    },
    "train delhi mumbai": {
        "items": [{"name": "Train Ticket Delhi-Mumbai", "qty": 1, "category": "travel"}],
        "budget_cap": 2000.0,
        "categories": ["travel"],
        "time_validity_hours": 2.0,
        "task_type": "train_tickets",
        "hitl_mode": "selection_hitl",
        "from_city": "delhi",
        "to_city": "mumbai",
    },
    "buy atta milk under": {
        "items": [
            {"name": "Atta (Wheat Flour)", "qty": 2, "category": "grocery"},
            {"name": "Milk (Full Cream)", "qty": 1, "category": "grocery"},
        ],
        "budget_cap": 500.0,
        "categories": ["grocery"],
        "time_validity_hours": 2.0,
        "task_type": "grocery",
        "hitl_mode": "amount_hitl",
    },
}

# System prompt for intent parsing (V2 — adds domain awareness)
INTENT_PARSER_SYSTEM_PROMPT = """You are an intent parser for a payment agent called PayBot, part of the ArthSetu platform for Indian SMB commerce.

Supported domains:
1. GROCERY — atta, milk, rice, dal, etc. If user says "cheapest" or "compare prices", set task_type to "grocery_cheapest"
2. TELECOM — Jio, Airtel, BSNL recharges. Set task_type to "phone_recharge"
3. MOVIES — movie tickets, BookMyShow. Set task_type to "movie_tickets". Extract movie name, price_cap, after_time
4. TRAINS — train tickets, IRCTC. Set task_type to "train_tickets". Extract from_city, to_city, preferred_class
5. GENERAL — anything else

Extract from the user's message:
- items: list of items to purchase, each with name, quantity (qty), and category
- budget_cap: maximum budget in INR. If not stated, estimate and add 20% buffer
- categories: list of categories
- time_validity_hours: default 2
- task_type: one of [phone_recharge, movie_tickets, train_tickets, grocery_cheapest, grocery, general_purchase]
- hitl_mode: one of [autonomous, amount_hitl, selection_hitl]
  - phone_recharge → autonomous
  - movie_tickets → selection_hitl
  - train_tickets → selection_hitl
  - grocery_cheapest → amount_hitl
  - grocery → amount_hitl
- Domain-specific fields (if applicable):
  - movie: movie name (for movie_tickets)
  - after_time: earliest show time like "21:00" (for movie_tickets)
  - from_city: departure city (for train_tickets)
  - to_city: destination city (for train_tickets)
  - preferred_class: SL/3A/2A/1A (for train_tickets)
  - operator: jio/airtel/bsnl (for phone_recharge)

Return ONLY valid JSON. No explanation. No markdown."""


def parse_intent(user_input: str) -> dict:
    """
    Parse natural language input into structured purchase intent with task classification.
    Falls back to pre-parsed intents, then mock parsing.
    """
    # 1. Try pre-parsed fallback first (for demo safety)
    fallback = _try_fallback(user_input)
    if fallback:
        fallback["raw_input"] = user_input
        # Override budget if specified in input
        budget_override = _extract_budget(user_input)
        if budget_override:
            fallback["budget_cap"] = budget_override
        # Ensure task_description is always present
        if "task_description" not in fallback:
            fallback["task_description"] = get_task_description(
                fallback.get("task_type", "general_purchase"),
                fallback.get("hitl_mode", "amount_hitl"),
            )
        return fallback

    # 2. Try Gemini API
    if GEMINI_API_KEY:
        result = _gemini_parse(user_input)
        if result:
            return result

    # 3. Fall back to mock parsing
    return _mock_parse(user_input)


def _try_fallback(user_input: str) -> dict | None:
    """Try to match against pre-parsed fallback intents."""
    input_lower = user_input.lower()
    best_match = None
    best_score = 0

    for key, intent in PRE_PARSED_INTENTS.items():
        words = key.split()
        matched = sum(1 for w in words if w in input_lower)
        score = matched / len(words) if words else 0
        if score > best_score and score >= 0.6:  # 60% keyword match threshold
            best_score = score
            best_match = intent.copy()

    return best_match


def _gemini_parse(user_input: str) -> dict | None:
    """Parse using Gemini API."""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=INTENT_PARSER_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1000,
            ),
        )

        result_text = response.text.strip()

        # Clean up markdown code fences
        if result_text.startswith("```"):
            result_text = re.sub(r"^```(?:json)?\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)

        parsed = json.loads(result_text)
        return _validate_intent(parsed, user_input)

    except json.JSONDecodeError as e:
        print(f"[IntentParser] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[IntentParser] Gemini API error: {e}")
        return None


def _validate_intent(parsed: dict, original_input: str) -> dict:
    """Validate and normalize the parsed intent, adding task classification."""
    items = parsed.get("items", [])
    if not items:
        items = [{"name": "unknown item", "qty": 1, "category": "general"}]

    for item in items:
        item.setdefault("name", "unknown")
        item.setdefault("qty", 1)
        item.setdefault("category", "general")

    categories = list(set(item["category"] for item in items))
    budget_cap = parsed.get("budget_cap", 500)
    time_validity_hours = parsed.get("time_validity_hours", 2)

    # Task classification (use parsed if available, else classify)
    task_type = parsed.get("task_type")
    hitl_mode = parsed.get("hitl_mode")

    if not task_type or not hitl_mode:
        task_type, hitl_mode = classify_task(parsed, original_input)

    result = {
        "items": items,
        "budget_cap": float(budget_cap),
        "categories": categories,
        "time_validity_hours": float(time_validity_hours),
        "raw_input": original_input,
        "task_type": task_type,
        "hitl_mode": hitl_mode,
        "task_description": get_task_description(task_type, hitl_mode),
    }

    # Pass through domain-specific fields
    for field in ["movie", "after_time", "from_city", "to_city", "preferred_class", "operator", "phone_number"]:
        if field in parsed:
            result[field] = parsed[field]

    return result


def _mock_parse(user_input: str) -> dict:
    """
    Enhanced mock parser for V2 — handles all 5 task domains.
    """
    input_lower = user_input.lower()

    items = []
    categories = set()
    task_type = None
    hitl_mode = None
    extra_fields = {}

    # --- Phone Recharge ---
    if any(kw in input_lower for kw in ["recharge", "prepaid", "data pack", "top up", "topup"]):
        operator = "jio"
        if "airtel" in input_lower:
            operator = "airtel"
        elif "bsnl" in input_lower:
            operator = "bsnl"
        elif "vi" in input_lower or "vodafone" in input_lower:
            operator = "vi"
        items.append({"name": f"{operator.capitalize()} Recharge", "qty": 1, "category": "telecom"})
        categories.add("telecom")
        task_type = "phone_recharge"
        hitl_mode = "autonomous"
        extra_fields["operator"] = operator

    # --- Movie Tickets ---
    elif any(kw in input_lower for kw in ["movie", "ticket", "cinema", "film", "show",
                                           "inception", "pushpa", "stree", "12th fail",
                                           "pvr", "inox", "cinepolis", "bookmyshow"]):
        # Extract movie name
        movie = "inception"  # default
        for m in ["inception", "pushpa", "stree", "12th fail"]:
            if m in input_lower:
                movie = m
                break
        items.append({"name": f"{movie.title()} Movie Ticket", "qty": 1, "category": "entertainment"})
        categories.add("entertainment")
        task_type = "movie_tickets"
        hitl_mode = "selection_hitl"
        extra_fields["movie"] = movie

        # Extract time constraint
        time_match = re.search(r'after\s+(\d{1,2})\s*(?:pm|PM)', input_lower)
        if time_match:
            hour = int(time_match.group(1))
            if hour < 12:
                hour += 12
            extra_fields["after_time"] = f"{hour:02d}:00"
        time_match2 = re.search(r'after\s+(\d{1,2}:\d{2})', input_lower)
        if time_match2:
            extra_fields["after_time"] = time_match2.group(1)

    # --- Train Tickets ---
    elif any(kw in input_lower for kw in ["train", "railway", "irctc", "rajdhani", "shatabdi", "express",
                                           "sleeper", "3ac", "2ac", "1ac", "berth"]):
        # Extract cities
        city_pairs = [
            ("delhi", "mumbai"), ("mumbai", "delhi"),
            ("delhi", "jaipur"), ("jaipur", "delhi"),
            ("mumbai", "goa"), ("goa", "mumbai"),
        ]
        from_city, to_city = "delhi", "mumbai"  # default
        for fc, tc in city_pairs:
            if fc in input_lower and tc in input_lower:
                from_city, to_city = fc, tc
                break

        items.append({"name": f"Train Ticket {from_city.title()}-{to_city.title()}", "qty": 1, "category": "travel"})
        categories.add("travel")
        task_type = "train_tickets"
        hitl_mode = "selection_hitl"
        extra_fields["from_city"] = from_city
        extra_fields["to_city"] = to_city

    # --- Grocery (cheapest / comparison) ---
    elif any(kw in input_lower for kw in ["cheapest", "compare", "comparison", "lowest price",
                                           "blinkit", "zepto", "bigbasket", "wherever is cheapest"]):
        _parse_grocery_items(input_lower, items, categories)
        task_type = "grocery_cheapest"
        hitl_mode = "amount_hitl"

    # --- Standard grocery ---
    else:
        jio_match = "jio" in input_lower
        airtel_match = "airtel" in input_lower
        if jio_match or airtel_match:
            op = "Jio" if jio_match else "Airtel"
            items.append({"name": f"{op} Recharge", "qty": 1, "category": "telecom"})
            categories.add("telecom")

        _parse_grocery_items(input_lower, items, categories)

        if not items:
            items = [{"name": "General Purchase", "qty": 1, "category": "general"}]
            categories.add("general")

        if not task_type:
            task_type = "grocery" if "grocery" in categories else "general_purchase"
            hitl_mode = "amount_hitl"

    # Task classification if not set
    if not task_type or not hitl_mode:
        result_so_far = {"items": items, "categories": list(categories)}
        task_type, hitl_mode = classify_task(result_so_far, user_input)

    # Extract budget
    budget_cap = _extract_budget(user_input) or 500

    result = {
        "items": items,
        "budget_cap": float(budget_cap),
        "categories": list(categories),
        "time_validity_hours": 2.0,
        "raw_input": user_input,
        "task_type": task_type,
        "hitl_mode": hitl_mode,
        "task_description": get_task_description(task_type, hitl_mode),
    }
    result.update(extra_fields)
    return result


def _parse_grocery_items(input_lower: str, items: list, categories: set):
    """Parse grocery items from input text."""
    grocery_keywords = {
        "atta": ("Atta (Wheat Flour)", "grocery"),
        "milk": ("Milk (Full Cream)", "grocery"),
        "rice": ("Rice (Basmati)", "grocery"),
        "dal": ("Dal (Toor)", "grocery"),
        "sugar": ("Sugar", "grocery"),
        "oil": ("Sunflower Oil", "grocery"),
        "bread": ("Bread", "grocery"),
        "eggs": ("Eggs (Pack of 6)", "grocery"),
        "ghee": ("Ghee (Amul)", "grocery"),
        "flour": ("Atta (Wheat Flour)", "grocery"),
        "earphone": ("Earphones (boAt Bassheads)", "electronics"),
        "headphone": ("Headphones", "electronics"),
        "usb": ("USB Cable (Type-C)", "electronics"),
        "cable": ("USB Cable (Type-C)", "electronics"),
        "paracetamol": ("Paracetamol (Crocin)", "health"),
        "medicine": ("Paracetamol (Crocin)", "health"),
        "barfi": ("Barfi (Kaju)", "food"),
        "sweets": ("Barfi (Kaju)", "food"),
        "t-shirt": ("T-Shirt (Cotton)", "clothing"),
        "tshirt": ("T-Shirt (Cotton)", "clothing"),
    }

    for keyword, (name, category) in grocery_keywords.items():
        if keyword in input_lower:
            # Extract quantity
            qty = 1
            qty_match = re.search(rf'(\d+)\s*(?:kg|l|pcs|packet|pack)?\s*{keyword}', input_lower)
            if not qty_match:
                qty_match = re.search(rf'{keyword}\s*(?:x\s*)?(\d+)', input_lower)
            if qty_match:
                qty = int(qty_match.group(1))

            items.append({"name": name, "qty": qty, "category": category})
            categories.add(category)


def _extract_budget(user_input: str) -> float | None:
    """Extract budget from user input."""
    input_lower = user_input.lower()
    budget_match = re.search(r'(?:under|below|budget|max|upto|up to)\s*(?:rs\.?|₹|inr)?\s*(\d+)', input_lower)
    if budget_match:
        return float(budget_match.group(1))
    return None
