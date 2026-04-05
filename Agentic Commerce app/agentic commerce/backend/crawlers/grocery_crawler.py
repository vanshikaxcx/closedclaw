"""
ArthSetu PayBot — Grocery Price Comparison Crawler
Real-time price crawling from Blinkit, Zepto, BigBasket using Playwright.
Falls back to cached data gracefully if crawling fails.
"""

import asyncio
import re
import json
import os
import time
from typing import Optional


STEALTH_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


def _is_blocked_status(status: int | None) -> bool:
    return status is None or status >= 400


async def _apply_stealth(page):
    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# ---------------------------------------------------------------------------
# Fallback / cached prices (used when crawlers are blocked or unavailable)
# ---------------------------------------------------------------------------

FALLBACK_PRICES = {
    "atta": {
        "blinkit": {"name": "Aashirvaad Whole Wheat Atta 2 kg", "price": 145, "unit": "2 kg", "source": "fallback"},
        "zepto": {"name": "Aashirvaad Atta Whole Wheat 2 kg", "price": 138, "unit": "2 kg", "source": "fallback"},
        "bigbasket": {"name": "Aashirvaad Select Whole Wheat Atta 2 kg", "price": 152, "unit": "2 kg", "source": "fallback"},
    },
    "milk": {
        "blinkit": {"name": "Amul Taaza Toned Fresh Milk 1 L", "price": 68, "unit": "1 L", "source": "fallback"},
        "zepto": {"name": "Amul Taaza Toned Milk 1 L", "price": 68, "unit": "1 L", "source": "fallback"},
        "bigbasket": {"name": "Amul Taaza Homogenised Toned Milk 1 L", "price": 65, "unit": "1 L", "source": "fallback"},
    },
    "rice": {
        "blinkit": {"name": "India Gate Basmati Rice Classic 1 kg", "price": 185, "unit": "1 kg", "source": "fallback"},
        "zepto": {"name": "India Gate Classic Basmati Rice 1 kg", "price": 179, "unit": "1 kg", "source": "fallback"},
        "bigbasket": {"name": "India Gate Basmati Rice - Classic 1 kg", "price": 189, "unit": "1 kg", "source": "fallback"},
    },
    "sugar": {
        "blinkit": {"name": "Uttam Sugar Pure Sulphurless 1 kg", "price": 46, "unit": "1 kg", "source": "fallback"},
        "zepto": {"name": "Uttam Sugar 1 kg", "price": 44, "unit": "1 kg", "source": "fallback"},
        "bigbasket": {"name": "Uttam Sugar - Sulphurless 1 kg", "price": 48, "unit": "1 kg", "source": "fallback"},
    },
    "oil": {
        "blinkit": {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "price": 145, "unit": "1 L", "source": "fallback"},
        "zepto": {"name": "Fortune Sunlite Sunflower Oil 1 L", "price": 140, "unit": "1 L", "source": "fallback"},
        "bigbasket": {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "price": 148, "unit": "1 L", "source": "fallback"},
    },
    "dal": {
        "blinkit": {"name": "Tata Sampann Toor Dal 1 kg", "price": 175, "unit": "1 kg", "source": "fallback"},
        "zepto": {"name": "Tata Sampann Toor Dal 1 kg", "price": 169, "unit": "1 kg", "source": "fallback"},
        "bigbasket": {"name": "Tata Sampann Unpolished Tur Dal 1 kg", "price": 179, "unit": "1 kg", "source": "fallback"},
    },
    "bread": {
        "blinkit": {"name": "Harvest Gold White Bread 400 g", "price": 45, "unit": "400 g", "source": "fallback"},
        "zepto": {"name": "Harvest Gold White Bread 400 g", "price": 42, "unit": "400 g", "source": "fallback"},
        "bigbasket": {"name": "Harvest Gold Premium White Bread 400 g", "price": 46, "unit": "400 g", "source": "fallback"},
    },
    "eggs": {
        "blinkit": {"name": "Fresho Farm Eggs Pack of 6", "price": 54, "unit": "6 pcs", "source": "fallback"},
        "zepto": {"name": "Country Eggs Pack of 6", "price": 52, "unit": "6 pcs", "source": "fallback"},
        "bigbasket": {"name": "Fresho Farm Eggs 6 pcs", "price": 55, "unit": "6 pcs", "source": "fallback"},
    },
    "paneer": {
        "blinkit": {"name": "Amul Fresh Paneer 200 g", "price": 95, "unit": "200 g", "source": "fallback"},
        "zepto": {"name": "Amul Fresh Paneer 200 g", "price": 92, "unit": "200 g", "source": "fallback"},
        "bigbasket": {"name": "Milky Mist Paneer 200 g", "price": 98, "unit": "200 g", "source": "fallback"},
    },
    "whey protein": {
        "blinkit": {"name": "MuscleBlaze Whey Protein 1 kg", "price": 2199, "unit": "1 kg", "source": "fallback"},
        "zepto": {"name": "Optimum Nutrition Whey Protein 1 lb", "price": 1899, "unit": "1 lb", "source": "fallback"},
        "bigbasket": {"name": "AS-IT-IS Whey Protein Concentrate 1 kg", "price": 1799, "unit": "1 kg", "source": "fallback"},
    },
}

