"""
HomePath (Fannie Mae REO) scraper – complete rewrite.
Uses Playwright to navigate the React SPA, capturing actual listing URLs
and thorough property data for all NWA ZIP codes.
"""
import logging
import re
import time
import urllib.parse

from playwright.sync_api import sync_playwright

from config import AREA, THRESHOLDS

log = logging.getLogger(__name__)

_BASE = "https://homepath.fanniemae.com"

# Search all NWA ZIPs + city names for thorough coverage
_SEARCH_TERMS = [
    "Bentonville, AR",
    "Rogers, AR",
    "Centerton, AR",
    "Bella Vista, AR",
    "Cave Springs, AR",
    "Lowell, AR",
    "Pea Ridge, AR",
    "Gravette, AR",
]

_PRICE_RE = re.compile(r"\$([\d,]+)")
_BEDS_RE = re.compile(r"(\d)\s*(?:bed|BR|bedroom)", re.I)
_BATHS_RE = re.compile(r"(\d(?:\.\d)?)\s*(?:bath|Ba)", re.I)
_SQFT_RE = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft)", re.I)
_ADDR_RE = re.compile(r"\d+\s+[A-Z][a-z].{2,40},\s*[A-Za-z ]+,?\s*AR\s*\d{5}", re.I)


def _safe_float(val) -> float | None:
    if val is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(val))
    return float(cleaned) if cleaned else None


def _parse_card(card: dict) -> dict | None:
    text = card.get("text", "")
    href = card.get("href", _BASE)

    # Minimum viable: must have a price
    price_m = _PRICE_RE.search(text)
    if not price_m:
        return None
    price = _safe_float(price_m.group(1))
    if not price or price < THRESHOLDS["min_price"] or price > THRESHOLDS["max_price"]:
        return None

    beds = _safe_float((m := _BEDS_RE.search(text)) and m.group(1))
    baths = _safe_float((m := _BATHS_RE.search(text)) and m.group(1))

    sqft_m = _SQFT_RE.search(text)
    sqft = _safe_float(sqft_m.group(1).replace(",", "")) if sqft_m else None

    # Sanity-check sqft (residential homes: 400–10,000 sqft)
    if sqft and not (400 <= sqft <= 10_000):
        sqft = None

    ppqft = round(price / sqft, 2) if price and sqft else None

    # Sanity-check $/sqft (realistic range: $50–$800)
    if ppqft and not (50 <= ppqft <= 800):
        ppqft = None
        sqft = None

    # Address: prefer regex match, else last substantive line
    addr_m = _ADDR_RE.search(text)
    if addr_m:
        address = addr_m.group().strip()
    else:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        skip = {"active", "pending", "sold", "coming soon", "available", "new"}
        address = next(
            (l for l in reversed(lines) if l.lower() not in skip and len(l) > 8),
            lines[0] if lines else "",
        )

    # City / ZIP from address
    zip_m = re.search(r"AR\s+(\d{5})", address, re.I)
    zip_code = zip_m.group(1) if zip_m else ""
    city_m = re.search(r",\s*([A-Za-z ]+),?\s*AR", address)
    city = city_m.group(1).strip() if city_m else "NWA"

    # Build the HomePath URL.
    # Fannie Mae's property-finder works reliably at city level.
    # A full-street-address search returns empty results, so we always
    # use the city-level search which narrows results to that small city.
    # The user can quickly spot the specific property in the short list.
    city_search = f"{city}, AR, USA"
    final_url = (
        "https://homepath.fanniemae.com/property-finder"
        f"?address={urllib.parse.quote(city_search)}"
    )
        )

    return {
        "source": "homepath_fanniemae",
        "address": address[:120],
        "city": city,
        "state": "AR",
        "zip_code": zip_code,
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "price_per_sqft": ppqft,
        "year_built": None,
        "dom": None,
        "listing_type": "fanniemae_reo",
        "description": text[:400],
        "url": final_url,
        "latitude": None,
        "longitude": None,
        "distress_flags": ["foreclosure", "reo", "bank-owned", "fannie mae", "as-is"],
    }


