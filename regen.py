"""
Quick regeneration from the last saved snapshot — no re-scraping.
Applies all URL fixes and uses the area median from the snapshot.

Usage: uv run python regen.py
"""
import json, logging, subprocess, sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("regen")

snap_path = Path("data/latest.json")
if not snap_path.exists():
    print("No snapshot — run: uv run python run.py first")
    sys.exit(1)

snap     = json.loads(snap_path.read_text(encoding="utf-8"))
listings = snap.get("listings", [])
median   = snap.get("area_median_ppqft")   # use the live Zillow median from last run
log.info("Loaded %d listings | median $%.0f/sqft", len(listings), median or 0)

# Fix HomePath URLs to city-level search (works reliably)
BASE = "https://homepath.fanniemae.com"
def fix_url(lst: dict) -> dict:
    """Re-apply the current _hp_url logic to cached listings."""
    # Just import and use the same function from report.py
    from report import _hp_url
    lst = dict(lst)
    lst["url"] = _hp_url(lst)
    return lst

fixed = [fix_url(l) for l in listings]

# Re-score with correct median
from analysis import score_listing
rescored = [score_listing(l, median) for l in fixed]
rescored.sort(key=lambda x: x["deal_score"], reverse=True)

results = {
    "area_median_ppqft": median,
    "total_active":      len(rescored),
    "total_sold_comps":  0,
    "deals":             [l for l in rescored if l["is_deal"]],
    "regular":           [l for l in rescored if not l["is_deal"]],
    "all_listings":      rescored,
}

from report import generate
out = generate(results, "deals_report.html", new_addresses=set())
log.info("Done — %d deals. Opening...", len(results["deals"]))
subprocess.run(["cmd", "/c", "start", "", str(out.resolve())], check=False)
