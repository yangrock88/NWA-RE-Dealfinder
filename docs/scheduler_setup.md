# Running and Scheduling

This document covers how to run the tool, what the output looks like, and how to troubleshoot common problems.

---

## Running manually

**Full scrape — fetches fresh data from all sources and opens the report:**
```
uv run python run.py
```

**Single-source debug run:**
```
uv run python run.py --source homepath
uv run python run.py --source craigslist
```

**Rebuild the report from the last cached scrape (no network requests):**
```
uv run python regen.py
```

**Run continuously in the background:**
```
uv run python scheduler.py
```

**Run once and exit:**
```
uv run python scheduler.py --once
```

The `--no-browser` flag on any of the above suppresses auto-opening the report when it finishes.

---

## GitHub Pages auto-publish

After each run the scheduler commits the updated `deals_report.html` and pushes it to the repository. GitHub Pages serves the latest version at:

https://yangrock88.github.io/NWA-RE-Dealfinder/deals_report.html

Each push shows up in the commit history with a timestamp message.

---

## Log file

Every run appends to `data/scheduler.log`. The format is:

```
HH:MM:SS [INFO] Starting scrape run at YYYY-MM-DD HH:MM:SS
HH:MM:SS [INFO] craigslist    1 listings
HH:MM:SS [INFO] homepath      60 listings
HH:MM:SS [INFO] NEW DEALS FOUND: 3
HH:MM:SS [INFO] Run complete in 98.3s | 61 listings | 60 deals
```

The log file grows without bound. If it gets large, delete it — a new one is created on the next run.

---

## Troubleshooting

**HomePath returns 0 listings:**
HomePath occasionally has downtime or makes changes to their page structure. Run the source in isolation to check:
```
uv run python run.py --source homepath
```
If it returns 0, open `https://homepath.fanniemae.com` in a browser to confirm the site is up and the search still works. If the site looks fine but the tool still returns 0, there may be a DOM change that requires updating the card selectors in `sources/homepath.py`.

**Zillow CSV fails:**
When the Zillow CSV fetch fails, the tool falls back to the hardcoded `NWA_MARKET` value in `config.py`. The dashboard will still generate with that value as the $/sqft baseline. Update `NWA_MARKET["area_median_price_per_sqft"]` to a current figure if the Zillow URL has changed.

**Report generates but shows 0 deals:**
Check `data/latest.json` — if it contains 0 listings, the previous run failed silently (usually a HomePath source error). Run `uv run python run.py --source homepath` to verify HomePath is working, then do a full `uv run python run.py` to repopulate the snapshot.
