"""
Deal analysis — compares active listings to the area median $/sqft
(Zillow ZHVI market median, sold comps, or the config fallback) and
flags distressed properties.
"""
import logging
import statistics

from config import DISTRESS_KEYWORDS, NWA_MARKET, THRESHOLDS

log = logging.getLogger(__name__)


# ── Median computation ─────────────────────────────────────────────────────────

def compute_area_median(sold_comps: list[dict]) -> float:
    """
    Return median $/sqft.  If we have enough sold comps, compute from them.
    Otherwise fall back to the hardcoded NWA market estimate in config.py
    (which the user can update with fresher data at any time).
    """
    values = [
        c["price_per_sqft"]
        for c in sold_comps
        if c.get("price_per_sqft")
        and c["price_per_sqft"] >= THRESHOLDS["min_price_per_sqft"]
        and c["price_per_sqft"] < 1_000   # filter obvious bad data
    ]
    if len(values) >= 5:
        median = statistics.median(values)
        log.info(
            "Area median $/sqft: $%.2f  (n=%d live comps, range $%.0f-$%.0f)",
            median, len(values), min(values), max(values),
        )
        return median

    fallback = NWA_MARKET["area_median_price_per_sqft"]
    log.info(
        "Area median $/sqft: $%.2f  (hardcoded NWA estimate – %s; update "
        "NWA_MARKET in config.py with fresher data)",
        fallback, NWA_MARKET["data_date"],
    )
    return float(fallback)


# ── Distress detection ─────────────────────────────────────────────────────────

def _detect_distress_in_text(text: str) -> list[str]:
    lower = text.lower()
    return [kw for kw in DISTRESS_KEYWORDS if kw in lower]


def _enrich_distress_flags(listing: dict) -> list[str]:
    """Union existing flags with anything found in the text fields."""
    existing = set(listing.get("distress_flags") or [])
    searchable = " ".join([
        listing.get("description", ""),
        listing.get("sale_type_raw", ""),
        listing.get("listing_type", ""),
    ])
    detected = set(_detect_distress_in_text(searchable))
    # Also flag based on listing_type field
    lt = listing.get("listing_type", "")
    if lt in ("foreclosure", "hud_foreclosure", "fanniemae_reo",
               "foreclosure_auction", "short_sale", "distressed", "reo"):
        detected.add(lt.replace("_", " "))
    return sorted(existing | detected)


# ── Scoring ────────────────────────────────────────────────────────────────────

_DISTRESSED_TYPES = frozenset({
    "foreclosure", "hud_foreclosure", "fanniemae_reo",
    "foreclosure_auction", "short_sale", "distressed", "reo",
})


def score_listing(listing: dict, area_median: float | None) -> dict:
    """
    Annotate a listing with:
      discount_pct   – % below area median $/sqft (positive = below median)
      deal_score     – composite 0-100+ score; higher = better potential deal
      is_deal        – True when score > 0 or listing type is distressed
      distress_flags – enriched keyword list
    """
    listing = dict(listing)   # never mutate the caller's dict

    listing["distress_flags"] = _enrich_distress_flags(listing)

    ppqft = listing.get("price_per_sqft")
    discount_pct: float | None = None

    if ppqft and area_median:
        discount_pct = round((1 - ppqft / area_median) * 100, 1)
        if ppqft < area_median * THRESHOLDS["underpriced_ratio"]:
            if "below-median-psf" not in listing["distress_flags"]:
                listing["distress_flags"].append("below-median-psf")

    dom = listing.get("dom")
    if dom and dom >= THRESHOLDS["dom_high"]:
        if "high-dom" not in listing["distress_flags"]:
            listing["distress_flags"].append("high-dom")

    listing["discount_pct"] = discount_pct

    # Score components
    score = 0.0
    if discount_pct and discount_pct > 0:
        score += min(discount_pct * 1.5, 45)   # up to 45pts for price discount
    if dom:
        score += min(dom / 10, 15)              # up to 15pts for stale listing
    if listing.get("listing_type") in _DISTRESSED_TYPES:
        score += 25
    if listing.get("listing_type") == "hud_foreclosure":
        score += 5                              # HUD = extra motivated seller
    score += len(listing["distress_flags"]) * 2

    listing["deal_score"] = round(score, 1)
    listing["is_deal"] = bool(
        listing["distress_flags"]
        or listing.get("listing_type") in _DISTRESSED_TYPES
    )
    return listing


# ── Main entry point ───────────────────────────────────────────────────────────

def analyze(active_listings: list[dict], sold_comps: list[dict],
            median_override: float | None = None) -> dict:
    """
    Run the full analysis pipeline.
    Returns a dict ready to be consumed by report.py.

    Pass median_override (e.g. the live Zillow ZHVI median) to skip
    comp-based median computation and score every listing once against
    that value instead.
    """
    area_median = (
        median_override if median_override and median_override > 0
        else compute_area_median(sold_comps)
    )
    scored = [score_listing(l, area_median) for l in active_listings]
    scored.sort(key=lambda x: x["deal_score"], reverse=True)

    deals = [l for l in scored if l["is_deal"]]
    regular = [l for l in scored if not l["is_deal"]]

    log.info(
        "Analysis complete – %d total listings | %d flagged as deals | median $%.0f/sqft",
        len(scored), len(deals), area_median or 0,
    )
    return {
        "area_median_ppqft": area_median,
        "total_active": len(scored),
        "total_sold_comps": len(sold_comps),
        "deals": deals,
        "regular": regular,
        "all_listings": scored,
    }