_QUERY_STOPWORDS = {
    "gm", "g", "gram", "grams", "kg", "ml", "l", "litre", "liter", "of",
    "the", "a", "an", "pack", "packet", "piece", "pieces", "pc", "pcs",
    "x", "qty", "quantity",
}

_NON_PRODUCT_LABELS = {
    "add", "buy", "buy now", "view", "shop", "see all", "offers", "offer",
    "price", "mrp", "₹", "rs", "cart",
}


def _normalize_item_query(item: str) -> str:
    """Normalize noisy user query text (qty/units/fillers) to product-centric terms."""
    text = (item or "").lower().strip()
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _QUERY_STOPWORDS]
    return " ".join(tokens).strip() or (item or "").strip().lower()


def _sanitize_product_name(name: str | None, query: str, platform: str) -> str:
    """Ensure scraped product name is always meaningful and never blank."""
    cleaned = (name or "").strip()
    lowered = cleaned.lower()

    is_non_product = (
        not cleaned
        or lowered in _NON_PRODUCT_LABELS
        or re.fullmatch(r"[₹\s\d.,/-]+", cleaned) is not None
        or (len(cleaned) <= 4 and cleaned.isupper())
    )

    if not is_non_product:
        return cleaned

    if cleaned:
        # remove obvious tokens but keep meaningful words if any
        cleaned = re.sub(r"\b(add|buy|view|offer|cart|mrp)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned and cleaned.lower() not in _NON_PRODUCT_LABELS:
            return cleaned

    query_clean = query.strip().title() if query else "Product"
    return f"{query_clean} ({platform.title()})"


def _sanitize_platform_result(result: dict | None, query: str, platform: str) -> dict | None:
    """Normalize platform payloads and remove blank-name artifacts."""
    if not result:
        return None

    result["name"] = _sanitize_product_name(result.get("name"), query, platform)
    all_results = result.get("all_results", [])
    sanitized_results = []
    for idx, entry in enumerate(all_results):
        if not isinstance(entry, dict):
            continue
        price = entry.get("price")
        if price is None:
            continue
        if not _is_plausible_price(query, price):
            continue
        sanitized_results.append({
            "name": _sanitize_product_name(entry.get("name"), query, platform),
            "price": price,
        })
        if len(sanitized_results) >= 3:
            break

    if sanitized_results:
        result["all_results"] = sanitized_results
        result["price"] = sanitized_results[0]["price"]
        result["name"] = sanitized_results[0]["name"]
    elif not _is_plausible_price(query, result.get("price")):
        return None
    return result


def _is_plausible_price(query: str, price: float | int | None) -> bool:
    """Guardrail against parsing noise from blocked pages or UI fragments."""
    if price is None:
        return False
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False

    q = (query or "").lower()
    if "whey" in q or "protein" in q:
        return 300 <= p <= 15000
    if "paneer" in q:
        return 30 <= p <= 1500
    if "milk" in q:
        return 10 <= p <= 500
    if "atta" in q:
        return 20 <= p <= 2000
    if "rice" in q or "dal" in q or "oil" in q or "sugar" in q:
        return 20 <= p <= 5000

    return 10 <= p <= 50000

# ---------------------------------------------------------------------------
# Playwright-based crawlers
# ---------------------------------------------------------------------------

async def _crawl_blinkit(item: str, qty_hint: str = "") -> dict | None:
    """Crawl Blinkit for product prices using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=STEALTH_ARGS)
            context = await browser.new_context(
                user_agent=STEALTH_UA,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                extra_http_headers={"accept-language": "en-IN,en;q=0.9"},
            )
            page = await context.new_page()
            await _apply_stealth(page)

            # Set a Delhi location cookie/localStorage for delivery availability
            home_resp = await page.goto("https://blinkit.com/", timeout=15000)
            await page.wait_for_timeout(2000)
            if _is_blocked_status(home_resp.status if home_resp else None):
                await browser.close()
                return None

            # Search for the item
            search_url = f"https://blinkit.com/s/?q={item}"
            search_resp = await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(3000)
            if _is_blocked_status(search_resp.status if search_resp else None):
                await browser.close()
                return None
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            await page.wait_for_timeout(1200)

            # Extract product cards
            products = await page.evaluate("""(query) => {
                const results = [];
                const pushResult = (name, price) => {
                    if (!price || Number.isNaN(price)) return;
                    results.push({ name: (name || '').trim(), price: parseInt(price) });
                };

                const queryWords = (query || '').toLowerCase().split(/\s+/).filter(Boolean);

                // 1) Prefer structured state (much cleaner than scraping random DOM text)
                const state = window?.grofers?.PRELOADED_STATE;
                const seen = new Set();
                const walk = (node) => {
                    if (!node) return;
                    if (Array.isArray(node)) {
                        node.forEach(walk);
                        return;
                    }
                    if (typeof node !== 'object') return;

                    const name = (node.name || node.title || node.display_name || '').toString().trim();
                    const p = node.discounted_price ?? node.selling_price ?? node.offer_price ?? node.price ?? node.mrp;
                    const price = typeof p === 'number' ? p : parseFloat(String(p || '').replace(/[^\d.]/g, ''));
                    if (name && price && Number.isFinite(price)) {
                        const lname = name.toLowerCase();
                        const relevance = queryWords.length === 0 || queryWords.some(w => lname.includes(w));
                        if (relevance) {
                            const key = `${lname}__${price}`;
                            if (!seen.has(key)) {
                                seen.add(key);
                                pushResult(name, price);
                            }
                        }
                    }
                    Object.values(node).forEach(walk);
                };

                if (state) {
                    walk(state);
                }

                if (results.length > 0) {
                    return results.sort((a, b) => a.price - b.price).slice(0, 8);
                }

                const parseCard = (card) => {
                    const nameEl = card.querySelector('[class*="Product__UpdatedTitle"], [class*="title"], h3, h4, h5');
                    const priceEl = card.querySelector('[class*="Product__UpdatedPriceAndAtcRow"], [class*="price"], [class*="Price"]');
                    const priceText = priceEl?.innerText || card.innerText || '';
                    const priceMatch = priceText.match(/₹\s*(\d+)/);
                    if (priceMatch) {
                        pushResult(nameEl?.innerText || query, priceMatch[1]);
                    }
                };

                const cards = document.querySelectorAll('[class*="Product__UpdatedPlpProductContainer"]');
                cards.forEach(parseCard);

                const testCards = document.querySelectorAll('[data-testid="plp-product"]');
                testCards.forEach(parseCard);

                if (results.length === 0) {
                    const divs = document.querySelectorAll('div[role="button"], a[href*="/prn/"]');
                    divs.forEach(parseCard);
                }

                if (results.length === 0) {
                    const lines = document.body.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                    const isQty = (s) => /^\d+(?:\.\d+)?\s?(kg|g|gm|ml|l|litre|liter|pcs|pc|pack)$/i.test(s || '');
                    const badName = (s) => /^(add|mins?|off|showing results|my cart|welcome|detect my location|or)$/i.test((s || '').trim());
                    lines.forEach((line, idx) => {
                        const pm = line.match(/₹\s*(\d+)/);
                        if (!pm) return;
                        const prev1 = idx > 0 ? lines[idx - 1] : '';
                        const prev2 = idx > 1 ? lines[idx - 2] : '';
                        if (!isQty(prev1)) return;
                        let name = query;
                        if (isQty(prev1) && prev2 && !prev2.includes('₹') && !badName(prev2)) {
                            name = prev2;
                        } else if (prev1 && !prev1.includes('₹') && !badName(prev1) && !/\d+\s*MINS?/i.test(prev1)) {
                            name = prev1;
                        }
                        pushResult(name, pm[1]);
                    });
                }

                return results.slice(0, 5);
            }""", item)

            await browser.close()

            if products and len(products) > 0:
                best = products[0]  # First result is usually best match
                return {
                    "name": best["name"],
                    "price": best["price"],
                    "unit": qty_hint or "1 unit",
                    "source": "live_crawl",
                    "platform": "blinkit",
                    "all_results": products[:3],
                }
            return None

    except Exception as e:
        print(f"[Blinkit Crawler] Error: {e}")
        return None


async def _crawl_zepto(item: str, qty_hint: str = "") -> dict | None:
    """Crawl Zepto for product prices using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=STEALTH_ARGS)
            context = await browser.new_context(
                user_agent=STEALTH_UA,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                extra_http_headers={"accept-language": "en-IN,en;q=0.9"},
            )
            page = await context.new_page()
            await _apply_stealth(page)

            search_url = f"https://www.zepto.com/search?query={item}"
            search_resp = await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(3000)
            if _is_blocked_status(search_resp.status if search_resp else None):
                await browser.close()
                return None
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            await page.wait_for_timeout(1200)

            products = await page.evaluate("""(query) => {
                const results = [];
                // Zepto product containers
                const cards = document.querySelectorAll('[data-testid="product-card"], [class*="product-card"], [class*="ProductCard"]');
                if (cards.length > 0) {
                    cards.forEach(card => {
                        const nameEl = card.querySelector('[class*="product-title"], [class*="ProductTitle"], h5, h4');
                        const priceEl = card.querySelector('[class*="product-price"], [class*="Price"], [class*="price"]');
                        if (nameEl && priceEl) {
                            const priceText = priceEl.innerText;
                            const priceMatch = priceText.match(/₹\s*(\d+)/);
                            if (priceMatch) {
                                results.push({
                                    name: nameEl.innerText.trim(),
                                    price: parseInt(priceMatch[1]),
                                });
                            }
                        }
                    });
                }
                // Fallback: look for any element with price symbol
                if (results.length === 0) {
                    const allText = document.body.innerText;
                    const lines = allText.split('\\n').map(l => l.trim()).filter(Boolean);
                    lines.forEach((line, idx) => {
                        if (!line.includes('₹')) return;
                        const priceMatch = line.match(/₹\s*(\d+)/);
                        if (!priceMatch) return;
                        let candidate = line.replace(/₹\s*\d+[\d,.]*/, '').trim();
                        if (!candidate && idx > 0) {
                            const prev = lines[idx - 1];
                            if (prev && !prev.includes('₹')) {
                                candidate = prev.trim();
                            }
                        }
                        if (!candidate) {
                            candidate = query;
                        }
                        if (candidate && priceMatch) {
                            results.push({
                                name: candidate.substring(0, 80),
                                price: parseInt(priceMatch[1]),
                            });
                        }
                    });
                }
                return results.slice(0, 5);
            }""", item)

            await browser.close()

            if products and len(products) > 0:
                best = products[0]
                return {
                    "name": best["name"],
                    "price": best["price"],
                    "unit": qty_hint or "1 unit",
                    "source": "live_crawl",
                    "platform": "zepto",
                    "all_results": products[:3],
                }
            return None

    except Exception as e:
        print(f"[Zepto Crawler] Error: {e}")
        return None


