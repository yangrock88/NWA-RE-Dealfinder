"""
Craigslist scraper for NW Arkansas real estate.
Fort Smith CL (fortsmith.craigslist.org) is the closest active market
to Bentonville/Rogers/Centerton. We search several AR-specific queries,
verify each listing's state via JSON-LD, and fetch detail pages for
beds/baths/sqft where available.
"""
import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import AREA, BROWSER_HEADERS, DISTRESS_KEYWORDS, THRESHOLDS

log = logging.getLogger(__name__)

_BASE = "https://fortsmith.craigslist.org"
_HEADERS = {**BROWSER_HEADERS, "Referer": _BASE}

# AR cities that indicate a NWA listing
_NWA_CITIES = frozenset({
    "bentonville", "centerton", "rogers", "bella vista", "lowell",
    "cave springs", "pea ridge", "gravette", "highfill", "anderson",
    "benton county", "nwa", "northwest arkansas", "springdale",
    "fayetteville", "siloam springs", "farmington",
})

# Search queries targeting the Bentonville/Centerton area
_QUERIES = [
    "Bentonville AR house",
    "Centerton AR house",
    "Rogers AR for sale",
    "Bella Vista AR house",
    "Benton County house for sale",
    "NWA house for sale",
]

_PRICE_RE = re.compile(r"\$([\d,]+)")
_SQFT_RE = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet)", re.I)
_BEDS_RE = re.compile(r"(\d)\s*(?:BR|bed|bedroom)", re.I)
_BATHS_RE = re.compile(r"(\d(?:\.\d)?)\s*(?:Ba|bath|bathroom)", re.I)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    if val is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(val))
    return float(cleaned) if cleaned else None


def _detect_distress(text: str) -> list[str]:
    lower = text.lower()
    return [kw for kw in DISTRESS_KEYWORDS if kw in lower]


def _is_ar(json_lds: list[dict], title: str) -> bool:
    """Return True only if listing is in Arkansas (not another Fayetteville, etc.)."""
    for jl in json_lds:
        addr = jl.get("address") or {}
        if isinstance(addr, dict):
            region = (addr.get("addressRegion") or "").upper()
            if region == "AR":
                return True
            if region and region != "":
                return False   # explicitly a different state
    # Fallback: title/description contains NWA city name
    lower = title.lower()
    return any(city in lower for city in _NWA_CITIES)


def _fetch_detail(url: str) -> dict:
    """Fetch CL listing detail page. Returns beds/baths/sqft/json_lds."""
    out = {"beds": None, "baths": None, "sqft": None, "price": None, "json_lds": []}
    try:
        r = requests.get(url, headers=_HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "lxml")

        # JSON-LD for structured address/price data
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                out["json_lds"].append(json.loads(script.string or ""))
            except json.JSONDecodeError:
                pass

        # Price
        price_tag = soup.select_one(".price") or soup.select_one("[class*='price']")
        if price_tag:
            pm = _PRICE_RE.search(price_tag.get_text())
            if pm:
                out["price"] = _safe_float(pm.group(1))

        # Beds / baths / sqft from attrgroup
        attrs = soup.select(".attrgroup")
        full_attr_text = " ".join(a.get_text(" ", strip=True) for a in attrs)
        body_text = soup.get_text(" ", strip=True)[:3000]

        for label, pat, key in [
            ("beds", _BEDS_RE, "beds"),
            ("baths", _BATHS_RE, "baths"),
            ("sqft", _SQFT_RE, "sqft"),
        ]:
            m = pat.search(full_attr_text) or pat.search(body_text)
            if m:
                val = _safe_float(m.group(1).replace(",", ""))
                out[key] = val

    except Exception as exc:
        log.debug("CL detail error for %s: %s", url, exc)
    return out


def _scrape_query(query: str) -> list[dict]:
    """Scrape Fort Smith CL with one search query. Returns AR-only listings."""
    params = {"query": query, "sort": "date"}
    try:
        r = requests.get(
            f"{_BASE}/search/reo",
            params=params,
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
    except Exception as exc:
        log.warning("CL query '%s' failed: %s", query, exc)
        return []

    soup = BeautifulSoup(r.text, "lxml")
    items = soup.select("li.cl-static-search-result")

    results = []
    for item in items:
        try:
            title = item.get("title", "").strip()
            a_tag = item.find("a")
            if not a_tag:
                continue
            url = a_tag.get("href", "")
            if not url.startswith("http"):
                url = _BASE + url

            price_el = item.select_one(".price")
            list_price = None
            if price_el:
                pm = _PRICE_RE.search(price_el.get_text())
                if pm:
                    list_price = _safe_float(pm.group(1))

            # Fetch detail to verify AR state + get property info
            detail = _fetch_detail(url)
            if not _is_ar(detail["json_lds"], title):
                log.debug("CL: non-AR listing skipped: %s", title[:50])
                continue

            price = detail.get("price") or list_price
            if price and (price < THRESHOLDS["min_price"] or price > THRESHOLDS["max_price"]):
                continue

            sqft = detail.get("sqft")
            ppqft = round(price / sqft, 2) if price and sqft and sqft > 0 else None

            flags = _detect_distress(f"{title} {query}")
            listing_type = "distressed" if flags else "fsbo"

            results.append({
                "source": "craigslist_fsbo",
                "address": "",
                "city": "NWA (Rogers/Bentonville area)",
                "state": "AR",
                "zip_code": "",
                "price": price,
                "beds": detail.get("beds"),
                "baths": detail.get("baths"),
                "sqft": sqft,
                "price_per_sqft": ppqft,
                "year_built": None,
                "dom": None,
                "listing_type": listing_type,
                "description": title,
                "url": url,
                "latitude": None,
                "longitude": None,
                "distress_flags": flags,
            })
            time.sleep(0.4)   # polite delay between detail fetches

        except Exception as exc:
            log.debug("CL item error: %s", exc)

    log.info("CL '%s': %d AR listings", query[:40], len(results))
    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_listings() -> list[dict]:
    """Fetch NWA AR real estate listings from Craigslist Fort Smith."""
    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in _QUERIES:
        for listing in _scrape_query(query):
            url = listing["url"]
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(listing)
        time.sleep(2)

    log.info("Craigslist total: %d unique NWA AR listings", len(results))
    return results
