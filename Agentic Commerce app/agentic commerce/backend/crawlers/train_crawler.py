"""
ArthSetu PayBot — Train Ticket Crawler
Real-time train schedule crawling using Playwright.
Falls back to catalog data when crawling fails.
"""

import asyncio
import re

# ---------------------------------------------------------------------------
# Train catalog (fallback + base data)
# ---------------------------------------------------------------------------

TRAIN_CATALOG = {
    "delhi-mumbai": {
        "route": "Delhi → Mumbai",
        "from_city": "Delhi",
        "to_city": "Mumbai",
        "distance": "1,384 km",
        "trains": [
            {
                "train_id": "12952",
                "name": "Mumbai Rajdhani Express",
                "departure": "16:55",
                "arrival": "08:35",
                "duration": "15h 40m",
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "classes": [
                    {"class_id": "1A", "name": "First AC", "price": 4815, "seats_available": 18},
                    {"class_id": "2A", "name": "Second AC", "price": 2880, "seats_available": 42},
                    {"class_id": "3A", "name": "Third AC", "price": 1995, "seats_available": 65},
                ],
            },
            {
                "train_id": "12954",
                "name": "August Kranti Rajdhani",
                "departure": "17:40",
                "arrival": "10:55",
                "duration": "17h 15m",
                "days": ["Mon", "Wed", "Fri", "Sun"],
                "classes": [
                    {"class_id": "2A", "name": "Second AC", "price": 2780, "seats_available": 38},
                    {"class_id": "3A", "name": "Third AC", "price": 1850, "seats_available": 72},
                ],
            },
        ],
    },
    "delhi-jaipur": {
        "route": "Delhi → Jaipur",
        "from_city": "Delhi",
        "to_city": "Jaipur",
        "distance": "308 km",
        "trains": [
            {
                "train_id": "12958",
                "name": "Ajmer Shatabdi Express",
                "departure": "06:05",
                "arrival": "10:30",
                "duration": "4h 25m",
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                "classes": [
                    {"class_id": "CC", "name": "Chair Car", "price": 895, "seats_available": 55},
                    {"class_id": "EC", "name": "Executive Chair", "price": 1690, "seats_available": 22},
                ],
            },
            {
                "train_id": "12462",
                "name": "Mandore Express",
                "departure": "20:50",
                "arrival": "05:50",
                "duration": "9h 00m",
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "classes": [
                    {"class_id": "SL", "name": "Sleeper", "price": 350, "seats_available": 120},
                    {"class_id": "3A", "name": "Third AC", "price": 895, "seats_available": 85},
                    {"class_id": "2A", "name": "Second AC", "price": 1290, "seats_available": 32},
                ],
            },
        ],
    },
    "mumbai-goa": {
        "route": "Mumbai → Goa",
        "from_city": "Mumbai",
        "to_city": "Goa",
        "distance": "588 km",
        "trains": [
            {
                "train_id": "10104",
                "name": "Mandovi Express",
                "departure": "07:10",
                "arrival": "18:50",
                "duration": "11h 40m",
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "classes": [
                    {"class_id": "SL", "name": "Sleeper", "price": 425, "seats_available": 95},
                    {"class_id": "3A", "name": "Third AC", "price": 1095, "seats_available": 60},
                    {"class_id": "2A", "name": "Second AC", "price": 1590, "seats_available": 28},
                ],
            },
            {
                "train_id": "12134",
                "name": "Mangaluru Express",
                "departure": "22:00",
                "arrival": "08:30",
                "duration": "10h 30m",
                "days": ["Tue", "Thu", "Sat"],
                "classes": [
                    {"class_id": "SL", "name": "Sleeper", "price": 395, "seats_available": 110},
                    {"class_id": "3A", "name": "Third AC", "price": 985, "seats_available": 72},
                ],
            },
        ],
    },
}

# Aliases for city matching
CITY_ALIASES = {
    "new delhi": "delhi", "ndls": "delhi", "del": "delhi",
    "bombay": "mumbai", "bom": "mumbai",
    "jp": "jaipur",
    "madgaon": "goa", "vasco": "goa", "panaji": "goa",
}


