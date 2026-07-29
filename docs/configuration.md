# Configuration Reference

All user-tunable settings live in `config.py`. This document walks through each section.

---

## Search area

```python
AREA = {
    "name": "Centerton / Bentonville, AR",
    "city_center": (36.3728, -94.2088),
    "bbox": {
        "lat_min": 36.28, "lat_max": 36.51,
        "lng_min": -94.38, "lng_max": -94.05,
    },
    "zip_codes": ["72712", "72713", "72715", "72716", "72719", "72758"],
    "craigslist_subdomain": "fortsmith",
    "state": "AR",
    "state_code": "AR",
    "county": "Benton",
    "radius_miles": 20,
}
```

`zip_codes` drives the Zillow CSV lookup — only these ZIPs are extracted from the national dataset. Adding a ZIP here will include it in the market average calculation.

`craigslist_subdomain` sets which CL market to search. NW Arkansas has no dedicated subdomain, so Fort Smith is used as the nearest active market.

---

## Market baseline

```python
NWA_MARKET = {
    "area_median_price_per_sqft": 190,
    "area_median_home_value": 415_000,
    "area_median_sqft": 2_100,
    "notes": "Bentonville/Centerton/Rogers AR — hot market (Walmart HQ effect)",
    "data_date": "2025-Q1",
}
```

These values are the fallback when the Zillow CSV fetch fails. They should be updated periodically. The live Zillow data (streamed on every run) overrides `area_median_price_per_sqft` automatically; `area_median_sqft` is used as the divisor to convert ZHVI home values to $/sqft.

If Zillow's data for the area is significantly different from what you're seeing in actual sales, adjust `area_median_sqft` up or down to calibrate the $/sqft figure.

---

## Score thresholds

```python
THRESHOLDS = {
    "underpriced_ratio": 0.82,
    "dom_high": 45,
    "min_price_per_sqft": 30,
    "max_price": 750_000,
    "min_price": 40_000,
}
```

`underpriced_ratio` — listings with $/sqft below this fraction of the area median get the "below-median-psf" distress flag. At 0.82, a listing priced at $178/sqft (82% of $217) or lower gets flagged.

`dom_high` — listings with days on market above this number get a "high-dom" flag, which also contributes to the deal score. Not applicable to HomePath listings, which don't expose DOM.

`min_price_per_sqft` and `max_price` / `min_price` — sanity filters to exclude data errors and placeholder listings.

---

## Distress keywords

```python
DISTRESS_KEYWORDS = [
    "foreclosure", "bank owned", "bank-owned", "reo", ...
]
```

The full list is in `config.py`. Keywords are matched case-insensitively against the combined listing title, description, and listing type. Each match adds a tag to `distress_flags` and 2 points to the deal score.

Adding new keywords is safe — just append to the list. They take effect on the next run or regen.

---

## HTTP headers

```python
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,...",
}
```

Used for plain HTTP requests (Craigslist, Zillow). Playwright handles its own browser fingerprint for HomePath.

---

## Modifying search cities

To add or remove cities from the HomePath search, edit `_SEARCH_TERMS` in `sources/homepath.py`:

```python
_SEARCH_TERMS = [
    "Bentonville, AR",
    "Rogers, AR",
    ...
]
```

Each term triggers a separate Playwright session (~8 seconds). Adding cities increases runtime proportionally.