def _extract_cards_js() -> str:
    """JS to extract listing cards with their URLs from HomePath SPA."""
    return """
    () => {
        // HomePath property card selectors (try a cascade)
        const trySelectors = [
            '[class*="PropertyCard"]',
            '[class*="property-card"]',
            '[class*="listing-card"]',
            '[class*="home-card"]',
            'article',
        ];

        let cards = [];
        for (const sel of trySelectors) {
            const els = Array.from(document.querySelectorAll(sel)).filter(el => {
                const t = el.innerText || '';
                // Must look like a property listing (has price + bed/bath)
                return /\\$[\\d,]{4,}/.test(t) && /(bed|bath|sqft|BR)/i.test(t);
            });
            if (els.length > 1) {
                cards = els.map(el => {
                    // Find the most specific listing link:
                    // prefer URLs with /listing, /property, or /detail paths;
                    // fall back to any anchor that isn't the current page.
                    const anchors = Array.from(el.querySelectorAll('a[href]'));
                    const SPECIFIC = ['/listing', '/property', '/detail', '/home/'];
                    const listingAnchor =
                        anchors.find(a => a.href && SPECIFIC.some(p => a.href.includes(p))) ||
                        anchors.find(a => a.href && !a.href.includes('?bounds=') && a.href !== window.location.href) ||
                        anchors[0];

                    let href = listingAnchor ? listingAnchor.href : '';
                    if (href && href.startsWith('/')) {
                        href = window.location.origin + href;
                    }
                    return { text: el.innerText, href: href || window.location.href };
                });
                break;
            }
        }
        return cards;
    }
    """


def _search_one(page, term: str) -> list[dict]:
    """Search HomePath for one term and return parsed listings."""
    # Find and clear the search box
    search_inp = (
        page.query_selector("input[placeholder*='Search by']")
        or page.query_selector("input[placeholder*='Address']")
        or page.query_selector("input[type='search']")
    )
    if not search_inp:
        log.warning("HomePath: search input not found")
        return []

    search_inp.click()
    search_inp.fill("")          # clear existing text
    search_inp.fill(term)
    page.wait_for_timeout(2_000)

    # Click any visible autocomplete suggestion that matches AR
    clicked = False
    for sel in ["[role='option']", "[role='listitem']", "li[class*='suggestion']", "[class*='item']"]:
        opts = page.query_selector_all(sel)
        for opt in opts:
            if opt.is_visible():
                txt = opt.inner_text()
                if "AR" in txt or "Arkansas" in txt or term.split(",")[0].lower() in txt.lower():
                    opt.click()
                    page.wait_for_timeout(3_000)
                    clicked = True
                    break
        if clicked:
            break

    if not clicked:
        search_inp.press("Enter")
        page.wait_for_timeout(4_000)

    # Wait for listings to render
    page.wait_for_timeout(2_000)

    raw_cards = page.evaluate(_extract_cards_js())
    results = []
    for card in (raw_cards or []):
        parsed = _parse_card(card)
        if parsed:
            results.append(parsed)

    log.debug("HomePath '%s': %d cards", term, len(results))
    return results


def fetch_listings() -> list[dict]:
    """Fetch all Fannie Mae REO listings for NWA AR from HomePath."""
    seen: set[str] = set()
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = ctx.new_page()

        try:
            log.info("HomePath: loading site...")
            page.goto(_BASE, wait_until="domcontentloaded", timeout=25_000)
            page.wait_for_timeout(3_000)

            for term in _SEARCH_TERMS:
                log.info("HomePath: searching '%s'", term)
                batch = _search_one(page, term)
                for item in batch:
                    key = item["address"].lower().strip()
                    if key and key not in seen and len(key) > 8:
                        seen.add(key)
                        results.append(item)
                time.sleep(1)

        except Exception as exc:
            log.warning("HomePath scrape error: %s", exc)
        finally:
            browser.close()

    log.info("HomePath: %d unique Fannie Mae REO listings found", len(results))
    return results
