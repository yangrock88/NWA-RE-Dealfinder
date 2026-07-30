# NWA Real Estate Deal Finder

**Live dashboard:** https://yangrock88.github.io/nwa-re-deals/deals_report.html

A tool for surfacing mispriced, distressed, and non-traditional home sales in the Centerton / Bentonville / Rogers area of Northwest Arkansas. It pulls listings from Fannie Mae HomePath and Craigslist, benchmarks prices against live Zillow market data, scores each listing by deal quality, and writes a self-contained HTML dashboard you can open in any browser.

---

## Quick start

```
# from the project root
uv run python run.py
```

The first run takes about two minutes — mostly HomePath scraping. The HTML report opens automatically when it finishes.

**Regenerate the dashboard from the last cached scrape (faster, no network):**

```
uv run python regen.py
```

**Single-source debug run:**

```
uv run python run.py --source homepath
uv run python run.py --source craigslist
```

---

## What it covers

| Geography | ZIP codes |
|---|---|
| Bentonville | 72712, 72713, 72715, 72716 |
| Centerton | 72719 |
| Rogers | 72758 |

The search also picks up listings in Bella Vista, Pea Ridge, Lowell, Cave Springs, and Gravette because HomePath returns results for those cities when queried.

---

## Dashboard walkthrough

When you open `deals_report.html` you'll see five sections:

**Stats strip** — total listing count, deals flagged, count of listings priced below the market $/sqft threshold, live Zillow median, and new-this-run count. Clicking any stat card filters the listings below it. Clicking the same card again resets the filter.

**Filter bar** — persistent across scrolling. Filters by city, ZIP, beds, baths, price range, sqft range, price-per-sqft range, deal score floor, and sale type. All filters combine with AND logic; results update immediately.

**Deal cards** — sorted by deal score, highest first. Each card shows the address, price, bed/bath/sqft/$/sqft, a "below market" badge when applicable, tags for the sale type, and two action buttons:
- *View on HomePath* — opens HomePath pre-searched to that specific address
- *Map* — opens Google Maps centered on the property

**All Scraped Listings** — full table of every listing pulled, including ones that didn't score as deals. Useful for scanning raw data.

**Manual Research** — direct links to HUD Homestore, Auction.com, Hubzu, Redfin, Zillow, the Benton County Circuit Clerk, and the county assessor. These sites block automated scraping; you browse them manually.

---

## Deal score explained

Scores run from 0 to roughly 90. Three color tiers on each card:

| Color | Score range | What it means |
|---|---|---|
| Green | 60 and above | Meaningful discount below market $/sqft |
| Yellow | 42 – 59 | At or near market, but a distressed sale type |
| Red | Below 42 | Above market price or minimal deal signal |

The score combines: price discount vs. Zillow median (up to 45 points), listing type (25 points for Fannie Mae REO / foreclosure), days on market (up to 15 points), and distress keyword flags (2 points each). Details in `docs/scoring.md`.

---

## Updating market data

The Zillow baseline (currently ~$217/sqft for NWA) is pulled fresh from Zillow's public research CSV on every scheduled run. If you want to override it manually — for instance if you have recent MLS comps — edit `config.py`:

```python
NWA_MARKET = {
    "area_median_price_per_sqft": 217,  # update this
    "area_median_home_value": 455_000,
    "area_median_sqft": 2_100,
    "data_date": "2025-Q1",
}
```

The hardcoded value is only used as a fallback when the Zillow CSV fetch fails.

---

## Running on a schedule

Run once and open a fresh report:

```
uv run python run.py
```

Run continuously in the background:

```
uv run python scheduler.py
```

Rebuild the report instantly from the last cached scrape (no network):

```
uv run python regen.py
```

Logs are written to `data/scheduler.log`.

---

## Project layout

```
re_deals/
├── run.py              Entry point — one scrape cycle, opens report
├── scheduler.py        Background scrape loop and scheduling
├── regen.py            Rebuild report from last snapshot without re-scraping
├── config.py           Search area, score thresholds, market baseline
├── analysis.py         Deal scoring logic
├── report.py           HTML dashboard generator
├── notifier.py         Windows desktop notifications
├── sources/
│   ├── homepath.py     Fannie Mae HomePath scraper (Playwright)
│   ├── zillow_csv.py   Zillow ZHVI public CSV parser
│   ├── craigslist.py   Craigslist Fort Smith FSBO scraper
│   ├── hud.py          HUD stub (links to manual search)
│   └── auction.py      Auction.com best-effort scraper
├── docs/               Extended documentation
└── data/               Runtime data (gitignored)
    ├── latest.json     Last scrape snapshot
    └── scheduler.log   Run history
```

---

## Dependencies

Managed by [uv](https://docs.astral.sh/uv/). Run `uv sync` to install.

| Package | Purpose |
|---|---|
| `playwright` | Headless Chromium for HomePath |
| `requests` | HTTP for Zillow CSV and Craigslist |
| `beautifulsoup4` + `lxml` | HTML parsing |

Python 3.11 or later required.
