# Data Sources

This document describes each source the tool pulls from, what it provides, how reliable it is, and what to do when it fails.

---

## HomePath — Fannie Mae REO

**URL:** https://homepath.fanniemae.com  
**Access method:** Playwright headless browser  
**Refresh cadence:** Every scheduled run  
**Coverage:** All NWA cities in the configured search list

HomePath lists homes Fannie Mae acquired through foreclosure. These are sold as-is, with no seller repairs, at prices set by Fannie Mae's own appraisal. Prices are often at or below market, and the non-traditional sale process (sealed bid, online offer submission) can create buying opportunities.

The site is a React single-page application. Automation uses Playwright to load the page in a real Chromium browser, type each city name into the search bar, wait for results to render, and extract property cards from the DOM. This approach is slow (roughly 8–10 seconds per city) but reliable.

**Search queries run (in order):**
Bentonville, Rogers, Centerton, Bella Vista, Cave Springs, Lowell, Pea Ridge, Gravette

**Fields captured:**
Address, city, ZIP, price, beds, baths, sqft, $/sqft, listing status

**Known limitations:**
- The site occasionally renders cards without sqft data. When that happens, $/sqft is left null and the listing appears in results without a market comparison.
- Duplicate prevention is done by normalized address string. Occasionally two cards for the same property slip through if the address format differs slightly between city searches.
- HomePath does not expose Days on Market in the card view.

**Link behavior:**
Clicking "View on HomePath" from the dashboard opens a pre-filtered search for the property's specific street address (e.g., `676 Brimwood Street, Centerton, AR 72719`). Results should be narrowed to one or two matching listings.

---

## Zillow Research CSV — Market Baseline

**URL:** https://files.zillowstatic.com/research/public_csvs/zhvi/  
**Access method:** HTTP streaming — no authentication required  
**Refresh cadence:** Every scheduled run  
**Coverage:** All ZIP codes in `config.AREA["zip_codes"]`

Zillow publishes monthly ZHVI (Zillow Home Value Index) data as public CSV files. The file used here is the single-family / condo tier (33rd–67th percentile), smoothed and seasonally adjusted. It covers every ZIP code in the US, so the file is large (~120 MB). The scraper streams it line by line and stops reading as soon as all target ZIPs are found, keeping memory use low.

The ZHVI value for each ZIP is the estimated median home sale price for that month. Dividing by the configured median sqft estimate (`NWA_MARKET["area_median_sqft"]`, default 2,100) yields a $/sqft baseline. That baseline drives the "below market" flag and the price-discount portion of the deal score.

**Current NWA values (as of last update):**

| ZIP | Area | Median Home Value |
|---|---|---|
| 72712 | Bentonville | ~$521,000 |
| 72713 | Bentonville | ~$456,000 |
| 72715 | Bentonville | ~$364,000 |
| 72719 | Centerton | ~$358,000 |
| 72758 | Rogers | ~$456,000 |

The median across these ZIPs (~$456,000 ÷ 2,100 sqft) yields the ~$217/sqft figure used in the dashboard.

**Known limitations:**
- ZHVI reflects the middle tier of homes. It is not the same as median $/sqft of actual sales. Treat it as a ballpark, not a precise appraisal benchmark.
- ZIP 72716 (Bentonville) does not appear in Zillow's ZHVI dataset and is skipped. If you need it, use a neighboring ZIP as a proxy.
- If the CSV fetch fails (network timeout, Zillow changes the URL), the tool falls back to the hardcoded `NWA_MARKET` value in `config.py`.

---

## Craigslist Fort Smith — FSBO Listings

**URL:** https://fortsmith.craigslist.org  
**Access method:** HTTP + BeautifulSoup HTML parsing  
**Refresh cadence:** Every scheduled run  
**Coverage:** NW Arkansas listings posted to Fort Smith CL

NW Arkansas (Fayetteville, Bentonville, Rogers, Springdale) does not have its own Craigslist subdomain. The closest active market is Fort Smith, roughly 70 miles south. Some Bentonville / Rogers sellers post there, but coverage is thin.

Each search result page is fetched as plain HTML. Property items use the `li.cl-static-search-result` selector. For each listing, a detail page is fetched to extract beds, baths, sqft, and the JSON-LD address block. The JSON-LD `addressRegion` field is checked to confirm the listing is in Arkansas before including it.

**Search queries run:**
"Bentonville AR house", "Centerton AR house", "Rogers AR for sale", "Bella Vista AR house", "Benton County house for sale", "NWA house for sale"

**Known limitations:**
- Fort Smith CL serves a wide region that overlaps with Arkansas and Oklahoma. Non-AR listings sometimes appear; the JSON-LD filter catches most but not all.
- Craigslist does not show Days on Market; all CL listings show DOM as null.
- Volume is low. Most weeks you'll see 0–2 verified NWA listings. That's not a bug — it reflects actual posting behavior.

---

## HUD Homestore — FHA Foreclosures (Manual)

**URL:** https://www.hudhomestore.gov  
**Access method:** Manual browser — not automated  

HUD Homestore lists homes the Department of Housing and Urban Development acquired after FHA loan defaults. These are sold at appraised value with specific bid rules (owner-occupant priority period, etc.).

The site renders property locations as pins on a Google Maps interface. Property data is loaded asynchronously through a map tile system that is not practical to scrape programmatically. The tool's HUD source is a stub that logs the manual search URL; all actual browsing is done by hand.

To search: go to https://www.hudhomestore.gov, type a ZIP code (72712, 72719, or 72758) into the search field, and press Enter. Properties appear as map pins. NWA is a strong market, so HUD inventory here is typically light.

---

## Auction.com — Foreclosure Auctions (Best-effort)

**URL:** https://www.auction.com  
**Access method:** JSON extraction from page source  
**Status:** Best-effort; often returns 0 results  

Auction.com lists bank-owned properties available for online auction, including REO (bank-owned after foreclosure) and pre-foreclosure homes. The tool attempts to extract listing JSON from the page's `__NEXT_DATA__` script block, which Next.js applications often embed.

In practice, Auction.com renders listings client-side through React state that isn't present in the initial HTML. The scraper returns 0 results in most runs. The source is kept because the data structure changes occasionally and it may start working without code changes.

For manual browsing: https://www.auction.com/reo/?state=AR&location=Bentonville,+AR&radius=25
