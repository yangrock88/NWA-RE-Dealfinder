# Architecture

This is a local Python application. There is no server, no cloud hosting, and no database. Everything runs on your Windows machine and produces a static HTML file.

---

## Data flow

```
Zillow Research CSV ──────────────────────────────┐
                                                   ▼
Craigslist Fort Smith ──► raw listing dicts ──► analysis.py ──► report.py ──► deals_report.html
                                                   ▲
HomePath (Playwright) ─────────────────────────────┘

scheduler.py orchestrates everything above.
data/latest.json stores the previous run for new-deal comparison.
```

---

## Module responsibilities

**`run.py`**
Entry point for a one-shot run. Parses command-line arguments and delegates to `scheduler.run_once()`.

**`scheduler.py`**
The main orchestrator. On each cycle it:
1. Fetches the Zillow market data
2. Calls each source module's `fetch_listings()` function
3. Deduplicates results by address
4. Calls `analysis.analyze()` to score listings
5. If Zillow data came back, rescores everything with the live median
6. Loads `data/latest.json` to find new listings
7. Fires desktop notifications if new deals appeared
8. Writes a new `data/latest.json`
9. Calls `report.generate()` to write the HTML file

**`analysis.py`**
Applies `score_listing()` to each listing dict. Returns a results dict with `deals`, `regular`, and `all_listings` lists sorted by score.

**`report.py`**
Reads the results dict and produces a self-contained HTML file with embedded CSS and JavaScript. All filtering is client-side; the HTML file works offline with no server.

**`regen.py`**
Loads `data/latest.json`, applies URL fixes, rescores with the saved median, and calls `report.generate()`. No network requests. Useful when the data is fresh but you want to change the report layout.

**`notifier.py`**
Sends Windows toast notifications using PowerShell's Windows Runtime APIs. Also calls `winsound.Beep()` for an audible alert when new deals are found.

**`sources/homepath.py`**
Uses Playwright to open `homepath.fanniemae.com`, search each configured city, and extract listing card data via JavaScript evaluation. Constructs a HomePath address-search URL for each listing so the dashboard link is pre-filled.

**`sources/zillow_csv.py`**
Streams Zillow's ZHVI CSV (the tier 0.33–0.67, single-family/condo, smoothed seasonally adjusted file). Reads line by line, discards rows not in the target ZIP list, and returns a dict of `{zip: median_value}`.

**`sources/craigslist.py`**
Fetches HTML from Fort Smith Craigslist's for-sale-by-owner category using requests. Parses `li.cl-static-search-result` elements. For each item, fetches the detail page to get beds/baths/sqft and checks the JSON-LD address block to confirm the listing is in Arkansas.

**`sources/hud.py`**
Returns an empty list and logs the manual search URL. HUD's site renders properties as Google Maps pins and does not expose a scrapeable API.

**`sources/auction.py`**
Attempts to parse `__NEXT_DATA__` JSON from Auction.com's search page. Returns 0 results in most runs because Auction.com renders listings client-side through React state not present in initial HTML.

---

## Why Playwright instead of requests for HomePath

HomePath is a React single-page application. The initial HTML response contains only the shell (header, navigation, search box, an empty div). Property listings are fetched and rendered by JavaScript after the page loads. Plain HTTP requests get the empty shell; Playwright runs a real browser that executes the JavaScript and returns the fully rendered DOM.

The downside is speed: Playwright takes about 8–10 seconds per city search. Eight cities means roughly 80 seconds just for HomePath.

---

## Why not Redfin or Zillow

Both sites use enterprise bot-detection services (Kasada / DataDome / PerimeterX). These systems fingerprint browsers at the TLS and behavioral level — they catch headless Chromium even when it presents as a real Chrome browser. Several approaches were tested:

- Plain `requests` → 403 from CloudFront immediately
- Playwright with real Chrome user-agent → 403 from the bot-detection layer
- `page.evaluate(fetch(...))` from within a loaded Redfin page → 403 with a different request ID

HomePath works because Fannie Mae does not use enterprise bot protection on their public property search.

---

## Report file size

The generated `deals_report.html` is large (~200 KB) because it contains every listing record as inline HTML with data attributes. This is intentional — the file is entirely self-contained. You can email it, save it to a network share, or open it offline. No server, no external dependencies.
