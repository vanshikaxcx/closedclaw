"""
ArthSetu PayBot — Domain Handlers
Routes search requests to domain-specific crawlers/catalogs.
Each handler returns structured options for the orchestrator.
"""

import asyncio
from backend.crawlers.grocery_crawler import crawl_grocery_prices, compare_grocery_prices_sync
from backend.crawlers.movie_crawler import search_movie_shows
from backend.crawlers.train_crawler import search_trains
from backend.crawlers.recharge_crawler import find_best_recharge_plan, detect_operator


def handle_grocery_search(items: list[dict]) -> dict:
    """Handle grocery search with price comparison across platforms."""
    return compare_grocery_prices_sync(items)


def handle_grocery_price_comparison(item: str, qty: str = "") -> dict:
    """Handle single item price comparison."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, crawl_grocery_prices(item, qty)).result()
            return result
        else:
            return asyncio.run(crawl_grocery_prices(item, qty))
    except RuntimeError:
        return asyncio.run(crawl_grocery_prices(item, qty))


def handle_movie_search(
    movie: str,
    price_cap: float = 500,
    after_time: str | None = None,
    city: str | None = None,
) -> dict:
    """Handle movie show search."""
    return search_movie_shows(movie, price_cap, after_time, city)


def handle_train_search(
    from_city: str,
    to_city: str,
    budget: float = 5000,
    preferred_class: str | None = None,
) -> dict:
    """Handle train search."""
    return search_trains(from_city, to_city, budget, preferred_class)


def handle_recharge_search(
    operator: str = "",
    budget: float = 500,
    days: int = 28,
    phone_number: str = "",
) -> dict:
    """Handle recharge plan search."""
    return find_best_recharge_plan(operator, budget, days, phone_number or None)


def search_options(task_type: str, params: dict) -> dict:
    """
    Universal search router — routes to domain-specific handlers.

    Args:
        task_type: phone_recharge, movie_tickets, train_tickets, grocery_cheapest, grocery
        params: Domain-specific search parameters

    Returns: Domain-specific search results
    """
    if task_type == "phone_recharge":
        return handle_recharge_search(
            operator=params.get("operator", ""),
            budget=params.get("budget", 500),
            days=params.get("days", 28),
            phone_number=params.get("phone_number", ""),
        )

    elif task_type == "movie_tickets":
        return handle_movie_search(
            movie=params.get("movie", ""),
            price_cap=params.get("price_cap", 500),
            after_time=params.get("after_time"),
            city=params.get("city"),
        )

    elif task_type == "train_tickets":
        return handle_train_search(
            from_city=params.get("from", params.get("from_city", "")),
            to_city=params.get("to", params.get("to_city", "")),
            budget=params.get("budget", 5000),
            preferred_class=params.get("class"),
        )

    elif task_type in ("grocery_cheapest", "grocery"):
        items = params.get("items", [])
        if isinstance(items, list) and len(items) > 0:
            return handle_grocery_search(items)
        item = params.get("item", "")
        if item:
            return handle_grocery_price_comparison(item, params.get("qty", ""))
        return {"error": "No items specified for grocery search"}

    return {"error": f"Unknown task type: {task_type}"}
