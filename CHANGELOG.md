# Changelog

## Unreleased

### Added
- Google Maps button on every listing card (direct link to property address on the map)
- Toggle behavior on stat card filters — clicking an active filter a second time resets it
- Score color-coding on listing cards: green (≥ 60), yellow (42–59), red (< 42), consistent in both the card grid and the detail table
- HomePath link now pre-fills the exact street address rather than just the city, narrowing search results to the specific block

### Changed
- Removed colored left border from listing cards — cleaner card design without the visual noise
- Removed the Refresh link from the dashboard header
- HomePath URL construction now strips extra spaces before commas in addresses (artifact from the ADDR_RE parser) to prevent empty search results

### Fixed
- `regen.py` now delegates URL construction to `report._hp_url()` instead of duplicating the logic

---

## v1.2 — Dashboard visual redesign

### Changed
- Complete CSS overhaul to a single-accent design system: one indigo accent (`#4F46E5`), one emerald signal color (`#059669`) for below-market listings, everything else neutral gray
- Removed the rainbow of per-category badge colors (previously: red for foreclosure, blue for REO, purple for HUD, orange for short sale, green for PSF)
- All listing tags now render in a uniform neutral gray style — category is communicated by text, not color
- Stat cards no longer use different text colors per metric
- Filter bar styling simplified

---

## v1.1 — Filter panel and auto-update

### Added
- Client-side filter panel with 9 filter dimensions: city, ZIP, beds, baths, price range, sqft range, $/sqft range, deal score floor, sale type
- Stat card quick-filters with active state highlight
- "New This Run" detection — compares current listings to `data/latest.json`
- Windows toast notifications for new deals
- Windows Task Scheduler integration (`scheduler.py --register`)
- `regen.py` for instant report rebuild from cached data
- Zillow ZHVI public CSV as live market median source (~$217/sqft for NWA)

### Changed
- HomePath scraper now searches all 8 NWA cities instead of just Bentonville and Rogers, increasing typical yield from 6 to 60+ listings per run
- Score thresholds recalibrated using live Zillow data instead of hardcoded $190/sqft estimate

---

## v1.0 — Initial build

### Added
- HomePath (Fannie Mae REO) scraper using Playwright
- Craigslist Fort Smith FSBO scraper
- HUD Homestore stub with manual search link
- Deal scoring algorithm (price discount + listing type + DOM + distress keywords)
- HTML dashboard with card grid and data table
- Manual research link section (HUD, Auction.com, Hubzu, Redfin, Zillow, county records)
- `pyproject.toml` with uv-managed dependencies