async def _crawl_bigbasket(item: str, qty_hint: str = "") -> dict | None:
    """Crawl BigBasket for product prices using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            async def _run_once(headless_mode: bool) -> list[dict] | None:
                browser = await p.chromium.launch(headless=headless_mode, args=STEALTH_ARGS)
                context = await browser.new_context(
                    user_agent=STEALTH_UA,
                    viewport={"width": 1280, "height": 800},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    extra_http_headers={"accept-language": "en-IN,en;q=0.9"},
                )
                page = await context.new_page()
                await _apply_stealth(page)

                search_url = f"https://www.bigbasket.com/ps/?q={item}&nc=as"
                search_resp = await page.goto(search_url, timeout=20000)
                await page.wait_for_timeout(3000)

                if _is_blocked_status(search_resp.status if search_resp else None):
                    await browser.close()
                    return None

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
                await page.wait_for_timeout(1200)

                products = await page.evaluate("""(query) => {
                    const results = [];
                    // BigBasket product listings
                    const cards = document.querySelectorAll('[qa="product"], [class*="SKUDeck"], [class*="product-deck"], li[class*="PaginateItems"]');
                    if (cards.length > 0) {
                        cards.forEach(card => {
                            const nameEl = card.querySelector('[class*="BrandName"], [class*="Description"], h3, a[class*="ng-binding"]');
                            const priceEl = card.querySelector('[class*="DiscountPrice"], [class*="MRP"], [class*="price"], span.big');
                            if (nameEl && priceEl) {
                                const priceText = priceEl.innerText;
                                const priceMatch = priceText.match(/₹\s*(\d+\.?\d*)/);
                                if (priceMatch) {
                                    results.push({
                                        name: (nameEl.innerText || query).trim(),
                                        price: parseFloat(priceMatch[1]),
                                    });
                                }
                            }
                        });
                    }
                    // Aggressive fallback
                    if (results.length === 0) {
                        const spans = document.querySelectorAll('span, div');
                        const priceEls = [];
                        spans.forEach(el => {
                            if (el.innerText && el.innerText.match(/^₹\s*\d+/) && el.innerText.length < 20) {
                                priceEls.push(el);
                            }
                        });
                        priceEls.slice(0, 5).forEach(el => {
                            const priceMatch = el.innerText.match(/₹\s*(\d+\.?\d*)/);
                            const parent = el.closest('div[class]') || el.parentElement;
                            const nameEl = parent?.querySelector('h3, a, span[class*="name"], [class*="Description"]');
                            if (priceMatch) {
                                results.push({
                                    name: nameEl?.innerText?.trim() || query,
                                    price: parseFloat(priceMatch[1]),
                                });
                            }
                        });
                    }

                    if (results.length === 0) {
                        const lines = document.body.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                        lines.forEach((line, idx) => {
                            const pm = line.match(/₹\s*(\d+\.?\d*)/);
                            if (!pm) return;
                            const prev = idx > 0 ? lines[idx - 1] : '';
                            const name = prev && !prev.includes('₹') ? prev : query;
                            results.push({ name: name.substring(0, 80), price: parseFloat(pm[1]) });
                        });
                    }
                    return results.slice(0, 5);
                }""", item)

                await browser.close()
                return products

            products = await _run_once(True)
            allow_headed_retry = os.getenv("BIGBASKET_HEADED_RETRY", "1") == "1"
            if not products and allow_headed_retry:
                products = await _run_once(False)

            if products and len(products) > 0:
                best = products[0]
                return {
                    "name": best["name"],
                    "price": best["price"],
                    "unit": qty_hint or "1 unit",
                    "source": "live_crawl",
                    "platform": "bigbasket",
                    "all_results": products[:3],
                }
            return None

    except Exception as e:
        print(f"[BigBasket Crawler] Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def crawl_grocery_prices(item: str, qty_hint: str = "", use_fallback: bool = True) -> dict:
    """
    Crawl real prices from Blinkit, Zepto, BigBasket for a grocery item.
    Falls back to cached data if crawling fails.
    Returns: {blinkit: {...}, zepto: {...}, bigbasket: {...}, cheapest: str}
    """
    item_lower = item.lower().strip()
    normalized_item = _normalize_item_query(item_lower)

    # Try to crawl all three platforms concurrently
    results = await asyncio.gather(
        _crawl_blinkit(normalized_item, qty_hint),
        _crawl_zepto(normalized_item, qty_hint),
        _crawl_bigbasket(normalized_item, qty_hint),
        return_exceptions=True,
    )

    blinkit_result = results[0] if not isinstance(results[0], Exception) and results[0] else None
    zepto_result = results[1] if not isinstance(results[1], Exception) and results[1] else None
    bigbasket_result = results[2] if not isinstance(results[2], Exception) and results[2] else None

    blinkit_result = _sanitize_platform_result(blinkit_result, normalized_item, "blinkit")
    zepto_result = _sanitize_platform_result(zepto_result, normalized_item, "zepto")
    bigbasket_result = _sanitize_platform_result(bigbasket_result, normalized_item, "bigbasket")

    # Fill in fallback for any platform that failed (optional)
    fallback_key = _find_fallback_key(normalized_item) or _find_fallback_key(item_lower)

    if use_fallback and not blinkit_result and fallback_key:
        blinkit_result = {**FALLBACK_PRICES[fallback_key]["blinkit"], "platform": "blinkit"}
    if use_fallback and not zepto_result and fallback_key:
        zepto_result = {**FALLBACK_PRICES[fallback_key]["zepto"], "platform": "zepto"}
    if use_fallback and not bigbasket_result and fallback_key:
        bigbasket_result = {**FALLBACK_PRICES[fallback_key]["bigbasket"], "platform": "bigbasket"}

    # Determine cheapest
    platforms = {}
    for name, result in [("blinkit", blinkit_result), ("zepto", zepto_result), ("bigbasket", bigbasket_result)]:
        if result:
            platforms[name] = result

    cheapest = min(platforms.keys(), key=lambda k: platforms[k]["price"]) if platforms else None

    return {
        "item": item,
        "normalized_item": normalized_item,
        "blinkit": blinkit_result,
        "zepto": zepto_result,
        "bigbasket": bigbasket_result,
        "cheapest_platform": cheapest,
        "cheapest_price": platforms[cheapest]["price"] if cheapest else None,
        "platforms_crawled": sum(1 for r in [blinkit_result, zepto_result, bigbasket_result] if r and r.get("source") == "live_crawl"),
        "platforms_fallback": sum(1 for r in [blinkit_result, zepto_result, bigbasket_result] if r and r.get("source") == "fallback"),
    }


def compare_grocery_prices_sync(items: list[dict], use_fallback: bool = True) -> dict:
    """
    Synchronous wrapper for comparing grocery prices across platforms.
    items: [{"name": "atta", "qty": "2 kg"}, ...]
    Works safely whether called from sync or async context.
    """
    import concurrent.futures

    try:
        loop = asyncio.get_running_loop()
        # We're inside an async context — run in a thread
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _compare_multiple(items, use_fallback=use_fallback))
            return future.result(timeout=60)
    except RuntimeError:
        # No running loop — safe to use asyncio.run directly
        return asyncio.run(_compare_multiple(items, use_fallback=use_fallback))


async def _compare_multiple(items: list[dict], use_fallback: bool = True) -> dict:
    """Compare prices for multiple items across platforms."""
    comparisons = []
    for item in items:
        result = await crawl_grocery_prices(item["name"], item.get("qty", ""), use_fallback=use_fallback)
        comparisons.append(result)

    # Calculate cheapest split (buy each item from cheapest platform)
    total_cheapest = 0
    split_orders = []
    for comp in comparisons:
        if comp["cheapest_platform"] and comp["cheapest_price"]:
            total_cheapest += comp["cheapest_price"]
            split_orders.append({
                "item": comp["item"],
                "platform": comp["cheapest_platform"],
                "price": comp["cheapest_price"],
            })

    return {
        "comparisons": comparisons,
        "cheapest_split": split_orders,
        "total_cheapest": total_cheapest,
        "recommendation": f"Buy from cheapest split across platforms for Rs.{total_cheapest} total",
    }


def _find_fallback_key(item: str) -> str | None:
    """Find the best matching fallback key for an item name."""
    item = item.lower()
    for key in FALLBACK_PRICES:
        if key in item or item in key:
            return key
    # Partial match
    for key in FALLBACK_PRICES:
        if any(word in item for word in key.split()) or any(word in key for word in item.split()):
            return key
    return None
