# Data Dictionary

Every listing record produced by the scrapers shares the same schema. This document defines each field, its type, where it comes from, and any caveats.

Records are stored as plain Python dicts during a run and serialized to JSON in `data/latest.json` at the end of each cycle.

---

## Core listing fields

| Field | Type | Description |
|---|---|---|
| `source` | string | Which scraper produced this record. Values: `homepath_fanniemae`, `craigslist_fsbo`, `auction_com` |
| `address` | string | Street address as parsed from the listing. May include city/state/ZIP when captured as a single string from the source (HomePath). |
| `city` | string | City name extracted from the address or listing metadata. |
| `state` | string | Two-letter state code. Always `AR` for this project. |
| `zip_code` | string | Five-digit ZIP code. Empty string when not available (some CL listings). |
| `price` | float or null | Listed price in US dollars. Null if no price was detected. |
| `beds` | float or null | Number of bedrooms. Float because some sources report half-bedrooms (e.g., 3.5). Null if not available. |
| `baths` | float or null | Number of bathrooms. Same note as beds. |
| `sqft` | float or null | Interior living area in square feet. Filtered to 400–10,000; values outside that range are set to null. |
| `price_per_sqft` | float or null | Computed as `price / sqft`. Null if either input is missing. Values outside 50–800 $/sqft are set to null (sanity check). |
| `year_built` | int or null | Year the structure was built. Not available from HomePath card data; null for all current records. |
| `dom` | int or null | Days on market. Available from Redfin (when used); null for HomePath and Craigslist. |
| `listing_type` | string | Classification of the sale type. See table below. |
| `description` | string | Raw card text or listing title as scraped. Truncated to 400 characters. |
| `url` | string | Link to the listing. For HomePath, this is a pre-filtered address search URL. |
| `latitude` | float or null | Geographic coordinates. Populated by Redfin when used; null for HomePath and CL. |
| `longitude` | float or null | Same as latitude. |
| `distress_flags` | list of strings | Keywords found in the listing text that suggest a distressed or non-traditional sale. See `config.DISTRESS_KEYWORDS` for the full list. |

---

## Listing type values

| Value | Meaning |
|---|---|
| `fanniemae_reo` | Fannie Mae Real Estate Owned — bank-owned after foreclosure |
| `hud_foreclosure` | HUD-owned after FHA loan default |
| `foreclosure` | Generic foreclosure listing (from other sources) |
| `foreclosure_auction` | Active foreclosure auction (Auction.com) |
| `short_sale` | Short sale — lender accepting less than the outstanding mortgage balance |
| `distressed` | Craigslist listing with one or more distress keywords detected |
| `fsbo` | For sale by owner (Craigslist, no distress keywords) |
| `active` | Standard MLS-type listing with no distress signal |

---

## Analysis fields (added during scoring)

These fields are not present in raw scraper output. They are added by `analysis.py` before the report is generated.

| Field | Type | Description |
|---|---|---|
| `deal_score` | float | Composite deal quality score. Higher is better. See `docs/scoring.md`. |
| `is_deal` | boolean | True when the listing has any distress flag, a non-standard listing type, or a deal score above zero. |
| `discount_pct` | float or null | How far the listing's $/sqft is below the area median, expressed as a percentage. Positive means below median (favorable). Null when $/sqft is unavailable. |
| `_is_new` | boolean | True when this address was not present in `data/latest.json` at the start of the current run. Used for the "New This Run" filter and notification. Not persisted to JSON. |

---

## Snapshot file — data/latest.json

The snapshot file is written at the end of every run. It contains:

| Key | Description |
|---|---|
| `listings` | Array of all listing records after scoring |
| `run_ts` | ISO 8601 timestamp of when the run completed |
| `area_median_ppqft` | The $/sqft baseline used for scoring (from Zillow or config fallback) |
| `deal_count` | Number of listings flagged as deals |

This file is gitignored. It serves only as the "previous run" reference for new-deal detection.
