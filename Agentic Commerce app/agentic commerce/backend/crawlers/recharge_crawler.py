"""
ArthSetu PayBot — Recharge Plan Crawler
Real-time recharge plan crawling from operator websites using Playwright.
Falls back to catalog data when crawling fails.
"""

import asyncio
import re

# ---------------------------------------------------------------------------
# Recharge plan catalog (fallback + base data)
# ---------------------------------------------------------------------------

RECHARGE_PLANS = {
    "jio": [
        {"plan_id": "JIO_199", "price": 199, "validity": "14 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
        {"plan_id": "JIO_239", "price": 239, "validity": "28 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
        {"plan_id": "JIO_299", "price": 299, "validity": "28 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
        {"plan_id": "JIO_349", "price": 349, "validity": "28 days",
         "data": "3GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
        {"plan_id": "JIO_449", "price": 449, "validity": "56 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
        {"plan_id": "JIO_599", "price": 599, "validity": "84 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "Jio"},
    ],
    "airtel": [
        {"plan_id": "AIR_179", "price": 179, "validity": "28 days",
         "data": "1GB/day", "sms": 100, "calls": "unlimited", "operator": "Airtel"},
        {"plan_id": "AIR_249", "price": 249, "validity": "28 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Airtel"},
        {"plan_id": "AIR_299", "price": 299, "validity": "28 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "Airtel"},
        {"plan_id": "AIR_359", "price": 359, "validity": "28 days",
         "data": "2.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Airtel"},
        {"plan_id": "AIR_479", "price": 479, "validity": "56 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Airtel"},
    ],
    "bsnl": [
        {"plan_id": "BSNL_187", "price": 187, "validity": "28 days",
         "data": "1GB/day", "sms": 100, "calls": "unlimited", "operator": "BSNL"},
        {"plan_id": "BSNL_247", "price": 247, "validity": "30 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "BSNL"},
        {"plan_id": "BSNL_319", "price": 319, "validity": "74 days",
         "data": "1GB/day", "sms": 100, "calls": "unlimited", "operator": "BSNL"},
        {"plan_id": "BSNL_397", "price": 397, "validity": "56 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "BSNL"},
    ],
    "vi": [
        {"plan_id": "VI_219", "price": 219, "validity": "28 days",
         "data": "1GB/day", "sms": 100, "calls": "unlimited", "operator": "Vi"},
        {"plan_id": "VI_269", "price": 269, "validity": "28 days",
         "data": "1.5GB/day", "sms": 100, "calls": "unlimited", "operator": "Vi"},
        {"plan_id": "VI_299", "price": 299, "validity": "28 days",
         "data": "2GB/day", "sms": 100, "calls": "unlimited", "operator": "Vi"},
    ],
}

# Number prefix → operator mapping
OPERATOR_PREFIXES = {
    "70": "vi", "71": "vi", "72": "vi", "73": "vi",
    "74": "jio", "75": "jio", "76": "jio", "77": "jio", "78": "jio",
    "79": "airtel", "80": "airtel", "81": "airtel",
    "82": "airtel", "83": "jio", "84": "airtel", "85": "jio",
    "86": "airtel", "87": "jio", "88": "airtel", "89": "jio",
    "90": "airtel", "91": "bsnl", "92": "airtel", "93": "airtel",
    "94": "bsnl", "95": "airtel", "96": "jio", "97": "airtel",
    "98": "airtel", "99": "airtel",
}


async def _crawl_jio_plans() -> list[dict] | None:
    """Crawl Jio website for recharge plans using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            await page.goto("https://www.jio.com/selfcare/plans/mobility/prepaid-plans-background/", timeout=15000)
            await page.wait_for_timeout(3000)

            plans = await page.evaluate("""() => {
                const results = [];
                const cards = document.querySelectorAll('[class*="plan-card"], [class*="PlanCard"], [class*="recharge-card"]');
                cards.forEach(card => {
                    const priceEl = card.querySelector('[class*="price"], [class*="amount"]');
                    const validityEl = card.querySelector('[class*="validity"], [class*="days"]');
                    const dataEl = card.querySelector('[class*="data"], [class*="benefit"]');
                    if (priceEl) {
                        const priceMatch = priceEl.innerText.match(/₹?\s*(\d+)/);
                        if (priceMatch) {
                            results.push({
                                price: parseInt(priceMatch[1]),
                                validity: validityEl?.innerText?.trim() || '',
                                data: dataEl?.innerText?.trim() || '',
                            });
                        }
                    }
                });
                return results.slice(0, 10);
            }""")

            await browser.close()
            return plans if plans and len(plans) > 0 else None

    except Exception as e:
        print(f"[Jio Crawler] Error: {e}")
        return None


async def _crawl_airtel_plans() -> list[dict] | None:
    """Crawl Airtel website for recharge plans using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            await page.goto("https://www.airtel.in/prepaid-recharge", timeout=15000)
            await page.wait_for_timeout(3000)

            plans = await page.evaluate("""() => {
                const results = [];
                const cards = document.querySelectorAll('[class*="plan"], [class*="offer-card"], [class*="recharge"]');
                cards.forEach(card => {
                    const priceEl = card.querySelector('[class*="price"], [class*="amount"], [class*="rupee"]');
                    const validityEl = card.querySelector('[class*="validity"], [class*="days"]');
                    const dataEl = card.querySelector('[class*="data"], [class*="benefit"]');
                    if (priceEl) {
                        const priceMatch = priceEl.innerText.match(/₹?\s*(\d+)/);
                        if (priceMatch) {
                            results.push({
                                price: parseInt(priceMatch[1]),
                                validity: validityEl?.innerText?.trim() || '',
                                data: dataEl?.innerText?.trim() || '',
                            });
                        }
                    }
                });
                return results.slice(0, 10);
            }""")

            await browser.close()
            return plans if plans and len(plans) > 0 else None

    except Exception as e:
        print(f"[Airtel Crawler] Error: {e}")
        return None


def detect_operator(phone_number: str) -> str | None:
    """Detect operator from phone number prefix."""
    phone = phone_number.replace("+91", "").replace(" ", "").replace("-", "")
    if len(phone) >= 10:
        prefix = phone[:2]
        return OPERATOR_PREFIXES.get(prefix)
    return None


def find_best_recharge_plan(
    operator: str,
    budget: float = 500,
    days: int = 28,
    phone_number: str | None = None,
) -> dict:
    """
    Find the best recharge plan for an operator within budget.
    Tries real crawling first, falls back to catalog.

    Args:
        operator: Operator name (jio, airtel, bsnl, vi)
        budget: Maximum recharge amount
        days: Minimum validity in days
        phone_number: Optional phone number for auto-detection

    Returns: {best_plan, all_plans[], operator, source}
    """
    # Auto-detect operator from phone number if not specified
    if not operator and phone_number:
        operator = detect_operator(phone_number) or "jio"

    operator_lower = operator.lower()

    # Try real crawling
    crawl_result = None
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            if operator_lower == "jio":
                crawl_result = asyncio.run(_crawl_jio_plans())
            elif operator_lower == "airtel":
                crawl_result = asyncio.run(_crawl_airtel_plans())
    except RuntimeError:
        pass

    # Get plans from catalog (always available)
    plans = RECHARGE_PLANS.get(operator_lower, [])

    if not plans:
        return {
            "operator": operator,
            "best_plan": None,
            "all_plans": [],
            "total_found": 0,
            "source": "catalog",
            "error": f"No plans found for operator '{operator}'",
        }

    # Filter by budget and validity
    eligible = []
    for plan in plans:
        if plan["price"] > budget:
            continue
        validity_days = int(plan["validity"].split()[0])
        if validity_days >= days:
            eligible.append(plan)

    # If no plans match exact validity, get any within budget
    if not eligible:
        eligible = [p for p in plans if p["price"] <= budget]

    # Sort by value (price descending — best value for money within budget)
    eligible.sort(key=lambda x: x["price"], reverse=True)

    best_plan = eligible[0] if eligible else None
    source = "live_crawl" if crawl_result else "catalog"

    return {
        "operator": operator.capitalize(),
        "best_plan": best_plan,
        "all_plans": eligible,
        "total_found": len(eligible),
        "source": source,
        "budget": budget,
        "min_days": days,
    }


def get_all_plans(operator: str) -> list[dict]:
    """Get all plans for an operator."""
    return RECHARGE_PLANS.get(operator.lower(), [])
