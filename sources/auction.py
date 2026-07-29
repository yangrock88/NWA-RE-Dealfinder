"""
Auction.com and Hubzu REO scraper (best-effort).
Both sites are React SPAs so initial HTML often lacks full listing data.
We try to pull JSON from embedded script tags; log a warning on failure.
"""
import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import AREA, BROWSER_HEADERS, THRESHOLDS

log = logging.getLogger(__name__)

_HEADERS = {**BROWSER_HEADERS, "Referer": "https://www.auction.com/"}
_SAFE = re.compile(r"[\d.]+")


def _safe_float(val) -> float | None:
    if val is None:
        return None
    m = _SAFE.search(str(val).replace(",", ""))
    return float(m.group()) if m else None


def _extract_next_data(html: str) -> list[dict]:
    """Pull listings from Next.js __NEXT_DATA__ JSON blob."""
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    # Walk the deeply nested Next.js page props to find an array of listings
    def _walk(node, depth=0):
        if depth > 8 or not isinstance(node, (dict, list)):
            return []
        if isinstance(node, list) and len(node) > 0 and isinstance(node[0], dict):
            if any(k in node[0] for k in ("price", "listPrice", "address", "streetAddress")):
                return node
        results = []
        children = node.values() if isinstance(node, dict) else node
        for child in children:
            results.extend(_walk(child, depth + 1))
        return results

    return _walk(data)


def _normalize_auction_item(item: dict, source_tag: str) -> dict | None:
    """Map a raw auction JSON item to the standard Listing shape."""
    price = _safe_float(
        item.get("listPrice") or item.get("startingBid") or item.get("price") or 0
    )
    if not price or price < THRESHOLDS["min_price"] or price > THRESHOLDS["max_price"]:
        return None

    sqft = _safe_float(item.get("squareFeet") or item.get("sqft") or 0)
    ppqft = round(price / sqft, 2) if price and sqft and sqft > 0 else None

    address = (
        item.get("address") or item.get("streetAddress") or item.get("street") or ""
    )
    city = item.get("city") or "Bentonville"
    url = item.get("url") or item.get("link") or item.get("detailUrl") or ""
    if url and not url.startswith("http"):
        url = "https://www.auction.com" + url

    return {
        "source": source_tag,
        "address": str(address).strip(),
        "city": str(city).strip(),
        "state": "AR",
        "zip_code": str(item.get("zip") or item.get("zipCode") or "").strip(),
        "price": price,
        "beds": _safe_float(item.get("bedrooms") or item.get("beds")),
        "baths": _safe_float(item.get("bathrooms") or item.get("baths")),
        "sqft": sqft or None,
        "price_per_sqft": ppqft,
        "year_built": None,
        "dom": None,
        "listing_type": "foreclosure_auction",
        "description": str(item.get("description") or "Foreclosure / REO auction property"),
        "url": url,
        "latitude": _safe_float(item.get("lat") or item.get("latitude")),
        "longitude": _safe_float(item.get("lng") or item.get("longitude")),
        "distress_flags": ["foreclosure", "auction", "bank-owned"],
    }


def _scrape_site(url: str, source_tag: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=25)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("%s fetch failed: %s", source_tag, exc)
        return []

    raw_items = _extract_next_data(resp.text)
    if not raw_items:
        # Fallback: look for any JSON array in <script> tags
        soup = BeautifulSoup(resp.text, "lxml")
        for script in soup.find_all("script", type="application/json"):
            try:
                blob = json.loads(script.string or "")
                if isinstance(blob, list) and blob and "price" in str(blob[0]):
                    raw_items = blob
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    results = []
    for item in raw_items:
        listing = _normalize_auction_item(item, source_tag)
        if listing:
            results.append(listing)

    log.info("%s: %d listings found", source_tag, len(results))
    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_listings() -> list[dict]:
    """Fetch REO/auction foreclosure listings from Auction.com."""
    lat, lng = AREA["city_center"]
    r = AREA["radius_miles"]
    url = (
        f"https://www.auction.com/reo/"
        f"?location=Bentonville%2C+AR&radius={r}&state=AR"
    )
    results = _scrape_site(url, "auction_com")
    time.sleep(2)
    return results
