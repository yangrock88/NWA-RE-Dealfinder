"""
Central config for the Centerton / Bentonville AR deal-finder.
Tweak THRESHOLDS to tighten or loosen the "underpriced" filter.
"""

# ── Search area ────────────────────────────────────────────────────────────────
AREA = {
    "name": "Centerton / Bentonville, AR",
    "city_center": (36.3728, -94.2088),   # Bentonville lat/lng
    "bbox": {                              # bounding box for polygon queries
        "lat_min": 36.28,
        "lat_max": 36.51,
        "lng_min": -94.38,
        "lng_max": -94.05,
    },
    # ZIP codes covering Centerton (72719) + Bentonville (72712-18) + Rogers (72758)
    "zip_codes": ["72712", "72713", "72715", "72716", "72719", "72758"],
    "craigslist_subdomain": "nwarkansas",
    "state": "AR",
    "state_code": "AR",
    "county": "Benton",
    "radius_miles": 20,
}

# ── NWA area market context ──────────────────────────────────────────────────────
# Based on 2024-2025 Bentonville/Rogers/Centerton market data.
# Update these if you have fresher data (Redfin, Zillow, county assessor).
# Source reference: Northwest AR MLS / Benton County Assessor
NWA_MARKET = {
    "area_median_home_value": 415_000,       # ~median list price in area
    "area_median_price_per_sqft": 190,       # $/sqft for median-priced home
    "area_median_sqft": 2_200,               # median home size
    "notes": "Bentonville/Centerton/Rogers AR - hot market (Walmart HQ effect)",
    "data_date": "2025-Q1",
}

# ── Deal thresholds ────────────────────────────────────────────────────────────────
THRESHOLDS = {
    # Flag if $/sqft is below this fraction of the area median
    "underpriced_ratio": 0.82,
    # Flag if days on market exceeds this
    "dom_high": 45,
    # Minimum valid $/sqft (filter out bad data)
    "min_price_per_sqft": 30,
    # Skip listings above this price (adjust to taste)
    "max_price": 750_000,
    # Skip listings below this price (no $1 placeholders)
    "min_price": 40_000,
}

# ── Keywords that signal distressed / non-traditional sales ───────────────────
DISTRESS_KEYWORDS = [
    "foreclosure", "bank owned", "bank-owned", "reo", "real estate owned",
    "short sale", "shortsale", "as-is", "as is", "estate sale", "probate",
    "motivated seller", "must sell", "price reduced", "price drop",
    "cash only", "fixer", "fixer upper", "fixer-upper", "investor special",
    "handyman", "needs work", "tlc", "auction", "hud home", "hud-home",
    "court ordered", "court-ordered", "bankruptcy", "distressed",
    "pre-foreclosure", "pre foreclosure", "notice of default",
    "lis pendens", "coming soon", "off market",
]

# ── HTTP headers (mimic a real browser) ───────────────────────────────────────
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