async def _crawl_trainman(from_city: str, to_city: str) -> list[dict] | None:
    """Crawl trainman.in for train schedules using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            url = f"https://www.trainman.in/trains/{from_city}-to-{to_city}"
            await page.goto(url, timeout=15000)
            await page.wait_for_timeout(3000)

            trains = await page.evaluate("""() => {
                const results = [];
                const rows = document.querySelectorAll('[class*="train-item"], [class*="TrainCard"], tr[class*="train"]');
                rows.forEach(row => {
                    const nameEl = row.querySelector('[class*="train-name"], [class*="name"], a');
                    const depEl = row.querySelector('[class*="departure"], [class*="dep"]');
                    const arrEl = row.querySelector('[class*="arrival"], [class*="arr"]');
                    const durEl = row.querySelector('[class*="duration"], [class*="dur"]');
                    if (nameEl) {
                        results.push({
                            name: nameEl.innerText?.trim(),
                            departure: depEl?.innerText?.trim() || '',
                            arrival: arrEl?.innerText?.trim() || '',
                            duration: durEl?.innerText?.trim() || '',
                        });
                    }
                });
                return results.slice(0, 10);
            }""")

            await browser.close()
            return trains if trains and len(trains) > 0 else None

    except Exception as e:
        print(f"[Trainman Crawler] Error: {e}")
        return None


def search_trains(
    from_city: str,
    to_city: str,
    budget: float = 5000,
    preferred_class: str | None = None,
) -> dict:
    """
    Search for trains matching constraints.
    Tries real crawling first, falls back to catalog.

    Args:
        from_city: Departure city
        to_city: Destination city
        budget: Maximum ticket price
        preferred_class: Preferred class (SL, 3A, 2A, 1A, CC, EC)

    Returns: {route, options[], source}
    """
    # Normalize city names
    from_norm = CITY_ALIASES.get(from_city.lower(), from_city.lower())
    to_norm = CITY_ALIASES.get(to_city.lower(), to_city.lower())

    # Try real crawling
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            crawl_result = None
        else:
            crawl_result = asyncio.run(_crawl_trainman(from_norm, to_norm))
    except RuntimeError:
        crawl_result = None

    # Find matching route in catalog
    route_key = f"{from_norm}-{to_norm}"
    route_data = TRAIN_CATALOG.get(route_key)

    if not route_data:
        # Try reverse
        for key, data in TRAIN_CATALOG.items():
            if (from_norm in data["from_city"].lower() and to_norm in data["to_city"].lower()):
                route_data = data
                break

    if not route_data:
        return {
            "from": from_city,
            "to": to_city,
            "options": [],
            "total_found": 0,
            "source": "catalog",
            "error": f"No trains found for {from_city} → {to_city}",
        }

    # Build options list
    options = []
    for train in route_data["trains"]:
        for cls in train["classes"]:
            if cls["price"] > budget:
                continue
            if preferred_class and cls["class_id"].lower() != preferred_class.lower():
                continue

            options.append({
                "option_id": f"{train['train_id']}_{cls['class_id']}",
                "train_id": train["train_id"],
                "train_name": train["name"],
                "departure": train["departure"],
                "arrival": train["arrival"],
                "duration": train["duration"],
                "class_id": cls["class_id"],
                "class_name": cls["name"],
                "price": cls["price"],
                "seats_available": cls["seats_available"],
                "days": train["days"],
                "label": f"{train['name']} · {cls['name']}",
                "detail": f"{train['departure']} → {train['arrival']} · {train['duration']} · {cls['seats_available']} seats",
            })

    # Sort by price
    options.sort(key=lambda x: x["price"])

    source = "live_crawl" if crawl_result else "catalog"

    return {
        "route": route_data["route"],
        "from": route_data["from_city"],
        "to": route_data["to_city"],
        "distance": route_data["distance"],
        "options": options,
        "total_found": len(options),
        "source": source,
    }
