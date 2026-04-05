"""
ArthSetu PayBot — Task Classifier
Enriches parsed intent with task_type and hitl_mode.
Determines how the agent should handle user interaction.
"""

# Task types and their HITL modes
TASK_HITL_MAP = {
    "phone_recharge": "autonomous",       # Single best answer → auto-execute
    "grocery": "amount_hitl",             # Standard grocery → approve if > threshold
    "grocery_cheapest": "amount_hitl",    # Price comparison → approve total
    "movie_tickets": "selection_hitl",    # User must choose show time
    "train_tickets": "selection_hitl",    # User must choose train + class
    "general_purchase": "amount_hitl",    # Fallback → standard HITL
}

# Keywords for task type detection
TASK_KEYWORDS = {
    "phone_recharge": [
        "recharge", "prepaid", "jio", "airtel", "bsnl", "vodafone", "vi",
        "mobile plan", "data pack", "validity", "top up", "topup",
    ],
    "movie_tickets": [
        "movie", "ticket", "film", "show", "cinema", "pvr", "inox", "cinepolis",
        "bookmyshow", "book my show", "imax", "3d",
        "inception", "pushpa", "stree", "12th fail",
    ],
    "train_tickets": [
        "train", "railway", "irctc", "rajdhani", "shatabdi", "express",
        "sleeper", "3ac", "2ac", "1ac", "coach", "berth", "tatkal",
        "platform", "station",
    ],
    "grocery_cheapest": [
        "cheapest", "cheapest price", "best price", "compare price", "compare",
        "lowest price", "price comparison", "blinkit", "zepto", "bigbasket",
        "wherever is cheapest",
    ],
    "grocery": [
        "grocery", "atta", "milk", "rice", "dal", "sugar", "oil", "bread",
        "eggs", "flour", "ghee", "spice", "vegetable", "fruit",
        "order", "buy", "purchase", "kilo", "litre", "packet",
    ],
}


def classify_task(intent: dict, user_input: str = "") -> tuple[str, str]:
    """
    Classify the task type and HITL mode from parsed intent and user input.

    Returns: (task_type, hitl_mode)
    """
    text = user_input.lower()
    items = intent.get("items", [])
    item_categories = [item.get("category", "").lower() for item in items if item.get("category")]
    intent_categories = [c.lower() for c in intent.get("categories", [])]
    all_categories = item_categories + intent_categories

    # Priority-ordered classification using TEXT-ONLY keyword matching
    # (item name matching is too ambiguous — 'ticket' appears in both movies and trains)

    # 1. Phone recharge (most specific)
    if _text_matches(text, "phone_recharge") or "telecom" in all_categories:
        return "phone_recharge", "autonomous"

    # 2. Train tickets — check before movies because 'train' is unambiguous
    if _text_matches(text, "train_tickets") or "travel" in all_categories or "transport" in all_categories:
        return "train_tickets", "selection_hitl"

    # 3. Movie tickets
    if _text_matches(text, "movie_tickets") or "entertainment" in all_categories or "movies" in all_categories:
        return "movie_tickets", "selection_hitl"

    # 4. Grocery with price comparison
    if _text_matches(text, "grocery_cheapest"):
        return "grocery_cheapest", "amount_hitl"

    # 5. Standard grocery
    if _text_matches(text, "grocery") or "grocery" in all_categories:
        return "grocery", "amount_hitl"

    # 6. Fallback
    return "general_purchase", "amount_hitl"


def _text_matches(text: str, task_type: str) -> bool:
    """Check if user input text matches keywords for a task type."""
    keywords = TASK_KEYWORDS.get(task_type, [])
    for kw in keywords:
        if kw in text:
            return True
    return False


def get_hitl_mode(task_type: str) -> str:
    """Get the HITL mode for a task type."""
    return TASK_HITL_MAP.get(task_type, "amount_hitl")


def get_task_description(task_type: str, hitl_mode: str) -> str:
    """Get a human-readable description of the task handling."""
    descriptions = {
        ("phone_recharge", "autonomous"): "Autonomous recharge — agent will find the best plan and execute without approval",
        ("movie_tickets", "selection_hitl"): "Movie booking — agent will search shows, you'll pick your preferred one",
        ("train_tickets", "selection_hitl"): "Train booking — agent will find trains, you'll select train and class",
        ("grocery_cheapest", "amount_hitl"): "Price comparison — agent will compare across Blinkit/Zepto/BigBasket, you approve total",
        ("grocery", "amount_hitl"): "Grocery order — agent will find items, you approve payment if above Rs.200",
        ("general_purchase", "amount_hitl"): "Purchase — agent will prepare order, you approve payment",
    }
    return descriptions.get((task_type, hitl_mode), f"Task: {task_type}, Mode: {hitl_mode}")
