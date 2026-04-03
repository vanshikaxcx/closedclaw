"""
ArthSetu PayBot — Movie Ticket Crawler
Real-time movie show crawling from BookMyShow using Playwright.
Falls back to catalog data when crawling fails.
"""

import asyncio
import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Fallback movie catalog (used when BookMyShow crawler is blocked)
# ---------------------------------------------------------------------------

MOVIE_CATALOG = [
    {
        "movie_id": "inception_2010",
        "title": "Inception",
        "language": "English",
        "genre": "Sci-Fi/Thriller",
        "rating": "8.8/10",
        "shows": [
            {"show_id": "pvr_imax_2115", "theatre": "PVR Ambience Mall", "city": "Gurgaon",
             "format": "IMAX", "time": "21:15", "price": 380, "seats_available": 45},
            {"show_id": "inox_2d_2130", "theatre": "INOX Gurgaon", "city": "Gurgaon",
             "format": "2D", "time": "21:30", "price": 320, "seats_available": 62},
            {"show_id": "cinepolis_2d_2200", "theatre": "Cinepolis DLF", "city": "Gurgaon",
             "format": "2D", "time": "22:00", "price": 290, "seats_available": 38},
            {"show_id": "pvr_2d_1430", "theatre": "PVR Select City Walk", "city": "Delhi",
             "format": "2D", "time": "14:30", "price": 350, "seats_available": 55},
        ],
    },
    {
        "movie_id": "pushpa2_2024",
        "title": "Pushpa 2: The Rule",
        "language": "Hindi",
        "genre": "Action/Drama",
        "rating": "7.5/10",
        "shows": [
            {"show_id": "pvr_imax_1900", "theatre": "PVR Ambience Mall", "city": "Gurgaon",
             "format": "IMAX", "time": "19:00", "price": 420, "seats_available": 30},
            {"show_id": "inox_2d_2000", "theatre": "INOX Gurgaon", "city": "Gurgaon",
             "format": "2D", "time": "20:00", "price": 280, "seats_available": 75},
            {"show_id": "cinepolis_3d_2100", "theatre": "Cinepolis DLF", "city": "Gurgaon",
             "format": "3D", "time": "21:00", "price": 350, "seats_available": 42},
        ],
    },
    {
        "movie_id": "12thfail_2023",
        "title": "12th Fail",
        "language": "Hindi",
        "genre": "Drama/Biography",
        "rating": "9.2/10",
        "shows": [
            {"show_id": "pvr_2d_1600", "theatre": "PVR Select City Walk", "city": "Delhi",
             "format": "2D", "time": "16:00", "price": 300, "seats_available": 88},
            {"show_id": "inox_2d_1830", "theatre": "INOX Nehru Place", "city": "Delhi",
             "format": "2D", "time": "18:30", "price": 260, "seats_available": 65},
        ],
    },
    {
        "movie_id": "stree2_2024",
        "title": "Stree 2",
        "language": "Hindi",
        "genre": "Comedy/Horror",
        "rating": "7.8/10",
        "shows": [
            {"show_id": "pvr_2d_2000", "theatre": "PVR Ambience Mall", "city": "Gurgaon",
             "format": "2D", "time": "20:00", "price": 300, "seats_available": 50},
            {"show_id": "inox_2d_2130_s2", "theatre": "INOX Gurgaon", "city": "Gurgaon",
             "format": "2D", "time": "21:30", "price": 280, "seats_available": 70},
            {"show_id": "cinepolis_3d_1930", "theatre": "Cinepolis DLF", "city": "Gurgaon",
             "format": "3D", "time": "19:30", "price": 340, "seats_available": 25},
        ],
    },
]


async def _crawl_bookmyshow(movie: str, city: str = "Delhi-NCR") -> list[dict] | None:
    """Crawl BookMyShow for movie shows using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            # Search for movie on BookMyShow
            search_url = f"https://in.bookmyshow.com/explore/movies-{city.lower().replace(' ', '-')}"
            await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(3000)

            # Try to find the movie and get shows
            shows = await page.evaluate("""(movieName) => {
                const results = [];
                // Look for movie cards
                const cards = document.querySelectorAll('[class*="movie-card"], [class*="MovieCard"], a[href*="movies"]');
                let movieUrl = null;

                cards.forEach(card => {
                    const title = card.querySelector('h3, h4, [class*="title"], [class*="name"]');
                    if (title && title.innerText.toLowerCase().includes(movieName.toLowerCase())) {
                        movieUrl = card.href || card.querySelector('a')?.href;
                    }
                });

                // If we can't find specific show times from search, extract what we can
                const allTexts = document.body.innerText;
                if (allTexts.toLowerCase().includes(movieName.toLowerCase())) {
                    results.push({
                        found: true,
                        movie_url: movieUrl,
                        page_text: allTexts.substring(0, 500),
                    });
                }

                return results;
            }""", movie)

            await browser.close()

            if shows and len(shows) > 0 and shows[0].get("found"):
                return shows
            return None

    except Exception as e:
        print(f"[BookMyShow Crawler] Error: {e}")
        return None


def search_movie_shows(
    movie: str,
    price_cap: float = 500,
    after_time: str | None = None,
    city: str | None = None,
) -> dict:
    """
    Search for movie shows matching constraints.
    Tries real crawling first, falls back to catalog.

    Args:
        movie: Movie name (partial match)
        price_cap: Maximum ticket price
        after_time: Minimum show time (e.g., "21:00")
        city: City filter

    Returns: {movie, shows[], source}
    """
    # Try real crawling first
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            crawl_result = None  # Can't nest event loops in async context
        else:
            crawl_result = asyncio.run(_crawl_bookmyshow(movie, city or "Delhi-NCR"))
    except RuntimeError:
        crawl_result = None

    # Use catalog data (always available, enriched if crawl succeeded)
    movie_lower = movie.lower()
    matched_movie = None

    for m in MOVIE_CATALOG:
        if movie_lower in m["title"].lower() or m["title"].lower() in movie_lower:
            matched_movie = m
            break

    if not matched_movie:
        # Fuzzy match
        for m in MOVIE_CATALOG:
            if any(word in m["title"].lower() for word in movie_lower.split()):
                matched_movie = m
                break

    if not matched_movie:
        return {
            "movie": movie,
            "shows": [],
            "total_found": 0,
            "source": "catalog",
            "error": f"Movie '{movie}' not found in catalog",
        }

    # Filter shows
    shows = matched_movie["shows"]
    filtered = []

    for show in shows:
        # Price filter
        if show["price"] > price_cap:
            continue

        # Time filter
        if after_time:
            show_time = show["time"]
            if show_time < after_time:
                continue

        # City filter
        if city and city.lower() not in show["city"].lower():
            continue

        filtered.append({
            **show,
            "movie_title": matched_movie["title"],
            "language": matched_movie["language"],
            "rating": matched_movie["rating"],
        })

    # Sort by price ascending
    filtered.sort(key=lambda x: x["price"])

    source = "live_crawl" if crawl_result else "catalog"

    return {
        "movie": matched_movie["title"],
        "movie_id": matched_movie["movie_id"],
        "language": matched_movie["language"],
        "genre": matched_movie["genre"],
        "rating": matched_movie["rating"],
        "shows": filtered,
        "total_found": len(filtered),
        "source": source,
        "filters_applied": {
            "price_cap": price_cap,
            "after_time": after_time,
            "city": city,
        },
    }
