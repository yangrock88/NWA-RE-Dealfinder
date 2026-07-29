"""
HUD Homestore stub.
HUD's site renders all listings as Google Maps pins via PropertyShark —
no clean API or parseable HTML is available without a full browser
automation session that's cost-prohibitive.

What to do manually:
  1. Go to https://www.hudhomestore.gov/Home/Index.aspx
  2. Type "72712" or "Bentonville AR" in the City/State/ZIP box
  3. Hit Enter — properties appear as map pins
  4. Click each pin to see case number, address, price, and bidding status

HUD homes in NWA are rare (hot market) but when available they're priced
by HUD appraisal and sold via online bid at hudhomestore.gov.
"""
import logging

log = logging.getLogger(__name__)

HUD_MANUAL_URL = "https://www.hudhomestore.gov/Home/Index.aspx"


def fetch_listings() -> list[dict]:
    """Returns empty list; logs the manual-research URL."""
    log.info(
        "HUD: automated scraping unavailable (map-pin interface). "
        "Manual search: %s",
        HUD_MANUAL_URL,
    )
    return []
